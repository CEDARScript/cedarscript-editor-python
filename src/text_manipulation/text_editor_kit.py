from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from cedarscript_ast_parser import Marker, RelativeMarker, RelativePositionType, Segment, MarkerType, BodyOrWhole
from .range_spec import IdentifierBoundaries, RangeSpec


def read_file(file_path: str) -> str:
    with open(file_path, 'r') as file:
        return file.read()


def write_file(file_path: str, lines: Sequence[str]):
    with open(file_path, 'w') as file:
        file.writelines([line + '\n' for line in lines])


# def count_leading_chars(line: str, char: str) -> int:
#     return len(line) - len(line.lstrip(char))

def bow_to_search_range(bow: BodyOrWhole, searh_range: IdentifierBoundaries | RangeSpec | None = None) -> RangeSpec:
    match searh_range:

        case RangeSpec() | None:
            return searh_range or RangeSpec.EMPTY

        case IdentifierBoundaries():
            return searh_range.location_to_search_range(bow)

        case _ as invalid:
            raise ValueError(f"Invalid: {invalid}")


# MarkerOrSegment

# class MarkerOrSegmentProtocol(Protocol):
#     def to_search_range(self) -> str:
#         ...


@runtime_checkable
class MarkerOrSegmentProtocol(Protocol):
    def marker_or_segment_to_index_range(
        self,
        lines: Sequence[str],
        search_start_index: int = 0, search_end_index: int = -1
    ) -> RangeSpec:
        ...


def marker_or_segment_to_search_range_impl(
    self,
    lines: Sequence[str],
    search_range: RangeSpec = RangeSpec.EMPTY
) -> RangeSpec | None:
    match self:
        case Marker(type=MarkerType.LINE):
            result = RangeSpec.from_line_marker(lines, self, search_range)
            assert result is not None, (
                f"Unable to find `{self}`; Try: 1) Double-checking the marker "
                f"(maybe you specified the the wrong one); or 2) using *exactly* the same characters from source; "
                f"or 3) using another marker"
            )
            # TODO check under which circumstances we should return a 1-line range instead of an empty range
            return result
        case Segment(start=s, end=e):
            return segment_to_search_range(lines, s, e, search_range)
        case _ as invalid:
            raise ValueError(f"Unexpected type: {invalid}")


Marker.to_search_range = marker_or_segment_to_search_range_impl
Segment.to_search_range = marker_or_segment_to_search_range_impl


def segment_to_search_range(
        lines: Sequence[str],
        start_relpos: RelativeMarker, end_relpos: RelativeMarker,
        search_range: RangeSpec = RangeSpec.EMPTY
) -> RangeSpec:
    assert len(lines), "`lines` is empty"

    start_match_result = RangeSpec.from_line_marker(lines, start_relpos, search_range)
    assert start_match_result, (
        f"Unable to find segment start `{start_relpos}`; Try: "
        f"1) Double-checking the marker (maybe you specified the the wrong one); or "
        f"2) using *exactly* the same characters from source; or 3) using a marker from above"
    )

    start_index_for_end_marker = start_match_result.as_index
    if start_relpos.qualifier == RelativePositionType.AFTER:
        start_index_for_end_marker += -1
    end_match_result = RangeSpec.from_line_marker(lines, end_relpos, RangeSpec(start_index_for_end_marker, search_range.end, start_match_result.indent))
    assert end_match_result, f"Unable to find segment end `{end_relpos}` - Try: 1) using *exactly* the same characters from source; or 2) using a marker from below"
    if end_match_result.as_index > -1:
        one_after_end = end_match_result.as_index + 1
        end_match_result = RangeSpec(one_after_end, one_after_end, end_match_result.indent)
    return RangeSpec(
        start_match_result.as_index, end_match_result.as_index, start_match_result.indent
    )
