import re
import shutil
import tempfile
import pytest
from pathlib import Path

from cedarscript_editor import find_commands, CEDARScriptEditor


def get_test_cases() -> list[str]:
    """Get all test cases from tests/corpus directory.
    
    Returns:
    list[str]: Names of all test case directories in the corpus
    """
    corpus_dir = Path(__file__).parent / 'corpus'
    result = [d.name for d in corpus_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    exclusive = [d for d in result if d.casefold().startswith('x.')]
    return exclusive or result


@pytest.fixture
def editor(tmp_path_factory):
    """Fixture providing a CEDARScriptEditor instance with a temporary directory.
    
    The temporary directory is preserved if the test fails, to help with debugging.
    It is automatically cleaned up if the test passes.
    """
    # Create temp dir under the project's 'out' directory
    out_dir = Path(__file__).parent.parent / 'out'
    out_dir.mkdir(exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix='test-', dir=out_dir))
    editor = CEDARScriptEditor(temp_dir)
    yield editor
    # Directory will be preserved if test fails (pytest handles this automatically)
    if not hasattr(editor, "_failed"):  # No failure occurred
        shutil.rmtree(temp_dir)


@pytest.mark.parametrize('test_case', get_test_cases())
def test_corpus(editor: CEDARScriptEditor, test_case: str):
    """Test CEDARScript commands from chat.xml files in corpus."""
    try:
        corpus_dir = Path(__file__).parent / 'corpus'
        test_dir = corpus_dir / test_case

        # Create scratch area for this test
        # Copy all files from test dir to scratch area, except chat.xml and expected.*
        def copy_files(src_dir: Path, dst_dir: Path):
            for src in src_dir.iterdir():
                if src.name == 'chat.xml' or src.name.startswith('expected.'):
                    continue
                dst = dst_dir / src.name
                if src.is_dir():
                    dst.mkdir(exist_ok=True)
                    copy_files(src, dst)
                else:
                    shutil.copy2(src, dst)

        copy_files(test_dir, editor.root_path)

        # Read chat.xml
        chat_xml = (test_dir / 'chat.xml').read_text()

        # Find and apply commands
        commands = list(find_commands(chat_xml))
        assert commands, "No commands found in chat.xml"
        
        # Check if test expects an exception
        throws_match = re.search(r'<throws value="([^"]+)">', chat_xml)
        if throws_match:
            expected_error = throws_match.group(1)
            with pytest.raises(Exception) as excinfo:
                editor.apply_commands(commands)
            # TODO excinfo.value is '<description>Unable to find function 'does-not-exist'</description>'
            actual_error = str(excinfo.value)
            match re.search(r'<description>(.+)</description>', actual_error):
                case None:
                    pass
                case _ as found:
                    actual_error = found.group(1)
            assert actual_error == expected_error, f"Expected error '{expected_error}', but got '{actual_error}'"
        else:
            editor.apply_commands(commands)

        def check_expected_files(dir_path: Path):
            for path in dir_path.iterdir():
                if path.is_dir():
                    check_expected_files(path)
                    continue
                # Find corresponding expected file in test directory
                rel_path = path.relative_to(editor.root_path)
                if str(rel_path).startswith("."):
                    continue
                expected_file = test_dir / f"expected.{rel_path}"
                assert expected_file.exists(), f"'expecteed.*' file not found: {expected_file}"

                expected_content = file_to_lines(expected_file, rel_path)
                actual_content = file_to_lines(path, rel_path)
                assert actual_content == expected_content, \
                    f"Output does not match expected content for {rel_path}"

        check_expected_files(editor.root_path)

    except Exception:
        editor._failed = True  # Mark as failed to preserve temp directory
        raise


def file_to_lines(file_path, rel_path):
    expected_content = [f"#{i} [{rel_path}]{c}" for i, c in enumerate(file_path.read_text().splitlines())]
    return expected_content

