from typing import runtime_checkable, Protocol, Sequence
from functools import cached_property
from cedarscript_ast_parser import Marker, Segment, RelativeMarker, RelativePositionType, MarkerType, BodyOrWhole

from .range_spec import IdentifierBoundaries, RangeSpec, ParentRestriction
from .text_editor_kit import read_file, write_file, bow_to_search_range


@runtime_checkable
class IdentifierFinder(Protocol):
    """Protocol for finding identifiers in source code."""

    def __call__(
            self, mos: Marker | Segment, parent_restriction: ParentRestriction = None
    ) -> IdentifierBoundaries | RangeSpec | None:
        """Find identifier boundaries for a given marker or segment."""
        pass

    def find_identifiers(
        self, identifier_type: str, name: str, all_restrictions: list[ParentRestriction] | None = None
    ) -> list[IdentifierBoundaries]:
        pass

    @cached_property
    def find_all_callables(self) -> list[IdentifierBoundaries]:
        return self.find_identifiers('function', r'.*')