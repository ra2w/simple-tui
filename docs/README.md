# tui (streamlit-inspired command palette, simple state) — v3

- Simple runtime: direct state dict, slash commands with typed args, streaming output helpers.
- Command palette completions: history, paths, choices, numbers, dependent values.
- Rich output helpers: queue Markdown, text, and table elements rendered with Rich.
- **NEW**: Headless mode with transcript recording for automation and testing.

See `API_DOCS.md` for the API, `ARCHITECTURE.md` for internals, and `docs/` for guides.
For headless mode documentation, see `docs/HEADLESS_MODE.md`.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python demo_app.py
```

## Quick Start
```python
from tui.app import App, Arg, Opt
from tui import completers

app = App("example", title="Example", append_only=True, interactive_prompts=True)
app.state.setdefault("items", [])
app.state.setdefault("color", "indigo")

@app.on_start
def show_intro(app_instance: App):
    app_instance.markdown("Commands: /add, /list, /color")
    if not app_instance.state["items"]:
        app_instance.info("No items yet. Use /add to create one.")
    else:
        rows = [
            {"ID": it["id"], "Name": it["name"], "Desc": it["desc"]}
            for it in app_instance.state["items"]
        ]
        app_instance.table("Items", rows, columns=["ID", "Name", "Desc"])

@app.command(
    "/add",
    args=[
        Arg("name", str, history=True, prompt=True),
        Opt("desc", str, default="", prompt=True),
    ],
)
def add(name: str, desc: str = ""):
    items = app.state["items"]
    if any(i["name"] == name for i in items):
        app.err(f"Item '{name}' exists")
        return
    items.append({"id": len(items) + 1, "name": name, "desc": desc})
    app.ok("Added")
    app.table(
        "Items",
        [{"ID": it["id"], "Name": it["name"], "Desc": it["desc"]} for it in items],
        columns=["ID", "Name", "Desc"],
    )

@app.command("/list", args=[])
def list_items():
    items = app.state["items"]
    if not items:
        app.warn("Nothing to list")
        return
    app.table(
        "Items",
        [{"ID": it["id"], "Name": it["name"], "Desc": it["desc"]} for it in items],
        columns=["ID", "Name", "Desc"],
    )

@app.command(
    "/color",
    args=[Arg("value", str, completer=completers.choices("indigo", "green", "orange"))],
)
def set_color(value: str):
    app.state["color"] = value
    app.ok(f"Color set to {value}")

app.run()
```

## Completers
- Completers are plain callables: `(context) -> list[str]`.
- Built-ins: `completers.choices()`, `completers.numbers()`, `completers.paths()`, `completers.history()`, `completers.dependent()`.
- Context keys: `prefix`, `command`, `arg_name`, `tokens`, `state`, `history`, `arg_values`.

## Headless Mode

Run TUI apps programmatically with full transcript recording:

```python
# Create app with headless mode
app = App("my_app", headless=True, transcript_path=Path("session.md"))

# Run commands from script
app.run_script(["/add item1", "/list", "/stats"])

# With interactive prompt responses
app.run_script(
    ["/add", "/update"],
    prompt_responses={"name": "test", "description": "Test item"}
)
```

See `demo_headless.py` for a complete example with CLI integration.

## Philosophy
- Favor explicit, tiny building blocks over heavy abstractions.
- Mutate `app.state` directly; commands are just functions.
- Stream output via `app.ok/info/warn/err`, `app.md`, `app.text`, and `app.table`.
- Keep command handlers fast and defer heavy work elsewhere.

For full documentation, see `API_DOCS.md`.
