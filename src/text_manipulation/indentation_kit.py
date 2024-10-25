"""
This module provides utilities for analyzing and manipulating indentation in text.

It includes functions and classes for extracting indentation, analyzing indentation
patterns, and adjusting indentation levels in text content. These tools are particularly
useful for processing and formatting source code or other text with structured indentation.

Key components:
- get_line_indent_count: Counts the number of leading whitespace characters in a line.
- extract_indentation: Extracts the leading whitespace from a line.
- IndentationInfo: A class that analyzes and represents indentation patterns in text.

This module is designed to work with various indentation styles, including spaces and tabs,
and can handle inconsistent or mixed indentation patterns.
"""

from collections import Counter
from collections.abc import Sequence
from math import gcd
from typing import NamedTuple


def get_line_indent_count(line: str) -> int:
    """
    Count the number of leading whitespace characters in a line.

    Args:
        line (str): The input line to analyze.

    Returns:
        int: The number of leading whitespace characters.

    Example:
        >>> get_line_indent_count("    Hello")
        4
        >>> get_line_indent_count("\t\tWorld")
        2
    """
    return len(line) - len(line.lstrip())


def extract_indentation(line: str) -> str:
    """
    Extract the leading whitespace from a given line.

    This function identifies and returns the leading whitespace characters
    (spaces or tabs) from the beginning of the input line.

    Args:
        line (str): The input line to process.

    Returns:
        str: The leading whitespace of the line.

    Examples:
        >>> extract_indentation("    Hello")
        '    '
        >>> extract_indentation("\t\tWorld")
        '\t\t'
        >>> extract_indentation("No indentation")
        ''
    """
    return line[:len(line) - len(line.lstrip())]


