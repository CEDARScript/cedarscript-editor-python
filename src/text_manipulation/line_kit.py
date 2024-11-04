from typing import Sequence

from collections.abc import Sequence

def get_line_indent_count_from_lines(lines: Sequence[str], index: int) -> int:
    return get_line_indent_count(lines[index])

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
    return line[:get_line_indent_count(line)]
