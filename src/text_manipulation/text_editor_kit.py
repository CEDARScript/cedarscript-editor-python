"""
This module provides utilities for text editing operations, particularly focused on
working with markers, segments, and range specifications in source code.

It includes functions for file I/O, marker and segment processing, and range
manipulations, which are useful for tasks such as code analysis and transformation.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable
from os import PathLike

from cedarscript_ast_parser import Marker, RelativeMarker, RelativePositionType, Segment, MarkerType, BodyOrWhole
from .range_spec import IdentifierBoundaries, RangeSpec


def read_file(file_path: str | PathLike) -> str:
    """
    Read the contents of a file.

    Args:
        file_path (str | PathLike): The path to the file to be read.

    Returns:
        str: The contents of the file as a string.
    """
    with open(file_path, 'r') as file:
        return file.read()


def write_file(file_path: str | PathLike, lines: Sequence[str]):
    """
    Write a sequence of lines to a file.

    Args:
        file_path (str | PathLike): The path to the file to be written.
        lines (Sequence[str]): The lines to be written to the file.
    """
    with open(file_path, 'w') as file:
        file.writelines([line + '\n' for line in lines])


# def count_leading_chars(line: str, char: str) -> int:
#     return len(line) - len(line.lstrip(char))

def bow_to_search_range(bow: BodyOrWhole, searh_range: IdentifierBoundaries | RangeSpec | None = None) -> RangeSpec:
    """
    Convert a BodyOrWhole specification to a search range.

    Args:
        bow (BodyOrWhole): The BodyOrWhole specification.
        searh_range (IdentifierBoundaries | RangeSpec | None, optional): The search range to use. Defaults to None.

    Returns:
        RangeSpec: The resulting search range.

    Raises:
        ValueError: If an invalid search range is provided.
    """
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
    """
    A protocol for objects that can be converted to an index range.

    This protocol defines the interface for objects that can be converted
    to a RangeSpec based on a sequence of lines and search indices.
    """

    def marker_or_segment_to_index_range(
        self,
        lines: Sequence[str],
        search_start_index: int = 0, search_end_index: int = -1
    ) -> RangeSpec:
        """
        Convert the object to an index range.

        Args:
            lines (Sequence[str]): The lines to search in.
            search_start_index (int, optional): The start index for the search. Defaults to 0.
            search_end_index (int, optional): The end index for the search. Defaults to -1.

        Returns:
            RangeSpec: The resulting index range.
        """
        ...


def marker_or_segment_to_search_range_impl(
    self,
    lines: Sequence[str],
    search_range: RangeSpec = RangeSpec.EMPTY
) -> RangeSpec | None:
    """
    Implementation of the marker or segment to search range conversion.

    This function is used to convert a Marker or Segment object to a RangeSpec.

    Args:
        self: The Marker or Segment object.
        lines (Sequence[str]): The lines to search in.
        search_range (RangeSpec, optional): The initial search range. Defaults to RangeSpec.EMPTY.

    Returns:
        RangeSpec | None: The resulting search range, or None if not found.

    Raises:
        ValueError: If an unexpected type is encountered.
    """
    match self:
        case Marker(type=MarkerType.LINE):
            result = RangeSpec.from_line_marker(lines, self, search_range)
            assert result is not None, (
                f"Unable to find {self}; Try: 1) Double-checking the marker "
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
    """
    Convert a segment defined by start and end relative markers to a search range.

    This function takes a segment defined by start and end relative markers and
    converts it to a RangeSpec that can be used for searching within the given lines.

    Args:
        lines (Sequence[str]): The lines to search in.
        start_relpos (RelativeMarker): The relative marker for the start of the segment.
        end_relpos (RelativeMarker): The relative marker for the end of the segment.
        search_range (RangeSpec, optional): The initial search range. Defaults to RangeSpec.EMPTY.

    Returns:
        RangeSpec: The resulting search range.

    Raises:
        AssertionError: If the lines are empty or if the start or end markers cannot be found.
    """
    assert len(lines), "`lines` is empty"

    match search_range:
        case None:
            search_range = RangeSpec.EMPTY
    start_match_result = RangeSpec.from_line_marker(lines, start_relpos, search_range)
    assert start_match_result, (
        f"Unable to find segment start: {start_relpos}; Try: "
        f"1) Double-checking the marker (maybe you specified the the wrong one); or "
        f"2) Using *exactly* the same characters from source; or 3) using a marker from above"
    )

    start_index_for_end_marker = start_match_result.as_index
    search_range_for_end_marker = search_range
    if end_relpos.marker_subtype != 'number':
        match start_relpos:
            case RelativeMarker(qualifier=RelativePositionType.AFTER):
                start_index_for_end_marker += -1
                search_range_for_end_marker = RangeSpec(
                    start_index_for_end_marker,
                    search_range.end,
                    start_match_result.indent
                )
    end_match_result = RangeSpec.from_line_marker(lines, end_relpos, search_range_for_end_marker)
    assert end_match_result, (
        f"Unable to find segment end: {end_relpos}; Try: "
        f"1) Using *exactly* the same characters from source; or "
        f"2) using a marker from below"
    )
    if end_match_result.as_index > -1:
        one_after_end = end_match_result.as_index + 1
        end_match_result = RangeSpec(one_after_end, one_after_end, end_match_result.indent)
    return RangeSpec(
        start_match_result.as_index, end_match_result.as_index, start_match_result.indent
    )
