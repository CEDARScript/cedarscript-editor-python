import subprocess
import tempfile
import os
from typing import Union, Sequence
from pathlib import Path


def process_ed_script(file_input: Union[str, Path, Sequence[str]], ed_script: str, is_path: bool = False) -> list[str]:
    """
    Process an ed script on file content or file by streaming to the ed command.

    Args:
        file_input: Either file content as string, path to file, or sequence of strings
        ed_script (str): The ed script commands as a string
        is_path (bool): If True, file_input is treated as a path, otherwise as content

    Returns:
        list[str]: The modified content as a list of strings (lines)

    Raises:
        FileNotFoundError: If is_path is True and the file doesn't exist
        RuntimeError: If ed command fails
    """
    temp_filename = None

    try:
        if is_path:
            # Convert to Path object for better path handling
            file_path = Path(file_input)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            input_file = str(file_path.absolute())
        else:
            # Create a temporary file for the content
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                # Handle both string and sequence input
                if isinstance(file_input, str):
                    temp_file.write(file_input)
                else:
                    temp_file.write('\n'.join(file_input))
                temp_filename = input_file = temp_file.name

        # Run ed with the script as input
        process = subprocess.Popen(
            ['ed', '-s', input_file],  # -s for silent mode
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send the ed script and get output
        _, errors = process.communicate(ed_script + 'w\nq\n')  # write and quit commands

        if process.returncode != 0:
            raise RuntimeError(f"ed failed with error: {errors}")

        # Read the modified content and return as list of strings
        with open(input_file, 'r') as f:
            result = f.read().splitlines()

        return result

    finally:
        # Clean up the temporary file if we created one
        if temp_filename and os.path.exists(temp_filename):
            os.unlink(temp_filename)
