# TUI Architecture (v3)

This document explains the design, flow, and key extension points of the `tui` v3 runtime. The goal is a compact, explicit core with great developer ergonomics.

## Overview
- Command-first: slash commands mutate shared state and enqueue output for the next render.
- Small, typed surface: `App`, `Arg`/`Opt`, and a handful of completer helpers drive both parsing and the palette experience.
- Streaming model: the runtime drains a queue of UI descriptors each loop; there is no diffing or virtual view tree.
- Explicit lifecycle: hooks (`on_start`, `before_prompt`, `after_prompt`) wrap the prompt loop for instrumentation or boot-time UI.

## Runtime flow
1. **Initialize**
   - `app = App(id, title=None, append_only=True, interactive_prompts=False)` sets up the command registry, console, history store, prompt session configuration, and mutable state dict.
   - History is loaded from `~/.<id>/history.json`; prompt history is stored at `~/.<id>/prompt_history.txt`.
2. **Register commands**
   - `@app.command("/name", args=[...])` captures handler functions plus their argument specs.
   - Each `Arg`/`Opt` describes type conversion, defaults, completions, prompt behavior, and repeatability.
   - Specs are reused by both the parser (for validation) and the slash completer (for suggestions).
3. **Attach hooks (optional)**
   - `@app.on_start` runs once before the first prompt—ideal for seeding the UI via `app.md`, `app.table`, etc.
   - `@app.before_prompt` executes before each prompt after rendering queued output.
   - `@app.after_prompt` runs after each prompt with `(app, text, handled)` for logging or metrics.
4. **Run loop** (`app.run()`)
   - Lazily creates a prompt_toolkit `PromptSession` with `SlashCompleter`.
   - Fires `on_start` hooks, prints a hint in append-only mode (`Type '/' for commands, or 'q' to quit.`).
   - Repeats:
     1. Execute `before_prompt` hooks.
     2. Drain and render the queued descriptors (`state["__print_queue__"]`) via `tui.ui.descriptors_to_elements` → Rich console output.
     3. Prompt the user. Slash commands are parsed; other text yields an error.
     4. Dispatch `/cmd ...` via `tui.commands.dispatch`, which:
        - Splits argv with `shlex`.
        - Parses positionals/optionals according to the stored spec.
        - Converts types, records history, and invokes the handler with kwargs.
     5. Run `after_prompt` hooks.
   - Exit paths: `q|quit|exit` or EOF/KeyboardInterrupt (the latter prints `Goodbye! 👋`).

## Parsing & completion pipeline
- Argument specs differentiate required vs optional based on defaults or use of `Opt`.
- Optional parameters accept both `--flag value` and positional fallback once requireds are satisfied.
- Repeatable args (`repeat=True`) collect values into lists.
- When `interactive_prompts=True`, arguments flagged with `prompt=True` trigger `TUIInteraction.ask_text` to resolve missing input.
- `SlashCompleter` keeps the registry in sync with the parser:
  - Parses typed tokens to determine the active argument.
  - Builds a context dict (`prefix`, `command`, `arg_name`, `tokens`, `state`, `history`, `arg_values`).
  - Invokes the active argument's completer (custom or auto-generated).

## Output stream
- Commands and hooks enqueue descriptors through helpers:
  - `app.ok/info/warn/err` enqueue styled text.
  - `app.md`/`app.markdown` enqueue Markdown panels.
  - `app.text`/`app.write` enqueue plain lines.
  - `app.table` enqueues structured table descriptors (columns optional).
- Descriptors live under `state["__print_queue__"]` until `_render()` drains and prints them with Rich.
- Tests call `_render()` directly to verify the queue drains and renders as expected.

## Modules & responsibilities
- `tui/app.py`
  - `App`, `Arg`, `Opt`, `Path`, lifecycle hooks, parser, print queue helpers, run loop, interactive prompt integration.
- `tui/commands.py`
  - `CommandRegistry`, `SlashCompleter`, `dispatch`; keeps parsing and completion in lock-step.
- `tui/completers.py`
  - Built-in completer factories: choices, numbers, paths, history, dependent.
- `tui/history.py`
  - Disk-backed recency store keyed by command/argument.
- `tui/ui.py`
  - Rich element dataclasses (`Header`, `Markdown`, `TableEl`, etc.), `render_elements`, `descriptors_to_elements`.
- `tui/interaction.py`
  - `TUIInteraction` providing text prompts when interactive prompting is enabled.
- `tui/messages.py`
  - Standalone styled log helpers used by fallback error reporting.

## Extension points
- **Commands**: add new slash handlers with typed arguments and custom completers.
- **Completions**: supply any callable `(context) -> list[str]`; dependent completions can inspect `context["arg_values"]`.
- **Output**: add descriptor kinds and teach `descriptors_to_elements` how to render them, or call Rich directly if needed.
- **Hooks**: instrument the loop via `on_start`, `before_prompt`, and `after_prompt` without patching the core.
- **Interaction**: swap `App.interaction` for a different implementation (e.g., form-based prompts) while retaining command specs.

## Data contracts
- Command registry entry: `name -> (handler: Callable[[list[str]], None], help_text: str, args: list[Arg|Opt])`.
- Completer context: `{ "prefix": str, "command": str, "arg_name": str, "tokens": list[str], "state": dict, "history": HistoryStore, "arg_values": dict }`.
- Print queue descriptor examples:
  - `{ "k": "md", "t": "**Hello**" }`
  - `{ "k": "text", "t": "Done" }`
  - `{ "k": "table", "title": "Items", "rows": [...], "cols": ["ID", "Name"] }`

## Non-goals
- No hidden state reconciliation or reactive view layer.
- No implicit global registries; everything hangs off the `App` instance.
- No background threading—command handlers run synchronously on the event loop.

## Summary
`tui` v3 keeps the runtime tiny: commands declare their CLI contracts, completions stay in sync automatically, and output is a simple stream of Rich-friendly descriptors. Hooks and the print queue provide enough structure for real applications without introducing heavy abstractions.
