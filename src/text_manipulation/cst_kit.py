from typing import runtime_checkable, Protocol, Sequence

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
