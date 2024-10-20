# CEDARScript Editor (Python)

[![PyPI version](https://badge.fury.io/py/cedarscript-editor.svg)](https://pypi.org/project/cedarscript-editor/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cedarscript-editor.svg)](https://pypi.org/project/cedarscript-editor/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`CEDARScript Editor (Python)` is a [CEDARScript](https://github.com/CEDARScript/cedarscript-grammar#readme) runtime
for interpreting `CEDARScript` scripts and performing code analysis and modification operations on a codebase.

CEDARScript enables offloading _low-level code syntax and structure concerns_, such as indentation and line counting,
from the LLMs.
The CEDARScript runtime _bears the brunt of file editing_ by locating the exact line numbers and characters to change,
which indentation levels to apply to each line and so on, allowing the _CEDARScript commands_ to focus instead on 
**higher levels of abstraction**, like identifier names, line markers, relative indentations and positions
(`AFTER`, `BEFORE`, `INSIDE` a function, its `BODY`, at the `TOP` or `BOTTOM` of it...).

It acts as an _intermediary_ between the **LLM** and the **codebase**, handling the low-level details of code
manipulation and allowing the AI to focus on higher-level tasks.

## What is CEDARScript?

[CEDARScript](https://github.com/CEDARScript/cedarscript-grammar#readme) (_Concise Examination, Development, And Refactoring Script_)
is a domain-specific language that aims to improve how AI coding assistants interact with codebases and communicate
their code modification intentions.

It provides a standardized way to express complex code modification and analysis operations, making it easier for
AI-assisted development tools to understand and execute these tasks.

## Features

- Given a `CEDARScript` script and a base directory, executes the script commands on files inside the base directory;
- Return results in `XML` format for easier parsing and processing by LLM systems

## Installation

You can install `CEDARScript` Editor using pip:

```
pip install cedarscript-editor
```

## Usage

Here's a quick example of how to use `CEDARScript` Editor:

```python
from cedarscript_editor import CEDARScriptEdior

parser = CEDARScriptEdior()
code = """
CREATE FILE "example.py"
UPDATE FILE "example.py"
    INSERT AT END OF FILE
        CONTENT
            print("Hello, World!")
        END CONTENT
END UPDATE
"""

commands, errors = parser.parse_script(code)

if errors:
    for error in errors:
        print(f"Error: {error}")
else:
    for command in commands:
        print(f"Parsed command: {command}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
