# TUI Developer Guide (v3, Comprehensive)

This guide explains how to build terminal UIs with the `tui` v3 runtime. It focuses on clarity and composable building blocks so teams can ship quickly and safely.

## Concepts
- App: `App(id, title=None, append_only=True, interactive_prompts=False)` wires the runtime, registry, history store, and console together.
- State: `app.state` is a plain dict you mutate directly; there is no commit or staging layer.
- Commands: declare slash commands with typed arguments; the same spec powers parsing and completions.
- Completers: small functions that map context to suggestions; built-ins cover choices, numbers, paths, history, and dependent lookups.
- Lifecycle hooks: `on_start`, `before_prompt`, and `after_prompt` let you enqueue UI or instrumentation around the prompt loop.
- Output queue: commands enqueue Markdown/text/table descriptors via helpers (`app.md`, `app.table`, ...); the runtime renders them with Rich on the next cycle.

## Quick Start
```python
from tui.app import App, Arg, Opt
from tui import completers

app = App("tasks", title="📋 Tasks", append_only=True, interactive_prompts=True)
app.state.setdefault("items", [])
app.state.setdefault("color", "indigo")

@app.on_start
def bootstrap(app_instance: App):
    app_instance.markdown("Commands: /add, /list, /color")
    if not app_instance.state["items"]:
        app_instance.info("No items yet. Use /add.")
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
    if any(it["name"] == name for it in items):
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

What happens
- `App` builds the prompt loop, loads history, and prints the banner once.
- Each command mutates `app.state` and queues Markdown/text/table output for the next render.
- History-backed arguments show recently used values in completions.

## App
- Constructor: `App(id: str, title: str | None = None, append_only: bool = True, interactive_prompts: bool = False)`
  - `id`: namespacing for disk-backed history (`~/.<id>/history.json`) and prompt history.
  - `title`: optional banner printed once in append-only mode.
  - `append_only`: if False, the console is cleared before each render.
  - `interactive_prompts`: enable follow-up prompts for arguments marked with `prompt=True` when input is missing.
- Properties
  - `state: dict`: shared mutable state.
  - `registry: CommandRegistry`: name → (handler, help, args).
  - `history: HistoryStore`: recency store for argument values.
  - `interaction: TUIInteraction`: prompt helper used when interactive prompts are enabled.
  - `prompt_history_path`: file used by prompt_toolkit to persist typed commands.
- Registration helpers
  - `command(name, args)` decorator registers a handler and its argument spec.
  - `on_start(fn)` runs once before the first prompt; ideal for printing initial UI.
  - `before_prompt(fn)` runs before each prompt (after draining queued output).
  - `after_prompt(fn)` runs after each prompt with `(app, text, handled)`.
- Output helpers
  - `info/ok/warn/err(text)` wrap consistent styling for inline messages.
  - `markdown(text)` / `md(text)` enqueue a Markdown panel.
  - `write(text)` / `text(text)` enqueue a plain text line.
  - `table(title, rows, columns=None)` enqueue a Rich table.
  - `enqueue_ui(descriptor)` accepts raw descriptors for advanced cases.
- Loop control
  - `run()` starts the prompt loop.
  - `_render()` drains the queue and renders immediately; useful in tests.

## Arguments
- `Arg(name, type=str, completer=None, default=None, history=False, prompt=False, repeat=False)`
  - Required positional argument unless `default` is not `None`, which makes it optional with a fallback.
  - `type`: one of `str`, `int`, `float`, `pathlib.Path`, or `tui.app.Path` (auto path completion).
  - `completer`: callable returning suggestions; defaults to history for `history=True` or paths for `Path` types.
  - `history`: record successful values to the history store and enable history completions.
  - `prompt`: when `interactive_prompts=True`, missing values trigger `interaction.ask_text`.
  - `repeat`: accept multiple values; the handler receives a `list`.
- `Opt` inherits from `Arg`
  - Optional flag available as `--name value` or `--name=value`.
  - Shares all fields with `Arg`; defaults are applied when omitted.
- `Path`
  - Marker type that maps to `pathlib.Path` conversion with path auto-completion.
- Repeatable arguments
  - When `repeat=True`, repeated flags or extra positional values append to a list.
  - Optional repeatables default to `[]`; required repeatables must receive at least one value (or via prompt).

## Parsing rules
- Required positionals are consumed in declaration order.
- Optional arguments accept both flag form (`--name value` or `--name=value`) and positional fallback after requireds.
- Unknown flags emit `Error: Unknown option: --flag`.
- Type conversion uses the declared `type`; invalid values emit `Error: Invalid value for ...`.
- Missing requireds emit `Error: Missing: name`.
- When `interactive_prompts=True`, arguments marked with `prompt=True` are asked for using `interaction.ask_text`.

## History store
- Stored at `~/.<app_id>/history.json`.
- `history.add(command, arg, value)` records recency timestamps.
- `history.get(command, arg, limit=8)` returns most recent values for completions.

## Completions
- Completers are callables: `(context: dict) -> list[str]`.
- Context keys provided by `SlashCompleter`:
  - `prefix`: current token fragment being completed (empty when starting a new token).
  - `command`: command name (e.g., `/add`).
  - `arg_name`: active argument.
  - `tokens`: raw tokens typed so far.
  - `state`: live `app.state`.
  - `history`: the `HistoryStore` instance.
  - `arg_values`: parsed values gathered so far (useful for dependent completions).
- Built-in helpers in `tui.completers`:
  - `choices(*items)` – filter a fixed list by prefix.
  - `numbers(start, stop, step)` – numeric ranges as strings.
  - `paths(extensions=None)` – filesystem paths with optional extension filter.
  - `history(limit=10)` – recent values from the history store.
  - `dependent(parent_arg, fetch)` – pass the parent argument value to `fetch(parent_value, ctx)`.
- Custom completion example
  ```python
  def project_names(ctx):
      prefix = ctx["prefix"]
      projects = sorted(ctx["state"].get("projects", []))
      return [name for name in projects if name.startswith(prefix)]

  @app.command("/assign", args=[Arg("project", completer=project_names)])
  def assign(project: str):
      app.ok(f"Assigned {project}")
  ```

## Output & rendering
- Commands enqueue output; the runtime drains `state["__print_queue__"]` at the start of each cycle.
- Descriptors are converted to Rich elements via `tui.ui.descriptors_to_elements`.
- Helpers map to descriptors:
  - `markdown/md` → `Markdown` panel.
  - `write/text` → plain text line.
  - `table` → `TableEl` (with inferred columns when not provided).
- Advanced use: import `tui.ui` (`Header`, `Subheader`, `Markdown`, `Text`, `TableEl`, `render_elements`) to render custom elements or build your own queue descriptors.

## Interaction (optional prompts)
- Enable by constructing the app with `interactive_prompts=True`.
- Arguments with `prompt=True` trigger `interaction.ask_text` when not supplied.
- Repeatable prompts accept comma-separated values; optional prompts can be left blank to keep defaults.
- Cancellation (`Ctrl+C`/`Ctrl+D`) returns `None` and aborts the command with `app.err("Canceled")`.

## Lifecycle hooks
- `@app.on_start`: runs once before the first prompt. Useful for seeding UI or warm-up tasks.
- `@app.before_prompt`: runs before each prompt after rendering queued output.
- `@app.after_prompt`: runs after each prompt with `(app, text, handled)`.
- Errors raised inside hooks are caught and surfaced via `app.err("<hook> error: ...")` so the loop keeps running.

## Runtime loop
1. `run()` lazily creates a `PromptSession` with slash completions and history.
2. `on_start` hooks fire once; append-only mode prints a hint (`Type '/' ...`).
3. For each iteration:
   - `before_prompt` hooks run.
   - `_render()` drains and renders queued UI.
   - The prompt collects input with completions.
   - Input is normalized:
     - blank → continue
     - `q|quit|exit` → exit
     - leading `/` → dispatch via `commands.dispatch`
     - other text → `app.err("Type '/' to run a command")`
   - `after_prompt` hooks run with the raw input and whether it was handled as a command.

## Patterns & best practices
- Initialize state once with `setdefault` and mutate in place for lists (`items[:] = ...`).
- Keep command handlers small; perform heavy work in helper functions or services.
- Use `history=True` for frequently reused arguments.
- Pair `repeat=True` with `prompt=True` to support comma-separated prompts for multi-select fields.
- Print structured feedback with `app.ok/info/warn/err` followed by tables or markdown panels for richer context.

## Extending
- Add new completer helpers in `tui/completers.py` or inject your own callables when registering commands.
- Extend output by adding new descriptor kinds and teaching `descriptors_to_elements` how to render them.
- Wrap `App.run` if you need a different interaction model (e.g., GUI) while keeping the same command surface.

## Troubleshooting
- `Unknown option` → check flag spelling; optional args must be declared in `args`.
- `Missing: name` → ensure required arguments were supplied or enable interactive prompts with `prompt=True`.
- `Invalid value` → confirm the input matches the declared `type`.
- No completions → verify the completer returns a list and that dependent completers look up existing `arg_values`.

## Reference: types & helpers
- `App`, `Arg`, `Opt`, `Path` from `tui.app`.
- `CommandRegistry`, `SlashCompleter`, `dispatch` from `tui.commands`.
- `HistoryStore` from `tui.history`.
- Completer helpers: `choices`, `numbers`, `paths`, `history`, `dependent` in `tui.completers`.
- UI helpers: `Header`, `Subheader`, `Markdown`, `Text`, `TableEl`, `render_elements`, `descriptors_to_elements` in `tui.ui`.
