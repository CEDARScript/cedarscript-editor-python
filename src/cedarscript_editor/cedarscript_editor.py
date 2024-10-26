import os
from collections.abc import Sequence
from pathlib import Path

from cedarscript_ast_parser import Command, RmFileCommand, MvFileCommand, UpdateCommand, \
    SelectCommand, CreateCommand, IdentifierFromFile, Segment, Marker, MoveClause, DeleteClause, \
    InsertClause, ReplaceClause, EditingAction, BodyOrWhole, RegionClause, MarkerType
from cedarscript_ast_parser.cedarscript_ast_parser import MarkerCompatible, RelativeMarker, \
    RelativePositionType, Region, SingleFileClause
from text_manipulation import (
    IndentationInfo, IdentifierBoundaries, RangeSpec, read_file, write_file, bow_to_search_range
)

from .tree_sitter_identifier_finder import IdentifierFinder


class CEDARScriptEditorException(Exception):
    def __init__(self, command_ordinal: int, description: str):
        match command_ordinal:
            case 0 | 1:
                items = ''
            case 2:
                items = "#1"
            case 3:
                items = "#1 and #2"
            case _:
                sequence = ", ".join(f'#{i}' for i in range(1, command_ordinal - 1))
                items = f"{sequence} and #{command_ordinal - 1}"
        if command_ordinal <= 1:
            note = ''
            previous_cmd_notes = ''
        else:

            previous_cmd_notes = (
                f", bearing in mind the file was updated and now contains all changes expressed in "
                f"commands {items}."
            )
            if 'syntax' in description.casefold():
                probability_indicator = "most probably"
            else:
                probability_indicator = "might have"

            note = (
                f"<note>*ALL* commands *before* command #{command_ordinal} "
                "were applied and *their changes are already committed*. "
                f"So, it's *CRUCIAL* to re-analyze the file to catch up with the applied changes "
                "and understand what still needs to be done. "
                f"ATTENTION: The previous command (#{command_ordinal - 1}) {probability_indicator} "
                f"caused command #{command_ordinal} to fail "
                f"due to changes that left the file in an invalid state (check that by re-reading the file!)</note>"
            )
        super().__init__(
            "<error-details>"
            f"\n<error-location>COMMAND #{command_ordinal}</error-location>"
            f"\n<description>{description}</description>"
            f"\n{note}"
            "\n<suggestion>Reflect about common mistakes when using CEDARScript. Now relax, take a deep breath, "
            "think step-by-step and write an in-depth analysis of what went wrong (specifying which command ordinal "
            "failed), then acknowledge which commands were already applied and concisely describe the state at which "
            "the file was left (saying what needs to be done now), then write new commands that will fix the problem"
            f"{previous_cmd_notes} (you'll get a one-million dollar tip if you get it right!) "
            "Use descriptive comment before each command; If showing CEDARScript commands to the user, "
            "*DON'T* enclose them in ```CEDARSCript and ``` otherwise they will be executed!"
            "</suggestion>\n</error-details>"
        )


