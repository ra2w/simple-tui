import os
from typing import List

from tui.app import App, Arg
from tui.commands import SlashCompleter


def test_history_record_and_completion(tmp_path, monkeypatch):
    os.environ["HOME"] = str(tmp_path)
    app = App("hist_test", append_only=True)

    @app.command("/task", args=[Arg("name", str, history=True)])
    def task(name: str):
        pass

    # Run once to record history
    entry = app.registry.resolve("/task")
    assert entry is not None
    entry.handler(["Foo"])  # history=True should record

    # History returns Foo
    hist = app.history.get("/task", "name", limit=8)
    assert "Foo" in hist

    # Completer suggests from history for the first arg
    comp = SlashCompleter(app.registry, history_store=app.history, state_provider=lambda: app.state)
    items = list(comp.get_completions(type("Doc", (), {"text_before_cursor": "/task "})(), None))
    texts = [c.text for c in items]
    assert "Foo" in texts


def test_unknown_flag_and_missing_value_errors(tmp_path, monkeypatch):
    app = App("err_test", append_only=True)

    @app.command("/task", args=[Arg("name", str)])
    def task(name: str):
        pass

    entry = app.registry.resolve("/task")
    assert entry is not None

    errors: List[str] = []
    monkeypatch.setattr(app, "err", lambda t: errors.append(t))

    entry.handler(["Foo", "--hours"])  # missing value for an unknown flag
    assert any("Unknown option: --hours" in e or "requires a value" in e for e in errors)