class IndentationInfo(NamedTuple):
    """
    A class to represent and manage indentation information.

    This class analyzes and provides utilities for working with indentation in text content.
    It detects the indentation character (space or tab), the number of characters used for
    each indentation level, and provides methods to adjust and normalize indentation.

    Attributes:
        char_count (int): The number of characters used for each indentation level.
        char (str): The character used for indentation (' ' for space, '\t' for tab).
        min_indent_level (int): The minimum indentation level found in the analyzed content.
        consistency (bool): Whether the indentation is consistent throughout the content.
        message (str | None): A message describing the indentation analysis results.

    Class Methods:
        from_content: Analyzes the indentation in the given content and creates an IndentationInfo instance.

    Methods:
        level_difference: Calculates the difference in indentation levels.
        char_count_to_level: Converts a character count to an indentation level.
        level_to_chars: Converts an indentation level to a string of indentation characters.
        shift_indentation: Adjusts the indentation of a sequence of lines.
        apply_relative_indents: Applies relative indentation based on annotations in the content.

    Note:
        This class is particularly useful for processing code or text with varying
        or inconsistent indentation, and for adjusting indentation to meet specific
        formatting requirements. It can handle both space and tab indentation, as well
        as mixed indentation styles.

    Example:
        >>> content = "    def example():\n        print('Hello')\n\t\tprint('World')"
        >>> info = IndentationInfo.from_content(content)
        >>> print(info.char, info.char_count, info.consistency)
        ' ' 4 False
    """
    char_count: int
    char: str
    min_indent_level: int
    consistency: bool = True
    message: str | None = None

    @classmethod
    def default(cls) -> 'IndentationInfo':
        return cls(4, ' ', 0)

    @classmethod
    def shift_indentation(cls,
        content: Sequence[str], target_lines: Sequence[str], target_reference_indentation_count: int,
        relindent_level: int | None
    ) -> list[str]:
        """
        Returns 'content' with shifted indentation based on a relative indent level and a reference indentation count.

        This method adjusts the indentation of each non-empty line in the input sequence.
        It calculates the difference between the target base indentation and the minimum
        indentation found in the content, then applies this shift to all lines.

        Args:
            content (Sequence[str]): A sequence of strings representing the lines to be adjusted.
            target_reference_indentation_count (int): The target base indentation count to adjust to.
            relindent_level (int|None):

        Returns:
            list[str]: A new list of strings with adjusted indentation.

        Note:
            - Empty lines and lines with only whitespace are preserved as-is.
            - The method uses the IndentationInfo of the instance to determine
              the indentation character and count.
            - This method is useful for uniformly adjusting indentation across all lines.

        Example:
            >>> info = IndentationInfo(4, ' ', 1, True)
            >>> lines = ["    def example():", "        print('Hello')"]
            >>> info.shift_indentation(content, 8)
            ['        def example():', '            print('Hello')']
        """
        context_indent_char_count = cls.from_content(target_lines).char_count
        return (cls.
            from_content(content).
            _replace(char_count=context_indent_char_count).
            _shift_indentation(
                content, target_lines, target_reference_indentation_count, relindent_level
            )
        )

    def _shift_indentation(self,
        content: Sequence[str], target_lines: Sequence[str], target_base_indentation_count: int, relindent_level: int | None
    ) -> list[str]:
        target_base_indentation_count += self.char_count * (relindent_level or 0)
        raw_line_adjuster = self._shift_indentation_fun(target_base_indentation_count)
        return [raw_line_adjuster(line) for line in content]

    @classmethod
    def from_content(cls, content: str | Sequence[str]) -> 'IndentationInfo':
        """
        Analyzes the indentation in the given content and creates an IndentationInfo instance.

        This method examines the indentation patterns in the provided content,
        determines the dominant indentation character and count, and assesses
        the consistency of indentation throughout the content.

        Args:
            content (str | Sequence[str]): The content to analyze. Can be a string
                                           or a sequence of strings.

        Returns:
            IndentationInfo: An instance of IndentationInfo with the analysis results.

        Note:
            - If no indentation is found, it assumes 4 spaces as per PEP 8.
            - For space indentation, it attempts to determine the most likely
              character count by analyzing patterns and using GCD.
        """
        # TODO Always send str?
        lines = [x for x in content.splitlines() if x.strip()] if isinstance(content, str) else content

        indentations = [extract_indentation(line) for line in lines if line.strip()]
        has_zero_indent = any((i == '' for i in indentations))
        indentations = [indent for indent in indentations if indent]

        if not indentations:
            return cls(4, ' ', 0, True, "No indentation found. Assuming 4 spaces (PEP 8).")

        indent_chars = Counter(indent[0] for indent in indentations)
        dominant_char = ' ' if indent_chars.get(' ', 0) >= indent_chars.get('\t', 0) else '\t'

        indent_lengths = [len(indent) for indent in indentations]

        char_count = 1
        if dominant_char != '\t':
            char_count = cls.calc_space_count_for_indent(indent_lengths)

        min_indent_chars = 0 if has_zero_indent else min(indent_lengths) if indent_lengths else 0
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

        return cls(char_count, dominant_char, min_indent_level, consistency, message)

    @staticmethod
    def calc_space_count_for_indent(indent_lengths: Sequence[int]) -> int:
        # For spaces, determine the most likely char_count
        space_counts = [sc for sc in indent_lengths if sc % 2 == 0]
        if not space_counts:
            return 2  # Default to 2 if no even space counts

        unique_space_counts = sorted(set(space_counts))
        if len(unique_space_counts) == 1:
            return unique_space_counts[0]

        deltas = sorted([b - a for a, b in zip(unique_space_counts, unique_space_counts[1:])], reverse=True)
        most_common_deltas = Counter(deltas).most_common(5)
        ratio_most_common = most_common_deltas[0][1] / len(deltas)
        if ratio_most_common > .6:
            return most_common_deltas[0][0]

        # Resort to GCD
        result = deltas[0]
        # find the largest GCD
        for i in range(1, len(most_common_deltas)):
            new_gcd = gcd(result, most_common_deltas[i][0])
            if new_gcd <= 1:
                break
            result = new_gcd
        return result

    def update_min_indent_level(self, content: str | Sequence[str]) -> 'IndentationInfo':
        return self._replace(min_indent_level=IndentationInfo.from_content(content).min_indent_level)

    def level_difference(self, base_indentation_count: int) -> int:
        """
        Calculate the difference in indentation levels.

        Args:
            base_indentation_count (int): The base indentation count to compare against.

        Returns:
            int: The difference in indentation levels.
        """
        return self.char_count_to_level(base_indentation_count) - self.min_indent_level

    def char_count_to_level(self, char_count: int) -> int:
        """
        Convert a character count to an indentation level.

        Args:
            char_count (int): The number of indentation characters.

        Returns:
            int: The corresponding indentation level.
        """
        return char_count // self.char_count

    def level_to_chars(self, level: int) -> str:
        """
        Convert an indentation level to a string of indentation characters.

        Args:
            level (int): The indentation level.

        Returns:
            str: A string of indentation characters for the given level.
        """
        return level * self.char_count * self.char

    def _shift_indentation_fun(self, target_base_indentation_count: int):
        # Calculate the indentation difference
        level_difference = self.level_difference(target_base_indentation_count)

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

    def apply_relative_indents(self, content: str | Sequence[str], context_indent_count: int = 0) -> list[str]:
        """
        Apply relative indentation based on annotations in the content.

        This method processes the input content, interpreting special annotations
        to apply relative indentation. It uses '@' followed by a number to indicate
        relative indentation levels.

        Args:
            content (str | Sequence[str]): The content to process. Can be a string
                                           or a sequence of strings.
            context_indent_count (int, optional): The base indentation count of the
                                                  context. Defaults to 0.

        Returns:
            list[str]: A new list of strings with normalized indentation (without the annotations)

        Note:
            - Lines starting with '@n:' (where n is an integer) are interpreted as
              having a relative indentation of n levels from the context indent level.
            - Empty lines and lines with only whitespace are removed.
            - The method uses the IndentationInfo of the instance to determine
              the indentation character and count.
            - This method is particularly useful for content with varying
              indentation levels specified by annotations.

        Raises:
            AssertionError: If the calculated indentation level for any line is negative.

        Example:
            >>> info = IndentationInfo(4, ' ', 0, True)
            >>> content = ["@0:def example():", "@1:    print('Hello')", "@2:    if True:", "@3:        print('World')"]
            >>> info.apply_relative_indents(content, 4)
            ['    def example():', '        print('Hello')', '            if True:', '                print('World')']
        """
        # TODO Always send str?
        lines = [l.lstrip() for l in content.splitlines() if l.strip()] if isinstance(content, str) else content

        context_indent_level = self.char_count_to_level(context_indent_count)
        for i in range(len(lines)):
            line = lines[i]
            parts = line.split(':', 1)
            if len(parts) == 2 and parts[0].startswith('@'):
                relative_indent_level = int(parts[0][1:])
                absolute_indent_level = context_indent_level + relative_indent_level
                assert absolute_indent_level >= 0, (
                    f"Final indentation for line `{line.strip()}` cannot be negative "
                    f"({absolute_indent_level})"
                )
                lines[i] = self.level_to_chars(absolute_indent_level) + parts[1].lstrip()
            else:
                absolute_indent_level = context_indent_level
                lines[i] = self.level_to_chars(absolute_indent_level) + line.lstrip()

        return lines