class CEDARScriptEditor:
    def __init__(self, root_path: os.PathLike):
        self.root_path = Path(os.path.abspath(root_path))
        print(f'[{self.__class__.__name__}] root: {self.root_path}')

    # TODO Add 'target_search_range: RangeSpec' parameter

    def apply_commands(self, commands: Sequence[Command]):
        result = []
        for i, command in enumerate(commands):
            try:
                match command:
                    case UpdateCommand() as cmd:
                        result.append(self._update_command(cmd))
                    case CreateCommand() as cmd:
                        result.append(self._create_command(cmd))
                    case RmFileCommand() as cmd:
                        result.append(self._rm_command(cmd))
                    case MvFileCommand():
                        raise ValueError('Noy implemented: MV')
                    case SelectCommand():
                        raise ValueError('Noy implemented: SELECT')
                    case _ as invalid:
                        raise ValueError(f"Unknown command '{type(invalid)}'")
            except Exception as e:
                print(f'[apply_commands] (command #{i+1}) Failed: {command}')
                if isinstance(command, UpdateCommand):
                    print(f'CMD CONTENT: ***{command.content}***')
                raise CEDARScriptEditorException(i + 1, str(e)) from e
        return result

    def _update_command(self, cmd: UpdateCommand):
        action: EditingAction = cmd.action
        target = cmd.target
        content = cmd.content or []
        file_path = os.path.join(self.root_path, target.file_path)

        src = read_file(file_path)
        lines = src.splitlines()

        identifier_finder = IdentifierFinder(file_path, src, RangeSpec.EMPTY)

        search_range = RangeSpec.EMPTY
        match action:
            case MoveClause():
                # READ + DELETE region  : action.region (PARENT RESTRICTION: target.as_marker)
                move_src_range = restrict_search_range(action.region, target, identifier_finder, lines)
                # WRITE region: action.insert_position
                search_range = restrict_search_range(action.insert_position, None, identifier_finder, lines)
            case _:
                move_src_range = None
                # Set range_spec to cover the identifier
                match action:
                    case RegionClause(region=region):
                        search_range = restrict_search_range(action.region, target, identifier_finder, lines)

        # UPDATE FUNCTION "_check_raw_id_fields_item"
        # FROM FILE "refactor-benchmark/checks_BaseModelAdminChecks__check_raw_id_fields_item/checks.py"
        # REPLACE LINE "def _check_raw_id_fields_item(self, obj, field_name, label):"
        # WITH CONTENT '''
        # @0:def _check_raw_id_fields_item(obj, field_name, label):
        # ''';
        # target = IdentifierFromFile(file_path='refactor-benchmark/checks_BaseModelAdminChecks__check_raw_id_fields_item/checks.py', identifier_type=<MarkerType.FUNCTION: 'function'>, name='_check_raw_id_fields_item', where_clause=None, offset=None)
        # action = ReplaceClause(region=Marker(type=<MarkerType.LINE: line>, value=def _check_raw_id_fields_item(self, obj, field_name, label):, offset=None))
        if search_range.line_count:
            match action:
                case RegionClause(region=Segment()):
                    pass
                case RegionClause(region=Marker()) if action.region.type in [MarkerType.FUNCTION, MarkerType.METHOD, MarkerType.CLASS]:
                    pass
                case _:
                    marker, search_range = find_marker_or_segment(action, lines, search_range)
                    search_range = restrict_search_range_for_marker(
                        marker, action, lines, search_range, identifier_finder
                    )

        match content:
            case str() | [str(), *_] | (str(), *_):
                pass
            case (region, relindent_level):
                content_range = restrict_search_range_for_marker(
                    region, action, lines, RangeSpec.EMPTY, identifier_finder
                )
                content = IndentationInfo.shift_indentation(
                    content_range.read(lines), lines, search_range.indent, relindent_level
                )
                content = (region, content)
            case _:
                match action:
                    case MoveClause(insert_position=region, relative_indentation=relindent_level):
                        # dest_range = restrict_search_range_for_marker(
                        #     region, action, lines, RangeSpec.EMPTY, identifier_finder
                        # )
                        # TODO Are the 3 lines above needed?
                        content = IndentationInfo.shift_indentation(
                            move_src_range.read(lines), lines, search_range.indent, relindent_level
                        )
                    case DeleteClause():
                        pass
                    case _:
                        raise ValueError(f'Invalid content: {content}')

        self._apply_action(action, lines, search_range, content, range_spec_to_delete=move_src_range)

        write_file(file_path, lines)

        return f"Updated {target if target else 'file'} in {file_path}\n  -> {action}"

    @staticmethod
    def _apply_action(
        action: EditingAction, lines: Sequence[str], range_spec: RangeSpec, content: str | None = None,
        range_spec_to_delete: RangeSpec | None = None
    ):
        match action:

            case MoveClause(insert_position=insert_position, to_other_file=other_file, relative_indentation=relindent):
                # TODO Move from 'lines' to the same file or to 'other_file'

                if range_spec < range_spec_to_delete:
                    range_spec_to_delete.delete(lines)
                    range_spec.write(content, lines)
                elif range_spec > range_spec_to_delete:
                    range_spec.write(content, lines)
                    range_spec_to_delete.delete(lines)

            case DeleteClause():
                range_spec.delete(lines)

            case ReplaceClause() | InsertClause():
                match content:
                    case (region, processed_content):
                        content = processed_content
                    case str():
                        content = IndentationInfo.from_content(lines).apply_relative_indents(
                            content, range_spec.indent
                        )

                range_spec.write(content, lines)

            case _ as invalid:
                raise ValueError(f"Unsupported action type: {type(invalid)}")

    def _rm_command(self, cmd: RmFileCommand):
        file_path = os.path.join(self.root_path, cmd.file_path)

    def _delete_function(self, cmd):  # TODO
        file_path = os.path.join(self.root_path, cmd.file_path)

    def _create_command(self, cmd: CreateCommand) -> str:
        """Handle the CREATE command to create new files with content.
        
        Args:
            cmd: The CreateCommand instance containing file_path and content
            
        Returns:
            str: A message describing the result
            
        Raises:
            ValueError: If the file already exists
        """
        file_path = os.path.join(self.root_path, cmd.file_path)
        
        if os.path.exists(file_path):
            raise ValueError(f"File already exists: {cmd.file_path}")
            
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        content = cmd.content
        if isinstance(content, (list, tuple)):
            content = '\n'.join(content)
            
        # Process relative indentation in content
        write_file(file_path, IndentationInfo.default().apply_relative_indents(content))
        
        return f"Created file: {cmd.file_path}"


