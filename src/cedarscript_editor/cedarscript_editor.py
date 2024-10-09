import os
from typing import Callable
from collections.abc import Sequence

from cedarscript_ast_parser import Command, CreateCommand, RmFileCommand, MvFileCommand, UpdateCommand, \
    SelectCommand, IdentifierFromFile, Segment, Marker, MoveClause, DeleteClause, \
    InsertClause, ReplaceClause, EditingAction, BodyOrWhole, RegionClause, MarkerType
from cedarscript_ast_parser.cedarscript_ast_parser import MarkerCompatible, RelativeMarker, RelativePositionType

from .identifier_selector import select_finder
from .python_identifier_finder import find_python_identifier
from .text_editor_kit import \
    normalize_indent, write_file, read_file, bow_to_search_range, \
    IdentifierBoundaries, RangeSpec, analyze_and_adjust_indentation, analyze_and_normalize_indentation, IndentationInfo


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
            plural_indicator=''
            previous_cmd_notes = ''
        else:

            plural_indicator='s'
            previous_cmd_notes = f", bearing in mind the file was updated and now contains all changes expressed in command{plural_indicator} {items}"
            if 'syntax' in description.casefold():
                probability_indicator = "most probably"
            else:
                probability_indicator= "might have"

            note = (
                f"<note>*ALL* commands *before* command #{command_ordinal} were applied and *their changes are already committed*. "
                f"Re-read the file to catch up with the applied changes."
                f"ATTENTION: The previous command (#{command_ordinal - 1}) {probability_indicator} caused command #{command_ordinal} to fail "
                f"due to changes that left the file in an invalid state (check that by re-analyzing the file!)</note>"
            )
        super().__init__(
            f"<error-details><error-location>COMMAND #{command_ordinal}</error-location>{note}"
            f"<description>{description}</description>"
            "<suggestion>NEVER apologize; just relax, take a deep breath, think step-by-step and write an in-depth analysis of what went wrong "
            "(specifying which command ordinal failed), then acknowledge which commands were already applied and concisely describe the state at which the file was left "
            "(saying what needs to be done now), "
            f"then write new commands that will fix the problem{previous_cmd_notes} "
            "(you'll get a one-million dollar tip if you get it right!) "
            "Use descriptive comment before each command.</suggestion></error-details>"
        )


