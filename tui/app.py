from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union
import inspect
import pathlib
import asyncio
import sys

from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from . import completers
from .history import HistoryStore
from .commands import CommandRegistry, SlashCompleter, dispatch, CommandSpec
from .ptkstyle import style as ptk_style
from .ui import render_elements, Markdown, descriptors_to_elements
from .theme import GRAY
from .interaction import TUIInteraction, HeadlessInteraction
from .transcript import TranscriptRecorder


# Simple path type marker
class Path:
    pass


@dataclass
class Arg:
    name: str
    type: type = str
    completer: Callable[[Dict[str, Any]], List[str]] | None = None
    default: Any = None
    history: bool = False
    prompt: bool = False
    repeat: bool = False

    def get_completer(self) -> Callable[[Dict[str, Any]], List[str]] | None:
        """Get the completer function for this argument."""
        if self.completer:
            return self.completer
        # Auto-completers for common types
        if self.type == pathlib.Path or self.type == Path:
            return completers.paths()
        if self.history:
            return completers.history()
        return None


@dataclass
class Opt(Arg):
    """Optional argument - inherits from Arg with a default value."""
    pass




def _converter_for(tp: type) -> Callable[[str], Any]:
    if tp is int:
        return int
    if tp is float:
        return float
    if tp in (pathlib.Path, Path):
        return pathlib.Path
    return str


