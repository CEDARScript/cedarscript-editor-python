import os
from abc import ABC, abstractmethod

from cedarscript_ast_parser import Command, CreateCommand, RmFileCommand, MvFileCommand, UpdateCommand, \
    SelectCommand, IdentifierFromFile, SingleFileClause, Segment, Marker, MoveClause, DeleteClause, \
    InsertClause, ReplaceClause, EditingAction, Region, BodyOrWhole, WhereClause, RegionClause
from .text_editor_kit import \
    normalize_indent, write_file, read_file, bow_to_search_range, \
    FunctionBoundaries, SearchRange, analyze_indentation, IndentationInfo

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


class CEDARScriptEditorBase(ABC):
    def __init__(self, root_path):
        self.root_path = os.path.abspath(root_path)
        print(f'[{self.__class__}] root: {self.root_path}')

    # TODO Add search_range: SearchRange parameter
    def find_function(self, source: str | list[str], file_name: str, function_name: str, offset: int | None = None) -> FunctionBoundaries:
        if not isinstance(source, str):
            source = '\n'.join(source)
        return self._find_function(source, file_name, function_name, offset)

    @abstractmethod
    def _find_function(self, source: str, file_name: str, function_name: str, offset: int | None = None) -> FunctionBoundaries | None:
        pass

    def apply_commands(self, commands: list[Command]):
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
        file_path = os.path.join(self.root_path, cmd.target.file_path)
        content = cmd.content or []

        match cmd.target:

            case IdentifierFromFile(
                identifier_type='FUNCTION', where_clause=WhereClause(field='NAME', operator='=', value=function_name)
            ):
                try:
                    return self._update_content(file_path, cmd.action, content, function_name=function_name, offset = cmd.target.offset)
                except IOError as e:
                    msg = f"function `{function_name}` in `{cmd.target.file_path}`"
                    raise IOError(f"Error updating {msg}: {e}")

            case SingleFileClause():
                try:
                    return self._update_content(file_path, cmd.action, content)
                except IOError as e:
                    msg = f"file `{cmd.target.file_path}`"
                    raise IOError(f"Error updating {msg}: {e}")

            case _ as invalid:
                raise ValueError(f"Not implemented: {invalid}")

    def _update_content(self, file_path: str, action: EditingAction, content: str | None,
                        search_range: SearchRange | None = None, function_name: str | None = None, offset: int | None = None) -> str:
        src = read_file(file_path)
        lines = src.splitlines()

        if function_name:
            function_boundaries = self.find_function(src, file_path, function_name, offset)
            if not function_boundaries:
                raise ValueError(f"Function '{function_name}' not found in {file_path}")
            if search_range:
                print(f'Discarding search range to use function range...')
            search_range = _get_index_range(action, lines, function_boundaries)
        else:
            search_range = _get_index_range(action, lines)

        self._apply_action(action, lines, search_range, content)

        write_file(file_path, lines)

        return f"Updated {'function ' + function_name if function_name else 'file'} in {file_path}\n  -> {action}"

    def _apply_action(self, action: EditingAction, lines: list[str], search_range: SearchRange, content: str | None = None):
        index_start, index_end, reference_indent = search_range

        match action:

            case MoveClause(insert_position=insert_position, to_other_file=other_file, relative_indentation=relindent):
                saved_content = lines[index_start:index_end]
                lines[index_start:index_end] = []
                # TODO Move from 'lines' to the same file or to 'other_file'
                dest_range = _get_index_range(InsertClause(insert_position), lines)
                indentation_info: IndentationInfo = analyze_indentation(saved_content)
                lines[dest_range.start:dest_range.end] = indentation_info.adjust_indentation(saved_content, dest_range.indent + (relindent or 0))

            case DeleteClause():
                lines[index_start:index_end] = []

            case ReplaceClause() | InsertClause():
                indentation_info: IndentationInfo = analyze_indentation(lines)
                lines[index_start:index_end] = normalize_indent(content, reference_indent, indentation_info)

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


def _get_index_range(action: EditingAction, lines: list[str], search_range: SearchRange | FunctionBoundaries | None = None) -> SearchRange:
    match action:
        case RegionClause(region=r) | InsertClause(insert_position=r):
            return find_index_range_for_region(r, lines, search_range)
        case _ as invalid:
            raise ValueError(f"Unsupported action type: {type(invalid)}")

def find_index_range_for_region(region: Region, lines: list[str], search_range: SearchRange | FunctionBoundaries | None = None) -> SearchRange:
    match region:
        case BodyOrWhole() as bow:
            # TODO Set indent char count
            index_range = bow_to_search_range(bow, search_range)
        case Marker() | Segment() as mos:
            if isinstance(search_range, FunctionBoundaries):
                search_range = search_range.whole
            index_range = mos.marker_or_segment_to_index_range(
                lines,
                search_range.start if search_range else 0,
                search_range.end if search_range else -1,
            )
        case _ as invalid:
            raise ValueError(f"Invalid: {invalid}")
    return index_range
