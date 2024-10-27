from ._version import __version__
import re
from .cedarscript_editor import CEDARScriptEditor
from cedarscript_ast_parser import CEDARScriptASTParser

__all__ = [
    "__version__", "find_commands", "CEDARScriptEditor"
]


# TODO Move to cedarscript-ast-parser
def find_commands(content: str):
    # Regex pattern to match CEDARScript blocks
    pattern = r'```CEDARScript\n(.*?)```'
    cedar_script_blocks = re.findall(pattern, content, re.DOTALL)
    print(f'[find_cedar_commands] Script block count: {len(cedar_script_blocks)}')
    if len(cedar_script_blocks) == 0 and not content.strip().endswith('<NOCEDARSCRIPT/>'):
        raise ValueError(
            "No CEDARScript block detected. "
            "Perhaps you forgot to enclose the block using ```CEDARScript and ``` ? "
            "Or was that intentional? If so, just write tag <NOCEDARSCRIPT/> as the last line"
        )
    cedarscript_parser = CEDARScriptASTParser()
    for cedar_script in cedar_script_blocks:
        parsed_commands, parse_errors = cedarscript_parser.parse_script(cedar_script)
        if parse_errors:
            raise ValueError(f"CEDARScript parsing errors: {[str(pe) for pe in parse_errors]}")
        for cedar_command in parsed_commands:
            yield cedar_command
