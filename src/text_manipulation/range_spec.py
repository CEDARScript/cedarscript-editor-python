"""
This module provides utilities for working with ranges of text in source code.

It includes classes and functions for specifying ranges, finding lines,
and manipulating text within those ranges. The main components are:

- RangeSpec: A class representing a range of lines in a text.
- IdentifierBoundaries: A class representing the boundaries of an identifier in code.
- Various utility functions for working with these classes and text manipulation.
"""

import re
from collections.abc import Sequence
from typing import NamedTuple, TypeAlias
from functools import total_ordering


from cedarscript_ast_parser import Marker, RelativeMarker, RelativePositionType, MarkerType, BodyOrWhole

from .indentation_kit import get_line_indent_count

MATCH_TYPES = ('exact', 'stripped', 'normalized', 'partial')


@total_ordering
class RangeSpec(NamedTuple):
    """
    Represents a range of lines in a text, with 0-based start and end indices and indentation.

    This class is used to specify a range of lines in a text, typically for
    text manipulation operations. It includes methods for comparing ranges,
    modifying the range, and performing operations on text using the range.

    Attributes:
        start (int): The starting 0-based index of the range.
        end (int): The ending 0-based index of the range (exclusive).
        indent (int): The indentation level at the start of the range.
    """
    start: int
    end: int
    indent: int = 0

    def __str__(self):
        return (f'{self.start}:{self.end}' if self.as_index is None else f'%{self.as_index}') + f'@{self.indent}'

    def __lt__(self, other):
        """Compare if this range is strictly before another range or int."""
        match other:
            case int():
                return self.end <= other
            case RangeSpec():
                return self.end <= other.start

    def __le__(self, other):
        """Compare if this range is before or adjacent to another range."""
        match other:
            case int():
                return self.end <= other - 1
            case RangeSpec():
                return self.end <= other.start - 1

    def __gt__(self, other):
        """Compare if this range is strictly after another range."""
        match other:
            case int():
                return self.start > other
            case RangeSpec():
                return self.start >= other.end

    def __ge__(self, other):
        """Compare if this range is after or adjacent to another range."""
        match other:
            case int():
                return self.start >= other
            case RangeSpec():
                return self.start >= other.end - 1

    def __contains__(self, item):
        match item:
            case int():
                return self.start <= item < self.end
            case RangeSpec():
                return self == RangeSpec.EMPTY or item != RangeSpec.EMPTY and self.start <= item.start and item.end <= self.end

    @property
    def line_count(self):
        """Return the number of lines in the range."""
        return self.end - self.start

    @property
    def as_index(self) -> int | None:
        """Return the start index if the range is empty, otherwise None."""
        return None if self.line_count else self.start

    @property
    def collapsed(self):
        """Return a new RangeSpec with the same start but zero length."""
        return self.set_line_count(0)

    def set_line_count(self, range_len: int):
        """Return a new RangeSpec with the specified line count by adjusting its end."""
        return self._replace(end=self.start + range_len)

    def inc(self, count: int = 1):
        """Return a new RangeSpec shifted forward by the specified count."""
        return self._replace(start=self.start + count, end=self.end + count)

    def dec(self, count: int = 1):
        """Return a new RangeSpec shifted backward by the specified count."""
        return self._replace(start=self.start - count, end=self.end - count)

    def read(self, src: Sequence[str]) -> Sequence[str]:
        """Read and return the lines from the source sequence specified by this range."""
        return src[self.start:self.end]

    def write(self, src: Sequence[str], target: Sequence[str]):
        """Write the source lines into the target sequence at the index position specified by this range."""
        target[self.start:self.end if self.end >= 0 else len(target)] = src

    def delete(self, src: Sequence[str]) -> Sequence[str]:
        """Delete the lines specified by this range from the source sequence and return the deleted lines."""
        result = self.read(src)
        del src[self.start:self.end]
        return result

    @staticmethod
    def normalize_line(line: str):
        """Normalize a line by replacing non-word characters with dots and stripping whitespace."""
        return re.sub(r'[^\w]', '.', line.strip(), flags=re.UNICODE)

    @classmethod
    def from_line_marker(
            cls,
            lines: Sequence[str],
            search_term: Marker,
            search_range: 'RangeSpec' = None
    ):
        """
        Find the index of a specified line within a list of strings, considering different match types and an offset.

        This method searches for a given line within a list, considering 4 types of matches in order of priority:
        1. Exact match
        2. Stripped match (ignoring leading and trailing whitespace)
        3. Normalized match (ignoring non-alphanumeric characters)
        4. Partial (Searching for a substring, using `casefold` to ignore upper- and lower-case differences).

        The method applies the offset across all match types while maintaining the priority order.

        Args:
            lines (Sequence[str]): The list of strings to search through.
            search_term (Marker): A Marker object containing:
                - value: The line to search for.
                - offset: The number of matches to skip before returning a result.
                          0 skips no match and returns the first match, 1 returns the second match, and so on.
            search_range (RangeSpec, optional): The range to search within. Defaults to None, which means
            search the entire list.

        Returns:
            RangeSpec: A RangeSpec object representing the found line, or None if no match is found.

        Raises:
            ValueError: If there are multiple matches and no offset is specified, or if the offset exceeds the
            number of matches.

        Note:
            - The method prioritizes match types in the order: exact, stripped, normalized, partial.
            - The offset is considered separately for each match type.
        """
        search_start_index, search_end_index, _ = search_range if search_range is not None else (0, -1, 0)
        search_line = search_term.value
        assert search_line, "Empty marker"
        assert search_term.type == MarkerType.LINE, f"Invalid marker type: {search_term.type}"

        matches = {t: [] for t in MATCH_TYPES}

        stripped_search = search_line.strip()
        normalized_search_line = cls.normalize_line(stripped_search)

        if search_start_index < 0:
            search_start_index = 0
        if search_end_index < 0:
            search_end_index = len(lines)

        assert search_start_index < len(lines), (
            f"search start index ({search_start_index}) "
            f"must be less than line count ({len(lines)})"
        )
        assert search_end_index <= len(lines), (
            f"search end index ({search_end_index}) "
            f"must be less than or equal to line count ({len(lines)})"
        )

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
            elif normalized_search_line == cls.normalize_line(line):
                matches['normalized'].append((i, reference_indent))

            # Dangerous! Last resort!
            elif normalized_search_line.casefold() in cls.normalize_line(line).casefold():
                matches['partial'].append((i, reference_indent))

        offset = search_term.offset or 0
        max_match_count = max([len(m) for m in matches.values()])
        for match_type in MATCH_TYPES:
            match_type_count = len(matches[match_type])
            if search_term.offset is None and match_type_count > 1:
                raise ValueError(
                    f"Line marker `{search_term.value}` is ambiguous (found {match_type_count} lines matching it) "
                    "Suggestions: 1) To disambiguate, try using a *different line* as marker (a couple lines before or "
                    "after the one you tried); 2) If you wanted to *REPLACE* line, try instead to replace a *SEGMENT* "
                    "a couple of lines long."
                    # f"Add an `OFFSET` (after the line marker) and a number between 0 and {match_type_count - 1}
                    # to determine how many to skip. "
                    # f"Example to reference the *last* one of those:
                    # `LINE '{search_term.value.strip()}' OFFSET {match_type_count - 1}`"
                    # ' (See `offset_clause` in `<grammar.js>` for details on OFFSET)'
                )

            if match_type_count and offset >= max_match_count:
                raise ValueError(
                    f"There are only {max_match_count} lines matching `{search_term.value}`, "
                    f"but 'OFFSET' was set to {search_term.offset} (you can skip at most {match_type_count-1} of those)"
                )

            if offset < match_type_count:
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
                return cls(index, index, reference_indent)

        return None


