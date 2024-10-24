import logging
from typing import Callable, TypeAlias, Sequence, NamedTuple, Iterable

from cedarscript_ast_parser import Marker, MarkerType, Segment
from grep_ast import filename_to_lang
from text_manipulation.indentation_kit import get_line_indent_count
from text_manipulation.range_spec import IdentifierBoundaries, RangeSpec
from tree_sitter_languages import get_language, get_parser

from .tree_sitter_identifier_queries import LANG_TO_TREE_SITTER_QUERY

_log = logging.getLogger(__name__)

IdentifierFinder: TypeAlias = Callable[[Marker | Segment, RangeSpec | None], IdentifierBoundaries | RangeSpec | None]


def find_identifier(source_info: tuple[str, str | Sequence[str]], search_rage: RangeSpec = RangeSpec.EMPTY) -> IdentifierFinder:
    file_path = source_info[0]
    source = source_info[1]
    if not isinstance(source, str):
        source = '\n'.join(source)
    return _select_finder(file_path, source, search_rage)


def _select_finder(file_path: str, source: str, search_range: RangeSpec = RangeSpec.EMPTY) -> IdentifierFinder:
    langstr = filename_to_lang(file_path)
    match langstr:
        case None:
            language = None
            query_info = None
            _log.info(f"[select_finder] NO LANGUAGE for `{file_path}`")
        case _:
            query_info = LANG_TO_TREE_SITTER_QUERY[langstr]
            language = get_language(langstr)
            _log.info(f"[select_finder] Selected {language}")
            tree = get_parser(langstr).parse(bytes(source, "utf-8"))

    source = source.splitlines()

    def find_by_marker(mos: Marker | Segment, search_range: RangeSpec | None = None) -> IdentifierBoundaries | RangeSpec | None:
        match mos:

            case Marker(MarkerType.LINE) | Segment():
                # TODO pass IdentifierFinder to enable identifiers as start and/or end of a segment
                return mos.to_search_range(source, search_range).set_line_count(1)  # returns RangeSpec

            case Marker() as marker:
                # Returns IdentifierBoundaries
                return _find_identifier(language, source, tree, query_info, marker)

    return find_by_marker


def _get_by_offset(obj: Sequence, offset: int):
    if 0 <= offset < len(obj):
        return obj[offset]
    return None


class CaptureInfo(NamedTuple):
    capture_type: str
    node: any

    def to_range_spec(self, lines: Sequence[str]) -> RangeSpec:
        start, end = self.range
        return RangeSpec(start, end + 1, get_line_indent_count(lines[start]))

    @property
    def node_type(self):
        return self.node.type

    @property
    def range(self):
        return self.node.range.start_point[0], self.node.range.end_point[0]

    @property
    def identifier(self):
        if not self.capture_type.endswith('.name'):
            return None
        return self.node.text.decode("utf-8")


def associate_identifier_parts(captures: Iterable[CaptureInfo], lines: Sequence[str]) -> list[IdentifierBoundaries]:
    identifier_map: dict[int, IdentifierBoundaries] = {}

    for capture in captures:
        capture_type = capture.capture_type.split('.')[-1]
        range_spec = capture.to_range_spec(lines)
        if capture_type == 'definition':
            identifier_map[range_spec.start] = IdentifierBoundaries(range_spec)

        else:
            parent = find_parent_definition(capture.node)
            if parent:
                parent_key = parent.start_point[0]
                parent = identifier_map.get(parent_key)
            if parent is None:
                raise ValueError(f'Parent node not found for [{capture.capture_type} - {capture.node_type}] ({capture.node.text.decode("utf-8").strip()})')
            match capture_type:
                case 'body':
                    parent = parent._replace(body=range_spec)
                case 'docstring':
                    parent = parent._replace(docstring=range_spec)
                case 'decorator':
                    parent = parent.decorators.append(range_spec)
                case _ as invalid:
                    raise ValueError(f'Invalid capture type: {invalid}')
            identifier_map[parent_key] = parent

    return sorted(identifier_map.values(), key=lambda x: x.whole.start)


def find_parent_definition(node):
    # TODO How to deal with 'decorated_definition' ?
    while node.parent:
        node = node.parent
        if node.type.endswith('_definition'):
            return node
    return None


def _find_identifier(language, source: Sequence[str], tree, query_scm: dict[str, dict[str, str]], marker: Marker) \
        -> IdentifierBoundaries | None:
    """
    Find the starting line index of a specified function in the given lines.

    :param source: The original text
    :param tree: The parsed tree from tree-sitter
    :param query_scm: A dictionary containing queries for different types of identifiers
    :param marker: Type, name and offset of the identifier to find.
    :return: IdentifierBoundaries with identifier start, body start, and end lines of the identifier
    or None if not found.
    """
    try:
        candidates = language.query(query_scm[marker.type].format(name=marker.value)).captures(tree.root_node)
        candidates: list[IdentifierBoundaries] = capture2identifier_boundaries(
            candidates,
            source
        )
    except Exception as e:
        raise ValueError(f"Unable to capture nodes for {marker}: {e}") from e

    candidate_count = len(candidates)
    if not candidate_count:
        return None
    if candidate_count > 1 and marker.offset is None:
        raise ValueError(
            f"The {marker.type} identifier named `{marker.value}` is ambiguous (found {candidate_count} matches). "
            f"Choose an `OFFSET` between 0 and {candidate_count - 1} to determine how many to skip. "
            f"Example to reference the *last* `{marker.value}`: `OFFSET {candidate_count - 1}`"
        )
    if marker.offset and marker.offset >= candidate_count:
        raise ValueError(
            f"There are only {candidate_count} {marker.type} identifiers named `{marker.value}`, "
            f"but 'OFFSET' was set to {marker.offset} (you can skip at most {candidate_count - 1} of those)"
        )
    candidates.sort(key=lambda x: x.whole.start)
    result: IdentifierBoundaries = _get_by_offset(candidates, marker.offset or 0)
    return result


def capture2identifier_boundaries(captures, lines: Sequence[str]) -> list[IdentifierBoundaries]:
    captures = [CaptureInfo(c[1], c[0]) for c in captures if not c[1].startswith('_')]
    unique_captures = {}
    for capture in captures:
        unique_captures[f'{capture.range[0]}:{capture.capture_type}'] = capture
    return associate_identifier_parts(unique_captures.values(), lines)