def find_index_range_for_region(region: BodyOrWhole | Marker | Segment | RelativeMarker,
                                lines: Sequence[str],
                                identifier_finder: IdentifierFinder,
                                search_range: RangeSpec | IdentifierBoundaries | None = None,
                                ) -> RangeSpec:
    # BodyOrWhole | RelativeMarker | MarkerOrSegment
    # marker_or_segment_to_index_range_impl
    # IdentifierBoundaries.location_to_search_range(self, location: BodyOrWhole | RelativePositionType) -> RangeSpec
    match region:
        case BodyOrWhole() as bow:
            # TODO Set indent char count
            index_range = bow_to_search_range(bow, search_range)
        case Marker() | Segment() as mos:
            if isinstance(search_range, IdentifierBoundaries):
                search_range = search_range.whole
            match mos:
                case Marker(type=marker_type):
                    match marker_type:
                        case MarkerType.LINE:
                            pass
                        case _:
                            # TODO transform to RangeSpec
                            mos = IdentifierFinder("TODO?.py", lines, RangeSpec.EMPTY)(mos, search_range).body
            index_range = mos.to_search_range(
                lines,
                search_range.start if search_range else 0,
                search_range.end if search_range else -1,
            )
        case _ as invalid:
            raise ValueError(f"Invalid: {invalid}")
    return index_range


def find_marker_or_segment(
        action: EditingAction, lines: Sequence[str], search_range: RangeSpec
) -> tuple[Marker, RangeSpec]:
    marker: Marker | Segment | None = None
    match action:
        case MarkerCompatible() as marker_compatible:
            marker = marker_compatible.as_marker
        case RegionClause(region=region):
            match region:
                case MarkerCompatible():
                    marker = region.as_marker
                case Segment() as segment:
                    # TODO Handle segment's start and end as a marker and support identifier markers
                    search_range = segment.to_search_range(lines, search_range)
                    marker = None
                case BodyOrWhole():
                    if search_range.end == -1:
                        search_range = search_range._replace(end=len(lines))

    return marker, search_range


def restrict_search_range(
        region: Region, parent_restriction: any,
        identifier_finder: IdentifierFinder, lines: Sequence[str]
) -> RangeSpec:
    identifier_boundaries = None
    match parent_restriction:
        case IdentifierFromFile():
            identifier_boundaries = identifier_finder(parent_restriction.as_marker)
    match region:
        case BodyOrWhole() | RelativePositionType():
            match parent_restriction:
                case IdentifierFromFile():
                    match identifier_boundaries:
                        case None:
                            raise ValueError(f"'{parent_restriction}' not found")
                case SingleFileClause():
                    return RangeSpec.EMPTY
                case None:
                    raise ValueError(f"'{region}' requires parent_restriction")
                case _:
                    raise ValueError(f"'{region}' isn't compatible with {parent_restriction}")
            return identifier_boundaries.location_to_search_range(region)
        case Marker() as inner_marker:
            match identifier_finder(inner_marker, identifier_boundaries.whole if identifier_boundaries is not None else None):
                case IdentifierBoundaries() as inner_boundaries:
                    return inner_boundaries.location_to_search_range(BodyOrWhole.WHOLE)
                case RangeSpec() as inner_range_spec:
                    return inner_range_spec
        case Segment() as segment:
            return segment.to_search_range(lines, identifier_boundaries.whole if identifier_boundaries is not None else None)
        case _ as invalid:
            raise ValueError(f'Unsupported region type: {type(invalid)}')
    return RangeSpec.EMPTY


def restrict_search_range_for_marker(
    marker: Marker,
    action: EditingAction,
    lines: Sequence[str],
    search_range: RangeSpec,
    identifier_finder: IdentifierFinder
) -> RangeSpec:
    if marker is None:
        return search_range

    match marker:
        case Marker():
            match marker.type:
                case MarkerType.LINE:
                    search_range = marker.to_search_range(lines, search_range)
                    match action:
                        case InsertClause():
                            if action.insert_position.qualifier == RelativePositionType.BEFORE:
                                search_range = search_range.inc()
                        case RegionClause():
                            search_range = search_range.set_line_count(1)
                case _:
                    identifier_boundaries = identifier_finder(marker)
                    if not identifier_boundaries:
                        raise ValueError(f"'{marker}' not found")
                    qualifier: RelativePositionType = marker.qualifier if isinstance(
                        marker, RelativeMarker
                    ) else RelativePositionType.AT
                    search_range = identifier_boundaries.location_to_search_range(qualifier)
        case Segment():
            pass  # TODO
    return search_range