class CEDARScriptEditor:
    def __init__(self, root_path):
        self.root_path = os.path.abspath(root_path)
        print(f'[{self.__class__}] root: {self.root_path}')

    # TODO Add 'target_search_range: RangeSpec' parameter
    def find_identifier(self, source_info: tuple[str, str | Sequence[str]], marker: Marker) -> IdentifierBoundaries:
        file_path = source_info[0]
        source = source_info[1]
        if not isinstance(source, str):
            source = '\n'.join(source)
        return (
            select_finder(self.root_path, file_path, source)
                (self.root_path, file_path, source, marker)
        )

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
                    case MvFileCommand() as cmd:
                        raise ValueError('Noy implemented: MV')
                    case SelectCommand() as cmd:
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

        # Example 1:
        # UPDATE FILE "tmp.benchmarks/2024-10-04-22-59-58--CEDARScript-Gemini-small/bowling/bowling.py"
        # INSERT INSIDE FUNCTION "__init__" TOP
        # WITH CONTENT '''
        #  @0:print("This line will be inserted at the top")
        #  ''';
        # After parsing ->
        # UpdateCommand(
        #     type='update',
        #     target=SingleFileClause(file_path='tmp.benchmarks/2024-10-04-22-59-58--CEDARScript-Gemini-small/bowling/bowling.py'),
        #     action=InsertClause(insert_position=RelativeMarker(type=<MarkerType.FUNCTION: 'function'>, value='__init__', offset=None)),
        #     content='\n @0:print("This line will be inserted at the top")\n '
        # )


        # Example 2:
        # UPDATE FUNCTION
        # FROM FILE "tmp.benchmarks/2024-10-04-22-59-58--CEDARScript-Gemini-small/bowling/bowling.py"
        # WHERE NAME = "__init__"
        # REPLACE SEGMENT
        # STARTING AFTER LINE "def __init__(self):"
        # ENDING AFTER LINE "def __init__(self):"
        # WITH CONTENT '''
        #  @0:print("This line will be inserted at the top")
        #  ''';
        # After parsing ->
        # UpdateCommand(
        # type='update',
        # target=IdentifierFromFile(file_path='bowling.py',
        # where_clause=WhereClause(field='NAME', operator='=', value='__init__'),
        # identifier_type='FUNCTION', offset=None
        # ),
        # action=ReplaceClause(
        # region=Segment(
        # start=RelativeMarker(type=<MarkerType.LINE: 'line'>, value='def __init__(self):', offset=None),
        # end=RelativeMarker(type=<MarkerType.LINE: 'line'>, value='def __init__(self):', offset=None)
        # )),
        # content='\n @0:print("This line will be inserted at the top")\n '
        # )

        src = read_file(file_path)
        lines = src.splitlines()

        source_info: tuple[str, str | Sequence[str]] = (file_path, src)

        def identifier_resolver(marker: Marker):
            return self.find_identifier(source_info, marker)

        # Set range_spec to cover the identifier
        search_range = restrict_search_range(action, target, identifier_resolver)

        marker, search_range = find_marker_or_segment(action, lines, search_range)

        search_range = restrict_search_range_for_marker(
            marker, action, lines, search_range, identifier_resolver
        )

        match content:
            case (region, relindent):
                dest_indent = search_range.indent
                content_range = restrict_search_range_for_marker(
                    region, action, lines, search_range, identifier_resolver
                )
                content = content_range.read(lines)
                content = analyze_and_adjust_indentation(
                    src_content_to_adjust=content,
                    target_context_for_analysis=lines,
                    base_indentation_count=dest_indent + (relindent or 0)
                )
            case str() | [str(), *_] | (str(), *_):
                pass
            case _:
                raise ValueError(f'Invalid content: {content}')


        self._apply_action(action, lines, search_range, content)

        write_file(file_path, lines)

        return f"Updated {target if target else 'file'} in {file_path}\n  -> {action}"

    def _apply_action(self, action: EditingAction, lines: Sequence[str], range_spec: RangeSpec, content: str | None = None):
        match action:

            case MoveClause(insert_position=insert_position, to_other_file=other_file, relative_indentation=relindent):
                saved_content = range_spec.delete(lines)
                # TODO Move from 'lines' to the same file or to 'other_file'
                dest_range = self._get_index_range(InsertClause(insert_position), lines)
                saved_content = analyze_and_adjust_indentation(
                    src_content_to_adjust=saved_content,
                    target_context_for_analysis=lines,
                    base_indentation_count= dest_range.indent + (relindent or 0)
                )
                dest_range.write(saved_content, lines)

            case DeleteClause():
                range_spec.delete(lines)

            case ReplaceClause() | InsertClause():
                content = analyze_and_normalize_indentation(
                    src_content_to_adjust=content,
                    target_context_for_analysis=lines,
                    context_indent_count=range_spec.indent
                )
                range_spec.write(content, lines)

            case _ as invalid:
                raise ValueError(f"Unsupported action type: {type(invalid)}")

    def _rm_command(self, cmd: RmFileCommand):
        file_path = os.path.join(self.root_path, cmd.file_path)

    def _delete_function(self, cmd): # TODO
        file_path = os.path.join(self.root_path, cmd.file_path)

    # def _create_command(self, cmd: CreateCommand):
    #     file_path = os.path.join(self.root_path, cmd.file_path)
    #
    #     os.makedirs(os.path.dirname(file_path), exist_ok=False)
    #     with open(file_path, 'w') as file:
    #         file.write(content)
    #
    #     return f"Created file: {command['file']}"

    def find_index_range_for_region(self,
                                    region: BodyOrWhole | Marker | Segment | RelativeMarker,
                                    lines: Sequence[str],
                                    identifier_resolver: Callable[[Marker], IdentifierBoundaries],
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
                                mos = self.find_identifier(lines, f'for:{region}', mos).body
                index_range = mos.to_search_range(
                    lines,
                    search_range.start if search_range else 0,
                    search_range.end if search_range else -1,
                )
            case _ as invalid:
                raise ValueError(f"Invalid: {invalid}")
        return index_range


def find_marker_or_segment(action: EditingAction, lines: Sequence[str], search_range: RangeSpec) -> tuple[Marker, RangeSpec]:
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
    return marker, search_range


def restrict_search_range(action, target, identifier_resolver: Callable[[Marker], IdentifierBoundaries]) -> RangeSpec:
    search_range = RangeSpec(0, -1, 0)
    match target:
        case IdentifierFromFile() as identifier_from_file:
            identifier_marker = identifier_from_file.as_marker
            identifier_boundaries = identifier_resolver(identifier_marker)
            if not identifier_boundaries:
                raise ValueError(f"'{identifier_marker}' not found")
            match action:
                case RegionClause(region=region):
                    match region:  # BodyOrWhole | Marker | Segment
                        case BodyOrWhole():
                            search_range = identifier_boundaries.location_to_search_range(region)
                        case _:
                            search_range = identifier_boundaries.location_to_search_range(BodyOrWhole.WHOLE)
    return search_range


def restrict_search_range_for_marker(
    marker: Marker,
    action: EditingAction,
    lines: Sequence[str],
    search_range: RangeSpec,
    identifier_resolver: Callable[[Marker], IdentifierBoundaries]
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
                        case DeleteClause():
                            search_range = search_range.set_length(1)
                case _:
                    identifier_boundaries = identifier_resolver(marker)
                    if not identifier_boundaries:
                        raise ValueError(f"'{marker}' not found")
                    qualifier: RelativePositionType = marker.qualifier if isinstance(
                        marker, RelativeMarker
                    ) else RelativePositionType.AT
                    search_range = identifier_boundaries.location_to_search_range(qualifier)
        case Segment():
            pass  # TODO
    return search_range