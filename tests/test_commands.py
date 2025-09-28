import os
from typing import Any, Dict, List, Optional

import tui.app as appmod
from tui.app import App, Arg, Opt
from tui.commands import dispatch


def make_app(tmp_path) -> App:
    os.environ["HOME"] = str(tmp_path)
    return App("test_app", append_only=True)


def test_command_with_history_flag(tmp_path):
    app = make_app(tmp_path)

    @app.command("/task", args=[Arg("name", str, history=True)])
    def task(name: str):
        pass

    entry = app.registry.resolve("/task")
    assert entry is not None
    args = entry.spec.args
    assert args[0].name == "name"
    assert args[0].history is True
    # History completer should be auto-assigned
    assert args[0].get_completer() is not None


def test_parse_required_and_optional_flags_with_equals_and_space(tmp_path):
    app = make_app(tmp_path)

    calls: List[Dict[str, Any]] = []

    @app.command("/task", args=[Arg("name", str), Opt("hours", int, default=1)])
    def task(name: str, hours: int = 1):
        calls.append({"name": name, "hours": hours})

    entry = app.registry.resolve("/task")
    assert entry is not None
    handler = entry.handler

    handler(["Write", "--hours", "3"])  # space form
    handler(["Code", "--hours=5"])      # equals form
    handler(["Doc"])                      # default

    assert calls == [
        {"name": "Write", "hours": 3},
        {"name": "Code", "hours": 5},
        {"name": "Doc", "hours": 1},
    ]


def test_missing_required_reports_error(tmp_path, monkeypatch):
    app = make_app(tmp_path)

    @app.command("/task", args=[Arg("name", str)])
    def task(name: str):
        pass

    errors = []
    monkeypatch.setattr(app, "err", lambda t: errors.append(t))

    entry = app.registry.resolve("/task")
    assert entry is not None
    handler = entry.handler
    handler([])
    assert any("Missing: name" in e for e in errors)


def test_interactive_prompts_fill_missing(tmp_path, monkeypatch):
    app = App("prompt_app", append_only=True, interactive_prompts=True)

    responses = iter(["Foo", ""])

    def fake_ask(prompt: str, default: Optional[str] = None):
        return next(responses)

    monkeypatch.setattr(app.interaction, "ask_text", fake_ask)

    calls: List[Dict[str, Any]] = []

    @app.command("/task", args=[Arg("name", str, prompt=True), Opt("limit", int, default=10, prompt=True)])
    def task(name: str, limit: int = 10):
        calls.append({"name": name, "limit": limit})

    entry = app.registry.resolve("/task")
    assert entry is not None
    handler = entry.handler
    handler([])

    assert calls == [{"name": "Foo", "limit": 10}]


def test_dispatch_handles_quoted_arguments(tmp_path):
    app = make_app(tmp_path)

    calls: List[str] = []

    @app.command("/say", args=[Arg("message", str)])
    def say(message: str):
        calls.append(message)

    dispatch(app.registry, '/say "hello world"')

    assert calls == ["hello world"]
