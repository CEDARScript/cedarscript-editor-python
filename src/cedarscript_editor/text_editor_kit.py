import re
from collections import Counter
from collections.abc import Sequence
from typing import NamedTuple, Protocol, runtime_checkable
from math import gcd

from cedarscript_ast_parser import Marker, RelativeMarker, RelativePositionType, Segment, MarkerType, BodyOrWhole

def read_file(file_path: str) -> str:
    with open(file_path, 'r') as file:
        return file.read()


def write_file(file_path: str, lines: Sequence[str]):
    with open(file_path, 'w') as file:
        file.writelines([line + '\n' for line in lines])


class RangeSpec(NamedTuple):
    start: int
    end: int
    indent: int = 0

    def __str__(self):
        return (f'{self.start}:{self.end}' if self.as_index is None else f'%{self.as_index}') + f'@{self.indent}'

    @property
    def as_index(self) -> int | None:
        return self.start if self.start == self.end else None

    @property
    def collapsed(self):
        return self.set_length(0)

    def set_length(self, range_len: int):
        return self._replace(end=self.start + range_len)

    def inc(self, count: int = 1):
        return self._replace(start=self.start + count, end=self.end + count)

    def dec(self, count: int = 1):
        return self._replace(start=self.start - count, end=self.end - count)

    def read[S: Sequence[str]](self, src: S) -> S:
        return src[self.start:self.end]

    def write[S: Sequence[str]](self, src: S, target: S):
        target[self.start:self.end] = src

    def delete[S: Sequence[str]](self, src: S) -> S:
        result = self.read(src)
        del src[self.start:self.end]
        return result



MATCH_TYPES = ('exact', 'stripped', 'normalized', 'partial')


class IdentifierBoundaries(NamedTuple):
    whole: RangeSpec
    body: RangeSpec

    def __str__(self):
        return f'IdentifierBoundaries({self.whole} (BODY: {self.body}) )'

    @property
    def start_line(self) -> int:
        return self.whole.start + 1

    @property
    def body_start_line(self) -> int:
        return self.body.start + 1

    @property
    def end_line(self) -> int:
        return self.whole.end

    # See the other bow_to_search_range
    def location_to_search_range(self, location: BodyOrWhole | RelativePositionType) -> RangeSpec:
        match location:
            case BodyOrWhole.BODY:
                return self.body
            case BodyOrWhole.WHOLE | RelativePositionType.AT:
                return self.whole
            case RelativePositionType.BEFORE:
                return RangeSpec(self.whole.start, self.whole.start, self.whole.indent)
            case RelativePositionType.AFTER:
                return RangeSpec(self.whole.end, self.whole.end, self.whole.indent)
            case RelativePositionType.INSIDE_TOP:
                return RangeSpec(self.body.start, self.body.start, self.body.indent)
            case RelativePositionType.INSIDE_BOTTOM:
                return RangeSpec(self.body.end, self.body.end, self.body.indent)
            case _ as invalid:
                raise ValueError(f"Invalid: {invalid}")


def bow_to_search_range(bow: BodyOrWhole, searh_range: IdentifierBoundaries | RangeSpec | None = None, lines: Sequence[str] | None = None) -> RangeSpec:
    match searh_range:

        case RangeSpec() | None:
            return searh_range or RangeSpec(0, -1, 0)

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
    search_range: RangeSpec = RangeSpec(0, -1, 0)
) -> RangeSpec | None:
    match self:
        case Marker(type=MarkerType.LINE):
            result = find_line_index_and_indent(lines, self, search_range)
            assert result, f"Unable to find `{self}`; Try: 1) Double-checking the marker (maybe you specified the the wrong one); or 2) using *exactly* the same characters from source; or 3) using another marker"
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
        search_range: RangeSpec = RangeSpec(0, -1, 0)
) -> RangeSpec:
    assert len(lines), "`lines` is empty"

    start_match_result = find_line_index_and_indent(lines, start_relpos, search_range)
    assert start_match_result, f"Unable to find segment start `{start_relpos}`; Try: 1) Double-checking the marker (maybe you specified the the wrong one); or 2) using *exactly* the same characters from source; or 3) using a marker from above"

    start_index_for_end_marker = start_match_result.as_index
    if start_relpos.qualifier == RelativePositionType.AFTER:
        start_index_for_end_marker += -1
    end_match_result = find_line_index_and_indent(lines, end_relpos, RangeSpec(start_index_for_end_marker, search_range.end, start_match_result.indent))
    assert end_match_result, f"Unable to find segment end `{end_relpos}` - Try: 1) using *exactly* the same characters from source; or 2) using a marker from below"
    if end_match_result.as_index > -1:
        one_after_end = end_match_result.as_index + 1
        end_match_result = RangeSpec(one_after_end, one_after_end, end_match_result.indent)
    return RangeSpec(
        start_match_result.as_index, end_match_result.as_index, start_match_result.indent
    )


