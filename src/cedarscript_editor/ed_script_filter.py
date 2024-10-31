import subprocess
import tempfile
from pathlib import Path
from typing import Sequence

def process_ed_script(content: Sequence[str], ed_script: str) -> list[str]:
    """
    Process an ed script on content using temporary files.

    Args:
        content: Sequence of strings (lines of the file)
        ed_script: The ed script commands as a string

    Returns:
        list[str]: The modified content as a list of strings (lines)

    Raises:
        RuntimeError: If ed command fails
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as content_file:

        # Write content and script to temp files
        content_file.write('\n'.join(content))
        content_file.flush()

        # Run ed
        ed_script = ed_script.strip()
        # 'H' to Enable verbose errors
        match ed_script:
            case '':
                ed_script = 'H\nw\nq'
            case _:
                ed_script = f'H\n{ed_script}\nw\nq'
        process = subprocess.run(
            ['ed', content_file.name],
            input=ed_script,
            capture_output=True,
            text=True
        )

        if process.returncode != 0:
            raise RuntimeError(f"ed failed: {process.stderr or process.stdout}")

        # Read back the modified content
        return Path(content_file.name).read_text().splitlines()