RangeSpec.EMPTY = RangeSpec(0, -1, 0)


class ParentInfo(NamedTuple):
    parent_name: str
    parent_type: str

ParentRestriction: TypeAlias = RangeSpec | str | None

class IdentifierBoundaries(NamedTuple):
    """
    Represents the boundaries of an identifier in code, including its whole range and body range.

    This class is used to specify the range of an entire identifier (whole) and its body,
    which is typically the content inside the identifier's definition.

    Attributes:
        whole (RangeSpec): The RangeSpec representing the entire identifier.
        body (RangeSpec): The RangeSpec representing the body of the identifier.
    """

    whole: RangeSpec
    body: RangeSpec | None = None
    docstring: RangeSpec | None = None
    decorators: list[RangeSpec] = []
    parents: list[ParentInfo] = []

    def __str__(self):
        return f'IdentifierBoundaries({self.whole} (BODY: {self.body}) )'

    @property
    def start_line(self) -> int:
        """Return the 1-indexed start line of the whole identifier."""
        return self.whole.start + 1

    @property
    def body_start_line(self) -> int:
        """Return the 1-indexed start line of the identifier's body."""
        return self.body.start + 1

    @property
    def end_line(self) -> int:
        """Return the 1-indexed end line of the whole identifier."""
        return self.whole.end

    def match_parent(self, parent_restriction: ParentRestriction) -> bool:
        match parent_restriction:
            case None:
                return True
            case RangeSpec():
                return self.whole in parent_restriction
            case str() as parent_name:
                # TODO Implement advanced query syntax
                return parent_name in [p.parent_name for p in self.parents]
            case _:
                raise ValueError(f'Invalid parent restriction: {parent_restriction}')

    def location_to_search_range(self, location: BodyOrWhole | RelativePositionType) -> RangeSpec:
        """
        Convert a location specifier to a RangeSpec for searching.

        This method interprets various location specifiers and returns the appropriate
        RangeSpec for searching within or around the identifier.

        Args:
            location (BodyOrWhole | RelativePositionType): The location specifier.

        Returns:
            RangeSpec: The corresponding RangeSpec for the specified location.

        Raises:
            ValueError: If an invalid location specifier is provided.
        """
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
