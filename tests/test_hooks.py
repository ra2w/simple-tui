import itertools

import tui.app as appmod
from tui.app import App


def test_hooks_run_in_order(monkeypatch, tmp_path, capsys):
    app = App("hook_test", append_only=True)

    events = []

    @app.on_start
    def start(app_instance: App):
        events.append("start")
        app_instance.write("start")

    @app.before_prompt
    def before(app_instance: App):
        events.append("before")

    @app.after_prompt
    def after(app_instance: App, text: str, handled: bool):
        events.append(f"after:{text}:{handled}")

    @app.command("/noop", args=[])
    def noop():
        events.append("cmd")

    class DummySession:
        def __init__(self):
            self._inputs = iter(["/noop", "q"])

        def prompt(self, *args, **kwargs):
            return next(self._inputs)

    monkeypatch.setattr(appmod, "PromptSession", lambda *a, **k: DummySession())

    app.run()

    # Drain any buffered output (not needed for assertions, but keeps capsys clean)
    capsys.readouterr()

    assert events == [
        "start",
        "before",
        "cmd",
        "after:/noop:True",
        "before",
        "after:q:False",
    ]
