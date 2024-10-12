import rope
from cedarscript_ast_parser import Marker, MarkerType
from rope.base import ast, libutils
from collections.abc import Sequence

from text_manipulation.range_spec import IdentifierBoundaries, RangeSpec
from text_manipulation.indentation_kit import get_line_indent_count


def get_by_offset(obj: Sequence, offset: int):
    if 0 <= offset < len(obj):
        return obj[offset]
    return None


def find_python_identifier(root_path: str, file_name: str, source: str, marker: Marker) -> IdentifierBoundaries | None:
    """
    Find the starting line index of a specified function in the given lines.

    :param root_path:
    :param file_name:
    :param source: Source code.
    :param marker: Type, name and offset of the identifier to find.
    TODO: If `None` when there are 2 or more identifiers with the same name, raise exception.
    :return: IdentifierBoundaries with identifier start, body start, and end lines of the identifier
    or None if not found.
    """
    project = rope.base.project.Project(root_path)
    resource = libutils.path_to_resource(project, file_name)
    pymodule = libutils.get_string_module(project, source, resource=resource)

    candidates: list[IdentifierBoundaries] = []
    lines = source.splitlines()
    # Use rope's AST to find the identifier
    match marker.type:
        case MarkerType.FUNCTION:
            ast_type = ast.FunctionDef
        case MarkerType.CLASS:
            ast_type = ast.ClassDef
        case _:
            raise ValueError(f'Invalid identifier type: {marker.type}')
    for node in ast.walk(pymodule.get_ast()):
        if not isinstance(node, ast_type) or node.name != marker.value:
            continue
        start_line = node.lineno
        body_start_line = node.body[0].lineno if node.body else start_line
        # Find the last line by traversing all child nodes
        end_line = start_line
        for child in ast.walk(node):
            if hasattr(child, 'lineno'):
                end_line = max(end_line, child.lineno)
        # TODO Set indentation for all 3 lines
        candidates.append(IdentifierBoundaries(
            RangeSpec(start_line - 1, end_line, get_line_indent_count(lines[start_line - 1])),
            RangeSpec(body_start_line - 1, end_line, get_line_indent_count(lines[body_start_line - 1]))
        ))

    candidate_count = len(candidates)
    if not candidate_count:
        return None
    if candidate_count > 1 and marker.offset is None:
        raise ValueError(
            f"There are {candidate_count} functions named `{marker.value}` in file `{file_name}`. "
            f"Use `OFFSET <0..{candidate_count - 1}>` to determine how many to skip. "
            f"Example to reference the *last* `{marker.value}`: `OFFSET {candidate_count - 1}`"
        )
    if marker.offset and marker.offset >= candidate_count:
        raise ValueError(
            f"There are only {candidate_count} functions named `{marker.value} in file `{file_name}`, "
            f"but 'offset' was set to {marker.offset} (you can only skip {candidate_count - 1} functions)"
        )
    candidates.sort(key=lambda x: x.start_line)
    result: IdentifierBoundaries = get_by_offset(candidates, marker.offset or 0)
    return result