def get_line_indent_count(line: str):
    return len(line) - len(line.lstrip())


def count_leading_chars(line: str, char: str) -> int:
    return len(line) - len(line.lstrip(char))


def normalize_line(line: str):
    return re.sub(r'[^\w]', '.', line.strip(), flags=re.UNICODE)


def find_line_index_and_indent(
    lines: Sequence[str],
    search_term: Marker | RelativeMarker,
    search_range: RangeSpec = RangeSpec(0, -1, 0)
) -> RangeSpec | None:
    """
    Find the index of a specified line within a list of strings, considering different match types and an offset.

    This function searches for a given line within a list, considering 4 types of matches in order of priority:
    1. Exact match
    2. Stripped match (ignoring leading and trailing whitespace)
    3. Normalized match (ignoring non-alphanumeric characters)
    4. Partial (Searching for a substring, using `casefold` to ignore upper- and lower-case differences.

    The function applies the offset across all match types while maintaining the priority order.

    :Args:
        :param lines: The list of strings to search through.
        :param search_term:
            search_marker.value: The line to search for.
            search_marker.offset: The number of matches to skip before returning a result.
                      0 skips no match and returns the first match, 1 returns the second match, and so on.
        :param search_range: The index to start the search from. Defaults to 0. The index to end the search at (exclusive).
                              Defaults to (0, -1), which means search to the end of the list.

    :returns:
        RangeSpec: The index for the desired line in the 'lines' list.
             Returns None if no match is found or if the offset exceeds the number of matches within each category.

    :Example:
        >> lines = ["Hello, world!", "  Hello, world!  ", "Héllo, wörld?", "Another line", "Hello, world!"]
        >> _find_line_index(lines, "Hello, world!", 1)
        4  # Returns the index of the second exact match

    Note:
        - The function prioritizes match types in the order: exact, stripped, normalized, partial.
        - The offset is considered separately for each type.
    """
    search_start_index, search_end_index, _ = search_range
    search_line = search_term.value
    assert search_line, "Empty marker"
    assert search_term.type == MarkerType.LINE, f"Invalid marker type: {search_term.type}"

    matches = {t: [] for t in MATCH_TYPES}

    stripped_search = search_line.strip()
    normalized_search_line = normalize_line(stripped_search)

    if search_start_index < 0:
        search_start_index = 0
    if search_end_index < 0:
        search_end_index = len(lines)

    assert search_start_index < len(lines), f"search start index ({search_start_index}) must be less than line count ({len(lines)})"
    assert search_end_index <= len(lines), f"search end index ({search_end_index}) must be less than or equal to line count ({len(lines)})"

    for i in range(search_start_index, search_end_index):
        line = lines[i]
        reference_indent = get_line_indent_count(line)

        # Check for exact match
        if search_line == line:
            matches['exact'].append((i, reference_indent))

        # Check for stripped match
        elif stripped_search == line.strip():
            matches['stripped'].append((i, reference_indent))

        # Check for normalized match
        elif normalized_search_line == normalize_line(line):
            matches['normalized'].append((i, reference_indent))

        # Last resort!
        elif normalized_search_line.casefold() in normalize_line(line).casefold():
            matches['partial'].append((i, reference_indent))

    offset = search_term.offset or 0
    for match_type in MATCH_TYPES:
        if offset < len(matches[match_type]):
            index, reference_indent = matches[match_type][offset]
            match match_type:
                case 'normalized':
                    print(f'Note: using {match_type} match for {search_term}')
                case 'partial':
                    print(f"Note: Won't accept {match_type} match at index {index} for {search_term}")
                    continue
            if isinstance(search_term, RelativeMarker):
                match search_term.qualifier:
                    case RelativePositionType.BEFORE:
                        index += -1
                    case RelativePositionType.AFTER:
                        index += 1
                    case RelativePositionType.AT:
                        pass
                    case _ as invalid:
                        raise ValueError(f"Not implemented: {invalid}")
            return RangeSpec(index, index, reference_indent)

    return None


