#!/usr/bin/env python3
"""
CEDARScript Editor CLI Interface

Provides command-line interface for executing CEDARScript commands
on code files using the CEDARScript Editor library.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from cedarscript_ast_parser import CEDARScriptASTParser

from .cedarscript_editor import CEDARScriptEditor, CEDARScriptEditorException
from . import find_commands


@click.command(help="Execute CEDARScript commands on code files")
@click.option(
    '--file', '-f',
    type=click.File('r'),
    help='Read CEDARScript commands from file'
)
@click.option(
    '--root', '-r',
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=Path.cwd(),
    help='Base directory for file operations (default: current directory)'
)
@click.option(
    '--quiet', '-q',
    is_flag=True,
    help='Minimal output (for scripting)'
)
@click.option(
    '--check', '-c',
    is_flag=True,
    help='Syntax check only - parse commands without executing'
)
@click.option(
    '--fenced', '-F',
    is_flag=True,
    default=False,
    help='Require CEDARScript blocks to be fenced with ```CEDARScript (default: treat entire input as single block)'
)
@click.argument('command', required=False)
def main(
    file: Optional[click.File],
    root: Path,
    quiet: bool,
    check: bool,
    fenced: bool,
    command: Optional[str]
) -> None:
    """
    CEDARScript Editor CLI

    Execute CEDARScript commands to transform code files.

    Examples:
        \b
        # Direct command
        cedarscript "UPDATE myfile.py SET imports.append('import os')"

        # From file (both short and long forms)
        cedarscript -f commands.cedar
        cedarscript --file commands.cedar

        # From STDIN
        cat commands.cedar | cedarscript

        # With custom base directory
        cedarscript -r /path/to/project -f commands.cedar
        cedarscript --root /path/to/project -f commands.cedar

        # Quiet mode for scripting
        cedarscript -q -f commands.cedar
        cedarscript --quiet -f commands.cedar

        # Syntax check only
        cedarscript -c -f commands.cedar
        cedarscript --check -f commands.cedar

        # With fenced requirement
        cedarscript -F -f commands.cedar
        cedarscript --fenced -f commands.cedar

        # Mixed short and long flags
        cedarscript -r /path/to -c -F --file commands.cedar
    """
    try:
        # Determine command source
        commands = _get_commands_input(file, command, quiet)

        if not commands.strip():
            _echo_error("No CEDARScript commands provided", quiet)
            sys.exit(1)

        # Parse commands
        if not quiet:
            click.echo("Parsing CEDARScript commands...")

        try:
            parsed_commands = list(find_commands(commands, require_fenced=fenced))
        except Exception as e:
            _echo_error(f"Failed to parse CEDARScript: {e}", quiet)
            sys.exit(1)

        if not quiet:
            click.echo(f"Parsed {len(parsed_commands)} command(s)")

        # If syntax check only, exit here
        if check:
            if not quiet:
                click.echo("Syntax check passed - commands are valid")
            sys.exit(0)

        # Execute commands
        if not quiet:
            click.echo(f"Executing commands in directory: {root}")

        editor = CEDARScriptEditor(str(root))
        results = editor.apply_commands(parsed_commands)

        # Output results
        if not quiet:
            click.echo("\nResults:")
            for result in results:
                click.echo(f"  {result}")
        else:
            # Quiet mode - just show success/failure
            click.echo(f"Applied {len(results)} command(s)")

    except CEDARScriptEditorException as e:
        _echo_error(f"CEDARScript execution error: {e}", quiet)
        sys.exit(2)
    except KeyboardInterrupt:
        _echo_error("Operation cancelled by user", quiet)
        sys.exit(130)
    except Exception as e:
        _echo_error(f"Unexpected error: {e}", quiet)
        sys.exit(3)


def _get_commands_input(
    file: Optional[click.File],
    command: Optional[str],
    quiet: bool
) -> str:
    """
    Determine the source of CEDARScript commands based on provided inputs.

    Priority: command argument > file option > STDIN
    """
    if command:
        return command

    if file:
        return file.read()

    # Check if STDIN has data (not a TTY)
    if not sys.stdin.isatty():
        try:
            return sys.stdin.read()
        except Exception as e:
            _echo_error(f"Error reading from STDIN: {e}", quiet)
            sys.exit(1)

    return ""


def _echo_error(message: str, quiet: bool) -> None:
    """Echo error message with appropriate formatting."""
    if quiet:
        # In quiet mode, send errors to stderr but keep them brief
        click.echo(f"Error: {message}", err=True)
    else:
        # In normal mode, use styled error output
        click.echo(click.style(f"Error: {message}", fg='red'), err=True)


if __name__ == '__main__':
    main()