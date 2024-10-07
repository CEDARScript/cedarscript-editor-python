import re
import os
from .cedarscript_editor_base import CEDARScriptEditorBase

class JavaCEDARScriptEditor(CEDARScriptEditorBase):
    def _find_function(self, lines, function_name):
        # Java method pattern: [modifiers] [return type] methodName(
        pattern = re.compile(rf'^\s*(public|protected|private|static|\s) +[\w<>\[\]]+\s+{re.escape(function_name)}\s*\(')
        for i, line in enumerate(lines):
            if pattern.search(line):
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

    def _create_command(self, command):
        file_path = os.path.join(self.root_path, command['file_path'])
        insert_position = command['insert_position']
        content = command['content']

        with open(file_path, 'r') as file:
            lines = file.readlines()

        marker = insert_position.split('"')[1]
        for i, line in enumerate(lines):
            if marker in line:
                # In Java, we typically want to insert methods inside a class
                class_indent = len(line) - len(line.lstrip())
                indented_content = '\n'.join(' ' * (class_indent + 4) + l for l in content.split('\n'))
                lines.insert(i + 1, indented_content + '\n\n')
                break

        with open(file_path, 'w') as file:
            file.writelines(lines)

        return f"Created method in {command['file_path']}"