class IndentationInfo(NamedTuple):
    char_count: int
    char: str
    min_indent_level: int
    consistency: bool = True
    message: str | None = None

    def level_difference(self, base_indentation_count: int):
        return self.char_count_to_level(base_indentation_count) - self.min_indent_level

    def char_count_to_level(self, char_count: int) -> int:
        return char_count // self.char_count

    def level_to_chars(self, level: int) -> str:
        return level * self.char_count * self.char

    def adjust_indentation_in_raw_lines(self, lines: Sequence[str], base_indentation_count: int) -> list[str]:
        raw_line_adjuster = self._adjust_indentation_fun(base_indentation_count)
        # Return the transformed lines
        return [raw_line_adjuster(line) for line in lines]

    def _adjust_indentation_in_raw_lines_fun(self, base_indentation_count: int):
        # Calculate the indentation difference
        level_difference = self.level_difference(base_indentation_count)

        def adjust_line(line: str) -> str:
            if not line.strip():
                # Handle empty lines or lines with only whitespace
                return line

            current_indent_count = get_line_indent_count(line)
            current_level = self.char_count_to_level(current_indent_count)
            new_level = max(0, current_level + level_difference)
            new_indent = self.level_to_chars(new_level)

            return new_indent + line.lstrip()
        return adjust_line

def normalize_indent[S: Sequence[str]](content: str | S, context_indent_count: int = 0, indentation_info: IndentationInfo | None = None) -> list[str]:
    # TODO Always send str?
    lines = [line.lstrip() for line in content.splitlines() if line.strip()] if isinstance(content, str) else content

    context_indent_level = indentation_info.char_count_to_level(context_indent_count)
    for i in range(len(lines)):
        line = lines[i]
        parts = line.split(':', 1)
        if len(parts) == 2 and parts[0].startswith('@'):
            relative_indent_level = int(parts[0][1:])
            absolute_indent_level = context_indent_level + relative_indent_level
            assert absolute_indent_level >= 0, f"Final indentation for line `{line.strip()}` cannot be negative ({absolute_indent_level})"
            lines[i] = indentation_info.level_to_chars(absolute_indent_level) + parts[1].lstrip()
        else:
            absolute_indent_level = context_indent_level
            lines[i] = indentation_info.level_to_chars(absolute_indent_level) + line.lstrip()

    return lines


def analyze_and_adjust_indentation[S: Sequence[str]](src_content_to_adjust: str | S, target_context_for_analysis: str | S, base_indentation_count: int) -> S:
    return analyze_indentation(target_context_for_analysis).adjust_indentation_in_raw_lines(src_content_to_adjust, base_indentation_count)

def analyze_and_normalize_indentation[S: Sequence[str]](src_content_to_adjust: str | S, target_context_for_analysis: str | S, context_indent_count: int = 0) -> S:
    indentation_info: IndentationInfo = analyze_indentation(target_context_for_analysis)
    return normalize_indent(src_content_to_adjust, context_indent_count, indentation_info)


def analyze_indentation[S: Sequence[str]](content: str | S) -> IndentationInfo:
    # TODO Always send str?
    lines = [line.lstrip() for line in content.splitlines() if line.strip()] if isinstance(content, str) else content

    def extract_indentation(line: str) -> str:
        return re.match(r'^\s*', line).group(0)

    indentations = [extract_indentation(line) for line in lines if line.strip()]

    if not indentations:
        return IndentationInfo(4, ' ', 0, True, "No indentation found. Assuming 4 spaces (PEP 8).")

    indent_chars = Counter(indent[0] for indent in indentations if indent)
    dominant_char = ' ' if indent_chars.get(' ', 0) >= indent_chars.get('\t', 0) else '\t'

    indent_lengths = [len(indent) for indent in indentations]

    if dominant_char == '\t':
        char_count = 1
    else:
        # For spaces, determine the most likely char_count
        space_counts = [len for len in indent_lengths if len % 2 == 0 and len > 0]
        if not space_counts:
            char_count = 2  # Default to 2 if no even space counts
        else:
            # Sort top 5 space counts and find the largest GCD
            sorted_counts = sorted([c[0] for c in Counter(space_counts).most_common(5)], reverse=True)
            char_count = sorted_counts[0]
            for i in range(1, len(sorted_counts)):
                new_gcd = gcd(char_count, sorted_counts[i])
                if new_gcd <= 1:
                    break
                char_count = new_gcd

    min_indent_chars = min(indent_lengths) if indent_lengths else 0
    min_indent_level = min_indent_chars // char_count

    consistency = all(len(indent) % char_count == 0 for indent in indentations if indent)
    match dominant_char:
        case ' ':
            domcharstr = 'space'
        case '\t':
            domcharstr = 'tab'
        case _:
            domcharstr = dominant_char
    message = f"Found {char_count}-{domcharstr} indentation"
    if not consistency:
        message += " (inconsistent)"

    return IndentationInfo(char_count, dominant_char, min_indent_level, consistency, message)

