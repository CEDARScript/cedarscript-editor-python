import re
from .cedarscript_editor_base import CEDARScriptEditorBase

class KotlinCEDARScriptEditor(CEDARScriptEditorBase):
    def _find_function(self, lines, function_name):
        pattern = re.compile(rf'^\s*fun\s+{re.escape(function_name)}\s*[\(<]')
        for i, line in enumerate(lines):
            if pattern.match(line):
                return i
        return None

    def _find_function_end(self, lines, start_index):
        brace_count = 0
        in_string = False
        string_delimiter = None
        for i in range(start_index, len(lines)):
            for char in lines[i]:
                if char in ['"', "'"]:
                    if not in_string:
                        in_string = True
                        string_delimiter = char
                    elif string_delimiter == char:
                        in_string = False
                        string_delimiter = None
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return i + 1
        return len(lines)
