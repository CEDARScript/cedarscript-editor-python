from .cedarscript_editor_base import CEDARScriptEditorBase, FunctionBoundaries
import rope.base.project
from rope.base import libutils, ast

from .text_editor_kit import SearchRange, get_line_indent_count


def get_by_offset(obj: list, offset: int):
    if 0 <= offset < len(obj):
        return obj[offset]
    return None

class PythonCEDARScriptEditor(CEDARScriptEditorBase):
    """
    A class to handle Python code editing operations.
    """

    # TODO Support search_start_line, search_end_line
    def _find_function(self, source: str, file_name: str, function_name: str, offset: int | None = None) -> FunctionBoundaries | None:
        """
        Find the starting line index of a specified function in the given lines.

        :param source: Source code.
        :param function_name: Name of the function to find.
        :param offset: how many functions to skip. TODO: If `None` when there are 2 or more functions with the same name, raise exception.
        :return: FunctionBoundaries with function start, body start, and end lines of the function or None if not found.
        """
        project = rope.base.project.Project(self.root_path)
        resource = libutils.path_to_resource(project, file_name)
        pymodule = libutils.get_string_module(project, source, resource=resource)

        candidates: list[FunctionBoundaries] = []
        lines = source.splitlines()
        # Use rope's AST to find the function
        for node in ast.walk(pymodule.get_ast()):
            if not isinstance(node, ast.FunctionDef) or node.name != function_name:
                continue
            start_line = node.lineno
            body_start_line = node.body[0].lineno if node.body else start_line
            # Find the last line by traversing all child nodes
            end_line = start_line
            for child in ast.walk(node):
                if hasattr(child, 'lineno'):
                    end_line = max(end_line, child.lineno)
            # TODO Set indentation for all 3 lines
            candidates.append(FunctionBoundaries(
                SearchRange(start_line - 1, end_line, get_line_indent_count(lines[start_line - 1])),
                SearchRange(body_start_line - 1, end_line, get_line_indent_count(lines[body_start_line - 1]))
            ))

        candidate_count = len(candidates)
        if not candidate_count:
            return None
        if candidate_count > 1 and offset is None:
            raise ValueError(
                f"There are {candidate_count} functions named `{function_name}` in file `{file_name}`. "
                f"Use `OFFSET <0..{candidate_count - 1}>` to determine how many to skip. "
                f"Example to reference the *last* `{function_name}`: `OFFSET {candidate_count - 1}`"
            )
        if offset and offset >= candidate_count:
            raise ValueError(
                f"There are only {candidate_count} functions named `{function_name} in file `{file_name}`, "
                f"but 'offset' was set to {offset} (you can only skip {candidate_count - 1} functions)"
            )
        candidates.sort(key=lambda x: x.start_line)
        return get_by_offset(candidates, offset or 0)


