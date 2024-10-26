import logging
from dataclasses import dataclass
from functools import cached_property
from typing import Sequence, Iterable

from cedarscript_ast_parser import Marker, MarkerType, Segment, RelativeMarker
from grep_ast import filename_to_lang
from text_manipulation.indentation_kit import get_line_indent_count
from text_manipulation.range_spec import IdentifierBoundaries, RangeSpec, ParentInfo, ParentRestriction
from tree_sitter_languages import get_language, get_parser

from .tree_sitter_identifier_queries import LANG_TO_TREE_SITTER_QUERY

"""
Parser for extracting identifier information from source code using tree-sitter.
Supports multiple languages and provides functionality to find and analyze identifiers
like functions and classes along with their hierarchical relationships.
"""

_log = logging.getLogger(__name__)

class IdentifierFinder:
    """Finds identifiers in source code based on markers and parent restrictions.

    Attributes:
        lines: List of source code lines
        file_path: Path to the source file
        source: Complete source code as a single string
        language: Tree-sitter language instance
        tree: Parsed tree-sitter tree
        query_info: Language-specific query information
    """

    def __init__(self, fname: str, source: str | Sequence[str], parent_restriction: ParentRestriction = None):
        self.parent_restriction = parent_restriction
        match source:
            case str() as s:
                self.lines = s.splitlines()
            case _ as lines:
                self.lines = lines
                source = '\n'.join(lines)
        langstr = filename_to_lang(fname)
        if langstr is None:
            self.language = None
            self.query_info = None
            _log.info(f"[IdentifierFinder] NO LANGUAGE for `{fname}`")
            return
        self.query_info: dict[str, dict[str, str]] = LANG_TO_TREE_SITTER_QUERY[langstr]
        self.language = get_language(langstr)
        _log.info(f"[IdentifierFinder] Selected {self.language}")
        self.tree = get_parser(langstr).parse(bytes(source, "utf-8"))

    def __call__(self, mos: Marker | Segment, parent_restriction: ParentRestriction = None) -> IdentifierBoundaries | RangeSpec | None:
        parent_restriction = parent_restriction or self.parent_restriction
        match mos:
            case Marker(MarkerType.LINE) | Segment():
                # TODO pass IdentifierFinder to enable identifiers as start and/or end of a segment
                return mos.to_search_range(self.lines, parent_restriction).set_line_count(1)  # returns RangeSpec

            case Marker() as marker:
                # Returns IdentifierBoundaries
                return self._find_identifier(marker, parent_restriction)

    def _find_identifier(self,
        marker: Marker,
        parent_restriction: ParentRestriction
    ) -> IdentifierBoundaries | RangeSpec | None:
        """Finds an identifier in the source code using tree-sitter queries.

        Args:
            language: Tree-sitter language
            source: List of source code lines
            tree: Parsed tree-sitter tree
            query_scm: Dictionary of queries for different identifier types
            marker: Type, name and offset of the identifier to find

        Returns:
            IdentifierBoundaries with identifier IdentifierBoundaries with identifier start, body start, and end lines of the identifier
        or None if not found
        """
        try:
            candidates = self.language.query(self.query_info[marker.type].format(name=marker.value)).captures(self.tree.root_node)
            candidates: list[IdentifierBoundaries] = [ib for ib in capture2identifier_boundaries(
                candidates,
                self.lines
            ) if ib.match_parent(parent_restriction)]
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
        match marker:
            case RelativeMarker(qualifier=relative_position_type):
                return result.location_to_search_range(relative_position_type)
        return result


def _get_by_offset(obj: Sequence, offset: int):
    if 0 <= offset < len(obj):
        return obj[offset]
    return None


@dataclass(frozen=True)
class CaptureInfo:
    """Container for information about a captured node from tree-sitter parsing.

    Attributes:
        capture_type: Type of the captured node (e.g., 'function.definition')
        node: The tree-sitter node that was captured

    Properties:
        node_type: Type of the underlying node
        range: Tuple of (start_line, end_line)
        identifier: Name of the identifier if this is a name capture
        parents: List of (node_type, node_name) tuples representing the hierarchy
    """
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

    @cached_property
    def parents(self) -> list[ParentInfo]:
        """Returns a list of (node_type, node_name) tuples representing the hierarchy.
        The list is ordered from immediate parent to root."""
        parents: list[ParentInfo] = []
        current = self.node.parent

        while current:
            # Check if current node is a container type we care about
            if current.type.endswith('_definition'):
                # Try to find the name node - exact field depends on language
                name = None
                for child in current.children:
                    if child.type == 'identifier' or child.type == 'name':
                        name = child.text.decode('utf-8')
                        break
                parents.append(ParentInfo(name, current.type))
            current = current.parent

        return parents


def associate_identifier_parts(captures: Iterable[CaptureInfo], lines: Sequence[str]) -> list[IdentifierBoundaries]:
    """Associates related identifier parts (definition, body, docstring, etc) into IdentifierBoundaries.

    Args:
        captures: Iterable of CaptureInfo objects representing related parts
        lines: Sequence of source code lines

    Returns:
        List of IdentifierBoundaries with all parts associated
    """
    identifier_map: dict[int, IdentifierBoundaries] = {}

    for capture in captures:
        capture_type = capture.capture_type.split('.')[-1]
        range_spec = capture.to_range_spec(lines)
        if capture_type == 'definition':
            identifier_map[range_spec.start] = IdentifierBoundaries(
                whole=range_spec,
                parents=capture.parents
            )

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
    """Returns the first parent node that ends with '_definition'"""
    # TODO How to deal with 'decorated_definition' ?
    while node.parent:
        node = node.parent
        if node.type.endswith('_definition'):
            return node
    return None


def capture2identifier_boundaries(captures, lines: Sequence[str]) -> list[IdentifierBoundaries]:
    """Converts raw tree-sitter captures to IdentifierBoundaries objects.

    Args:
        captures: Raw captures from tree-sitter query
        lines: Sequence of source code lines

    Returns:
        List of IdentifierBoundaries representing the captured identifiers
    """
    captures = [CaptureInfo(c[1], c[0]) for c in captures if not c[1].startswith('_')]
    unique_captures = {}
    for capture in captures:
        unique_captures[f'{capture.range[0]}:{capture.capture_type}'] = capture
    return associate_identifier_parts(unique_captures.values(), lines)
