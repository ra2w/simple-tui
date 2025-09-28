# Headless Mode Documentation

The TUI framework now supports a headless mode that allows you to run commands programmatically and capture a complete transcript of the session, similar to LISP's dribble functionality.

## Overview

Headless mode enables:
- Running commands from scripts or programmatically
- Capturing all input/output to transcript files
- Pre-defining responses for interactive prompts
- Automated testing and batch processing
- Session replay and debugging

## Basic Usage

### Creating a Headless App

```python
from tui.app import App

app = App(
    "my_app",
    headless=True,
    transcript_path=Path("session.md"),
    transcript_format="markdown"  # or "json"
)
```

### Running Commands

```python
# From a list
app.run_script(["/add foo", "/list", "/stats"])

# From a file
app.run_script(Path("commands.txt"))

# From a string
app.run_script("""
/add item1
/add item2 --description "Second item"
/list
""")
```

## Transcript Recording

The transcript captures:
- Command execution with timestamps
- All output (info, ok, warn, err messages)
- UI elements (tables, markdown, text)
- Interactive prompts and responses
- Session metadata

### Markdown Format

```markdown
# TUI Session Transcript
Started: 2024-01-09 10:30:00

## Command: /add foo
> /add foo
✓ Added 'foo'

## Command: /list
> /list
### Items
| ID | Name | Description |
|----|------|-------------|
| 1  | foo  | No description |

Session ended: 2024-01-09 10:30:05
Duration: 5.00 seconds
Commands executed: 2
```

### JSON Format

```json
{
  "session": {
    "start_time": "2024-01-09T10:30:00",
    "end_time": "2024-01-09T10:30:05",
    "duration_seconds": 5.0
  },
  "entries": [
    {
      "type": "command",
      "command": "/add foo",
      "timestamp": "2024-01-09T10:30:00",
      "outputs": [
        {"type": "ok", "content": "Added 'foo'"}
      ]
    }
  ]
}
```

## Handling Interactive Prompts

When commands have arguments with `prompt=True`, headless mode can handle them automatically:

```python
# Define prompt responses
responses = {
    "name": "test_item",
    "Enter description": "Test description"
}

# Run with responses
app.run_script(["/add", "/update"], prompt_responses=responses)
```

### Response Matching

The system tries multiple strategies to match prompts:
1. Exact prompt string match
2. Simplified key (lowercase, underscores)
3. Argument name extraction from "Enter X" prompts

## Script Files

Command scripts support:
- One command per line
- Comments with `#`
- Empty lines ignored

Example `commands.txt`:
```bash
# Add some items
/add apple
/add banana --description "Yellow fruit"

# List and show stats
/list
/stats
```

## CLI Integration

The `demo_headless.py` example shows full CLI integration:

```bash
# Run from script with transcript
python demo_headless.py --script commands.txt --transcript output.md

# Run specific commands
python demo_headless.py -c "/add foo" "/list" -t session.md

# With prompt responses
python demo_headless.py -s interactive.txt -r responses.json -t output.md

# JSON format output
python demo_headless.py -s commands.txt -t output.json -f json

# Fail on first error
python demo_headless.py -s commands.txt -t output.md --fail-fast
```

## Error Handling

Control error behavior with `fail_on_error`:

```python
# Stop on first error (default: True)
app.run_script(commands, fail_on_error=True)

# Continue despite errors
app.run_script(commands, fail_on_error=False)
```

## Use Cases

1. **Automated Testing**: Create test suites that verify command behavior
2. **Batch Processing**: Run multiple operations without user interaction
3. **Documentation**: Generate examples with actual command output
4. **Debugging**: Capture sessions for analysis
5. **CI/CD Integration**: Automate TUI operations in pipelines
6. **Demo Generation**: Create reproducible demonstrations

## API Reference

### App Class

New parameters:
- `headless: bool` - Enable headless mode
- `transcript_path: Optional[Path]` - Path for transcript file
- `transcript_format: str` - "markdown" or "json"

New method:
- `run_script(commands, prompt_responses, fail_on_error)` - Execute commands in headless mode

### TranscriptRecorder Class

Records session activity:
- `record_command(command: str)` - Record a command execution
- `record_output(type: str, content: str)` - Record output messages
- `record_ui_element(type: str, data: dict)` - Record UI elements
- `record_prompt_response(prompt: str, response: str)` - Record interactions
- `finalize()` - Complete and save the transcript

## Best Practices

1. **Use meaningful transcript names**: Include timestamps or test names
2. **Organize scripts**: Group related commands in script files
3. **Version control scripts**: Track command scripts alongside code
4. **Test with responses**: Pre-define all expected prompts
5. **Review transcripts**: Use them for debugging and documentation
6. **Handle errors gracefully**: Consider using `fail_on_error=False` for demos