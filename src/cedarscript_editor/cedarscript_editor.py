import os
from collections.abc import Sequence
from pathlib import Path

from cedarscript_ast_parser import Command, RmFileCommand, MvFileCommand, UpdateCommand, \
    SelectCommand, CreateCommand, IdentifierFromFile, Segment, Marker, MoveClause, DeleteClause, \
    InsertClause, ReplaceClause, EditingAction, BodyOrWhole, RegionClause, MarkerType, EdScript, \
    CaseStatement
from .ed_script_filter import process_ed_script
from .case_filter import process_case_statement
from cedarscript_ast_parser.cedarscript_ast_parser import MarkerCompatible, RelativeMarker, \
    RelativePositionType, Region, SingleFileClause
from text_manipulation import (
    IndentationInfo, IdentifierBoundaries, RangeSpec, read_file, write_file, bow_to_search_range, IdentifierFinder
)

from .tree_sitter_identifier_finder import TreeSitterIdentifierFinder


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
            "the file was left (saying what needs to be done now). Write all that inside these 2 tags "
            "(<reasoning>...Chain of thoughts and reasoning here...</reasoning>\\n<verdict>...distilled analysis "
            "here...</verdict>); "
            "Then write new commands that will fix the problem"
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
                raise CEDARScriptEditorException(i + 1, str(e)) from e
        return result

    def _update_command(self, cmd: UpdateCommand):
        action: EditingAction = cmd.action
        target = cmd.target
        content = cmd.content or []
        file_path = os.path.join(self.root_path, target.file_path)

        src = read_file(file_path)
        lines = src.splitlines()

        identifier_finder = TreeSitterIdentifierFinder(file_path, src, RangeSpec.EMPTY)
            
        search_range = RangeSpec.EMPTY
        move_src_range = None
        match action:
            case MoveClause():
                # READ + DELETE region  : action.region (PARENT RESTRICTION: target.as_marker)
                move_src_range = restrict_search_range(action.region, target, identifier_finder, lines)
                # WRITE region: action.insert_position
                search_range = restrict_search_range(action.insert_position, None, identifier_finder, lines)
            case RegionClause(region=region) | InsertClause(insert_position=region):
                search_range = restrict_search_range(region, target, identifier_finder, lines)

        if search_range and search_range.line_count:
            match action:
                case RegionClause(region=Segment()):
                    pass
                case RegionClause(region=Marker()) if action.region.type in [MarkerType.FUNCTION, MarkerType.METHOD, MarkerType.CLASS]:
                    pass
                case _:
                    marker, search_range = find_marker_or_segment(action, lines, search_range)
                    match action:
                        case InsertClause(insert_position=RelativeMarker(
                            qualifier=qualifier)
                        ):
                            # TODO Handle BEFORE AFTER INSIDE_TOP INSIDE_BOTTOM
                            search_range = search_range.set_line_count(0)
                            if qualifier != RelativePositionType.AFTER:
                                search_range = search_range.inc()


        match content:
            case EdScript() as ed_script_filter:
                # Filter the search range lines using an ED script
                range_lines = search_range.read(lines)
                content = process_ed_script(range_lines, ed_script_filter.script)
            case CaseStatement() as case_filter:
                # Filter the search range lines using `WHEN..THEN` pairs of a CASE statement
                range_lines = search_range.read(lines)
                content = process_case_statement(range_lines, case_filter)
            case str() | [str(), *_] | (str(), *_):
                pass
            case (region, relindent_level):
                content_range = restrict_search_range_for_marker(
                    region, action, lines, RangeSpec.EMPTY, identifier_finder
                )
                content = IndentationInfo.shift_indentation(
                    content_range.read(lines), lines, search_range.indent, relindent_level,
                    identifier_finder
                )
                content = (region, content)
            case _:
                match action:
                    case MoveClause(insert_position=region, relative_indentation=relindent_level):
                        content = IndentationInfo.shift_indentation(
                            move_src_range.read(lines), lines, search_range.indent, relindent_level,
                            identifier_finder
                        )
                    case DeleteClause():
                        pass
                    case _:
                        raise ValueError(f'Invalid content: {content}')

        self._apply_action(
            action, lines, search_range, content,
            range_spec_to_delete=move_src_range, identifier_finder=identifier_finder
        )

        write_file(file_path, lines)

        return f"Updated {target if target else 'file'}\n  -> {action}"

    @staticmethod
    def _apply_action(
        action: EditingAction, lines: Sequence[str], range_spec: RangeSpec, content: str | None = None,
        range_spec_to_delete: RangeSpec | None = None,
        identifier_finder: IdentifierFinder | None = None
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
                    case str():
                        content = IndentationInfo.from_content(lines, identifier_finder).apply_relative_indents(
                            content, range_spec.indent
                        )
                    case Sequence():
                        content = [line.rstrip() for line in content]

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
                                identifier_finder_IS_IT_USED: IdentifierFinder,
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
                            mos = TreeSitterIdentifierFinder("TODO?.py", lines, RangeSpec.EMPTY)(mos, search_range).body
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
                case None:
                    raise ValueError(f"Unable to find {region}")
                case _ as invalid:
                    raise ValueError(f'Invalid: {invalid}')
        case Segment() as segment:
            return segment.to_search_range(lines, identifier_boundaries.whole if identifier_boundaries is not None else None)
        case _ as invalid:
            raise ValueError(f'Unsupported region type: {type(invalid)}')


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
        case Marker(type=MarkerType.LINE):
            search_range = marker.to_search_range(lines, search_range)
            match action:
                case InsertClause():
                    if action.insert_position.qualifier == RelativePositionType.BEFORE:
                        search_range = search_range.inc()
                case RegionClause():
                    search_range = search_range.set_line_count(1)
        case Marker():
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
