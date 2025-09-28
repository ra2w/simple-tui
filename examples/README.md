# Headless Mode Examples

This directory contains examples demonstrating the headless mode functionality.

## Files

- `commands.txt` - Simple command script with no interactive prompts
- `interactive_commands.txt` - Commands that trigger interactive prompts
- `responses.json` - Pre-defined responses for interactive prompts

## Usage Examples

### Run a simple script and save transcript
```bash
python demo_headless.py --script examples/commands.txt --transcript output.md
```

### Run specific commands
```bash
python demo_headless.py --commands "/add foo" "/list" "/stats" --transcript session.md
```

### Run with interactive prompts and responses
```bash
python demo_headless.py --script examples/interactive_commands.txt --responses examples/responses.json --transcript interactive.md
```

### Output in JSON format
```bash
python demo_headless.py --script examples/commands.txt --transcript output.json --format json
```

### Fail on first error
```bash
python demo_headless.py --script examples/commands.txt --transcript output.md --fail-fast
```

## Transcript Output

The transcript captures:
- All executed commands
- Command outputs (info, ok, warn, err messages)
- UI elements (tables, markdown, text)
- Interactive prompts and responses
- Session metadata (start time, duration, command count)

## Response File Format

The responses JSON file maps prompt strings to responses:

```json
{
  "name": "value_for_name_prompt",
  "Enter description": "value_for_description_prompt",
  "simplified_key": "value"
}
```

The system tries multiple matching strategies:
1. Exact prompt match
2. Simplified key (lowercase, underscores for spaces)
3. Argument name extraction from "Enter X" prompts