class App:
    def __init__(self, id: str, title: Optional[str] = None, append_only: bool = True, 
                 interactive_prompts: bool = False, headless: bool = False,
                 transcript_path: Optional[pathlib.Path] = None,
                 transcript_format: str = "markdown"):
        # Ensure event loop exists
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        self.id = id
        self.state: Dict[str, Any] = {}
        # Streaming mode only (append-only terminal output)
        self.append_only: bool = append_only
        self.title = title
        self.console = Console()
        self.registry = CommandRegistry()
        self.history = HistoryStore(id)
        # Create path for prompt history
        self.prompt_history_path = pathlib.Path.home() / f".{id}" / "prompt_history.txt"
        self.prompt_history_path.parent.mkdir(parents=True, exist_ok=True)
        self._session: PromptSession | None = None
        self.interaction = TUIInteraction()
        self.interactive_prompts = interactive_prompts
        self._start_hooks: List[Callable[["App"], None]] = []
        self._before_prompt_hooks: List[Callable[["App"], None]] = []
        self._after_prompt_hooks: List[Callable[["App", str, bool], None]] = []
        
        # Headless mode configuration
        self.headless = headless
        self.transcript: Optional[TranscriptRecorder] = None
        if headless and transcript_path:
            self.transcript = TranscriptRecorder(transcript_path, transcript_format)
        
        # Disable interactive prompts in headless mode by default
        if headless and interactive_prompts:
            self.interactive_prompts = False

        if self.title and self.append_only and not self.headless:
            # One-time header in streaming mode
            render_elements(self.console, Markdown(f"{self.title}"))

    # Output helpers
    def _message(
        self,
        markup: str,
        *,
        transcript_type: Optional[str] = None,
        transcript_text: Optional[str] = None,
    ):
        self.enqueue_ui({"k": "text", "t": markup})
        if transcript_type and self.transcript:
            self.transcript.record_output(
                transcript_type,
                transcript_text if transcript_text is not None else markup,
            )

    def info(self, t: str):
        self._message(
            f"[{GRAY}]{t}[/{GRAY}]",
            transcript_type="info",
            transcript_text=t,
        )

    def ok(self, t: str):
        self._message(
            f"[green]✓ {t}[/green]",
            transcript_type="ok",
            transcript_text=t,
        )

    def warn(self, t: str):
        self._message(
            f"[yellow]⚠ {t}[/yellow]",
            transcript_type="warn",
            transcript_text=t,
        )

    def err(self, t: str):
        self._message(
            f"[red]Error: {t}[/red]",
            transcript_type="err",
            transcript_text=t,
        )
    # Ephemeral UI queue helpers
    def _queue(self):
        return self.state.setdefault("__print_queue__", [])

    def enqueue_ui(self, desc: Dict[str, Any]):
        self._queue().append(desc)
        self._record_transcript_descriptor(desc)

    def _record_transcript_descriptor(self, desc: Dict[str, Any]):
        if not self.transcript:
            return

        kind = desc.get("k")
        if kind == "md":
            self.transcript.record_ui_element(
                "markdown",
                {"content": desc.get("t", "")},
            )
        elif kind == "text":
            self.transcript.record_ui_element(
                "text",
                {"content": desc.get("t", "")},
            )
        elif kind == "table":
            self.transcript.record_ui_element(
                "table",
                {
                    "title": desc.get("title", ""),
                    "rows": desc.get("rows", []),
                    "columns": desc.get("cols", []),
                },
            )
    def markdown(self, text: str):
        self.enqueue_ui({"k": "md", "t": text})

    def md(self, text: str):
        self.markdown(text)

    def write(self, text: str):
        self.enqueue_ui({"k": "text", "t": text})

    def text(self, text: str):
        self.write(text)

    def table(self, title: str, rows: List[Dict[str, Any]], columns: List[str] | None = None):
        self.enqueue_ui({"k": "table", "title": title, "rows": rows or [], "cols": columns})

    def on_start(self, fn: Callable[["App"], None]):
        self._start_hooks.append(fn)
        return fn

    def before_prompt(self, fn: Callable[["App"], None]):
        self._before_prompt_hooks.append(fn)
        return fn

    def after_prompt(self, fn: Callable[["App", str, bool], None]):
        self._after_prompt_hooks.append(fn)
        return fn

    def _fire_hooks(self, hooks: List[Callable[..., None]], *args: Any, label: str):
        for hook in hooks:
            try:
                hook(*args)
            except Exception as exc:
                self.err(f"{label} error: {exc}")

    def _run_start_hooks(self):
        self._fire_hooks(self._start_hooks, self, label="on_start")

    def _run_before_prompt_hooks(self):
        self._fire_hooks(self._before_prompt_hooks, self, label="before_prompt")

    def _run_after_prompt_hooks(self, text: str, handled: bool):
        self._fire_hooks(self._after_prompt_hooks, self, text, handled, label="after_prompt")

    # Decorators
    def command(self, name: str, args: List[Arg | Opt]):
        def deco(fn: Callable):
            cmd_name = name
            spec = CommandSpec.from_args(cmd_name, args, _converter_for, optional_types=(Opt,))

            def handler(argv: List[str]):
                prompt_fn = None
                if self.interactive_prompts:
                    def prompt(plan, default_text):
                        return self.interaction.ask_text(f"Enter {plan.name}", default=default_text)
                    prompt_fn = prompt

                values = spec.parse(
                    argv,
                    on_error=self.err,
                    prompt_fn=prompt_fn,
                    interactive=self.interactive_prompts,
                )
                if values is None:
                    return

                for arg_name, recorded_value in spec.history_entries(values):
                    self.history.add(cmd_name, arg_name, str(recorded_value))

                try:
                    fn(**{p.name: values.get(p.name) for p in inspect.signature(fn).parameters.values()})
                except TypeError:
                    fn(**values)

            help_text = (inspect.getdoc(fn) or "").strip()
            self.registry.register(cmd_name, handler, help_text, spec)
            return fn

        return deco

    def _handle_command_text(
        self,
        text: str,
        *,
        fail_on_error: bool,
        from_script: bool,
        catch_exceptions: bool,
    ) -> bool:
        handled = text.startswith("/")

        def finish():
            self._run_after_prompt_hooks(text, handled)
            self._render()

        if handled:
            try:
                dispatch(self.registry, text, on_error=self.err)
            except Exception as exc:
                if catch_exceptions:
                    self.err(f"Command failed: {str(exc)}")
                    if fail_on_error:
                        return False
                    finish()
                    return True
                raise
        else:
            message = "Commands must start with '/'" if from_script else "Type '/' to run a command"
            self.err(message)
            if fail_on_error:
                return False
            finish()
            return True

        finish()
        return True

    def _render(self):
        # Streaming mode: never clears; just prints new content
        if not self.append_only:
            self.console.clear()
            if self.title:
                render_elements(self.console, Markdown(f"{self.title}"))
            self.console.print("Type '/' for commands, or 'q' to quit.")

        # Drain ephemeral UI queue first
        q = list(self.state.get("__print_queue__", []))
        if q:
            self.state["__print_queue__"] = []
            queued_elements = descriptors_to_elements(q)
            render_elements(self.console, queued_elements)

    def run_script(self, commands: Union[List[str], str, pathlib.Path], 
                   prompt_responses: Optional[Dict[str, Any]] = None,
                   fail_on_error: bool = True):
        """Run a script of commands in headless mode.
        
        Args:
            commands: List of commands, script file path, or multiline string
            prompt_responses: Dict mapping prompt names to responses
            fail_on_error: Whether to stop on first error
        """
        original_interaction = self.interaction
        original_interactive = self.interactive_prompts

        try:
            if self.interactive_prompts or prompt_responses:
                self.interaction = HeadlessInteraction(prompt_responses or {}, self.transcript)
                self.interactive_prompts = True

            if isinstance(commands, pathlib.Path):
                with open(commands, 'r') as f:
                    command_list = [
                        line.strip()
                        for line in f
                        if line.strip() and not line.strip().startswith('#')
                    ]
            elif isinstance(commands, str):
                command_list = [
                    line.strip()
                    for line in commands.splitlines()
                    if line.strip() and not line.strip().startswith('#')
                ]
            else:
                command_list = list(commands)

            self._headless_prompt_responses = prompt_responses or {}

            self._run_start_hooks()

            for cmd in command_list:
                self._run_before_prompt_hooks()
                self._render()

                if cmd.lower() in {"q", "quit", "exit"}:
                    self._run_after_prompt_hooks(cmd, False)
                    self._render()
                    break

                if self.transcript:
                    self.transcript.record_command(cmd)

                should_continue = self._handle_command_text(
                    cmd,
                    fail_on_error=fail_on_error,
                    from_script=True,
                    catch_exceptions=True,
                )
                if not should_continue:
                    break
        finally:
            if self.transcript:
                self.transcript.finalize()
            self.interaction = original_interaction
            self.interactive_prompts = original_interactive
    
    def run(self):
        if self._session is None:
            self._session = PromptSession(
                style=ptk_style,
                history=FileHistory(str(self.prompt_history_path))
            )
        completer = SlashCompleter(
            self.registry,
            history_store=self.history,
            state_provider=lambda: self.state,
        )
        self._run_start_hooks()
        if self.append_only:
            # Initial hint only in streaming mode
            self.console.print("\nType '/' for commands, or 'q' to quit.")
        while True:
            self._run_before_prompt_hooks()
            self._render()
            try:
                s = self._session.prompt(HTML('<prompt>#</prompt> '), completer=completer).strip()
            except (KeyboardInterrupt, EOFError):
                self.info("Goodbye! 👋")
                self._run_after_prompt_hooks("", False)
                self._render()
                break

            if s.lower() in {"q", "quit", "exit"}:
                self._run_after_prompt_hooks(s, False)
                self._render()
                break
            if not s:
                self._run_after_prompt_hooks(s, False)
                self._render()
                continue
            self._handle_command_text(
                s,
                fail_on_error=False,
                from_script=False,
                catch_exceptions=False,
            )
