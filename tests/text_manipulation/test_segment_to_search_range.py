import pytest
from cedarscript_ast_parser import RelativeMarker, RelativePositionType, MarkerType
from text_manipulation import RangeSpec
from text_manipulation.text_editor_kit import segment_to_search_range


def test_basic_segment_search():
    # Test input
    lines = """
#
#
#
#
#
#
def _():
    pass
def hello(self):
    print('hello'),
    return None,
    x = 1
""".strip().splitlines()
    content = """
def hello(self, OK):
    # OK !
    """.strip().splitlines()
    expected = """
#
#
#
#
#
#
def _():
    pass
def hello(self, OK):
    # OK !
    print('hello'),
    return None,
    x = 1
""".strip().splitlines()

    # To represent a RangeSpec that starts at line 1 and ends at line 1, we must transform from line numbering to indexes.
    # NOTE: in RangeSpec, we use index values, not line numbers. So for the first line (line 1), the index is 0
    # Also, the end index is EXCLUSIVE, so if you want a range that covers index 0, use RangeSpec(0, 1)

    # We want to restrict our search to start at line 9 which is `def hello(self):` in array 'lines'
    # (so it's index 8) and end after the last line
    search_range = RangeSpec(8, len(lines))

    # Point to line 1 in our search_range (which is line 9 overall which is 'def hello():')
    # The relative_start_marker points to AFTER line 0, which is line 1 in our search_range
    relative_start_marker = RelativeMarker(
        RelativePositionType.AFTER,
        type=MarkerType.LINE,
        value=0, # but as this marker is AFTER, it points to line 1
        marker_subtype='number'
    )
    # The relative_end_marker should point to BEFORE line 2, which is line 1 in our search_range.
    relative_end_marker = relative_start_marker.with_qualifier(RelativePositionType.BEFORE)
    relative_end_marker.value = 2  # but as this marker is BEFORE, it points to line 1

    # So now, both relative_start_marker and relative_end_marker point to line 1 (relative to the search range)
    # In terms of indexes, both point to index 0.
    # When converting this tuple(relative_start_marker, relative_end_marker) to a single absolute RangeSpec,
    # the expected RangeSpec instance should be RangeSpec(2, 3) which means it corresponds to absolute lines
    # from line 3 up to line 3 (inclusive).

    # call the method to search inside the range 'search_range' for the segment
    result: RangeSpec = segment_to_search_range(
        lines, relative_start_marker, relative_end_marker, search_range=search_range
    )
    
    # Verify results
    assert result.start == 8, 'start: should be absolute line 9 (so absolute index 8)'
    assert result.end == 9, "end: should be absolute line 10 (it's exclusive), so should be absolute index 9"
    assert result.indent == 4, "Indent level should be 4, because line 9 has no indentation"

    result.write(content, lines)
    # Check the actual content
    assert lines == expected
