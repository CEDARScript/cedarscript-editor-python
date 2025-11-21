# CEDARScript Editor (Python)

[![PyPI version](https://badge.fury.io/py/cedarscript-editor.svg)](https://pypi.org/project/cedarscript-editor/)
[![Python Versions](https://img.shields.io/pypi/pyversions/cedarscript-editor.svg)](https://pypi.org/project/cedarscript-editor/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

`CEDARScript Editor (Python)` is a [CEDARScript](https://bit.ly/cedarscript) runtime
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

### Python Library

Here's a quick example of how to use `CEDARScript` Editor as a Python library:

```python
from cedarscript_editor import CEDARScriptEditor

editor = CEDARScriptEditor("/path/to/project")

# Parse and execute CEDARScript commands
cedarscript = """```CEDARScript
CREATE FILE "example.py" WITH
"""
print("Hello, World!")
"""
```"""

# Apply commands to the codebase
results = editor.apply_cedarscript(cedarscript)
print(results)
```

### Command Line Interface

`cedarscript-editor` also provides a CLI for executing CEDARScript commands directly from the command line.

#### Installation

After installing via pip, the `cedarscript` command will be available:

```bash
pip install cedarscript-editor
```

#### Basic Usage

```bash
# Execute CEDARScript directly
cedarscript 'CREATE FILE "example.py" WITH "print(\"Hello World\")"'

# Read CEDARScript from file
cedarscript -f commands.cedar
cedarscript --file commands.cedar

# Read from STDIN
cat commands.cedar | cedarscript
echo 'UPDATE FILE "test.py" INSERT LINE 1 "import os"' | cedarscript

# Specify base directory
cedarscript --root /path/to/project -f commands.cedar

# Quiet mode for scripting
cedarscript --quiet -f commands.cedar

# Syntax check only
cedarscript --check -f commands.cedar
```

#### CLI Options

- `-f, --file FILENAME`: Read CEDARScript commands from file
- `--root DIRECTORY`: Base directory for file operations (default: current directory)
- `-q, --quiet`: Minimal output (for scripting)
- `--check`: Syntax check only - parse commands without executing
- `COMMAND`: Direct CEDARScript command (alternative to file input)

#### CEDARScript File Format

CEDARScript commands must be enclosed in fenced code blocks:

````markdown
```CEDARScript
CREATE FILE "example.py" WITH
"""
print("Hello, World!")
"""
```
````

Or use the `<NOCEDARSCRIPT/>` tag for direct command execution:

```cedarscript
<NOCEDARSCRIPT/>
CREATE FILE "example.py" WITH
"""
print("Hello, World!")
"""
```

#### Examples

**Create a new file:**
```bash
cedarscript '```CEDARScript
CREATE FILE "utils.py" WITH
"""
def hello():
    print("Hello from utils!")
"""
```'
```

**Update an existing file:**
```bash
cat > update_commands.cedar << 'EOF'
```CEDARScript
UPDATE FILE "app.py"
INSERT LINE 1
    """Application module"""
INSERT AFTER "import os"
    import sys
```'
EOF

cedarscript -f update_commands.cedar
```

**Multi-file operations:**
```bash
cat > refactor.cedar << 'EOF'
```CEDARScript
# Move method to top level
UPDATE CLASS "DataProcessor"
FROM FILE "data.py"
MOVE METHOD "process"

# Update call sites
UPDATE FUNCTION "main"
FROM FILE "main.py"
REPLACE LINE 5
    result = process(data)
```'
EOF

cedarscript --root ./my-project -f refactor.cedar
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
