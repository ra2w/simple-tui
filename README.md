# simple-tui

A streamlit-inspired TUI (Text User Interface) framework with command palette and simple state management.

## Features

- 🎨 Simple runtime: direct state dict, slash commands with typed args, streaming output helpers
- 🔍 Command palette completions: history, paths, choices, numbers, dependent values
- 📊 Rich output helpers: queue Markdown, text, and table elements rendered with Rich
- 🤖 Headless mode with transcript recording for automation and testing

## Installation

### From PyPI (once published)
```bash
pip install simple-tui
```

### For Development
```bash
git clone https://github.com/ra2w/simple-tui
cd simple-tui
pip install -e .
```

### Install with development dependencies
```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from tui import App, Arg, Opt
from tui import completers

app = App("example", title="Example App")
app.state.setdefault("items", [])

@app.on_start
def show_intro(app_instance: App):
    app_instance.markdown("# Welcome! Commands: /add, /list")
    
@app.command("/add", args=[
    Arg("name", str, history=True, prompt=True),
    Opt("desc", str, default="", prompt=True),
])
def add_item(name: str, desc: str = ""):
    app.state["items"].append({"name": name, "desc": desc})
    app.ok(f"Added {name}")
    
app.run()
```

## Building the Package

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# This creates:
# - dist/simple_tui-3.0.0-py3-none-any.whl
# - dist/simple_tui-3.0.0.tar.gz
```

## Publishing to PyPI

```bash
# Test on TestPyPI first
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## API Overview

### Core Components

- `App`: Main application class with state management
- `Arg`/`Opt`: Command argument definitions with completers
- `UI`: Output elements (Header, Markdown, Text, Table)
- Message helpers: `info()`, `ok()`, `warn()`, `err()`

### Built-in Completers

- `completers.choices()`: Fixed list of options
- `completers.numbers()`: Number range completion
- `completers.paths()`: File/directory path completion
- `completers.history()`: Command history completion
- `completers.dependent()`: Context-aware completion

## Documentation

- [API Documentation](docs/API_DOCS.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Cookbook](docs/COOKBOOK.md)
- [Headless Mode Guide](docs/HEADLESS_MODE.md)

## Examples

See the `examples/` directory for more usage examples.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Ramu Arunachalam (ramu@acapital.com)