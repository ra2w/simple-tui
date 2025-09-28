from tui.app import App


def test_render_outputs_written_content(tmp_path, capsys):
    app = App("render_test", append_only=True)

    app.write("Hello")
    app.markdown("**World**")
    app.table("Items", [{"ID": 1, "Name": "X"}])

    app._render()
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "World" in out
    assert "Items" in out
    assert not app.state.get("__print_queue__")


def test_non_append_only_clears_and_shows_hint(tmp_path, capsys, monkeypatch):
    app = App("non_append", append_only=False)

    clears = []

    def fake_clear(*args, **kwargs):
        clears.append(True)

    monkeypatch.setattr(app.console, "clear", fake_clear)

    app.write("Hello")

    app._render()
    out = capsys.readouterr().out
    assert clears, "console.clear should be invoked in non append-only mode"
    assert "Type '/' for commands" in out
    assert "Hello" in out
    assert not app.state.get("__print_queue__")
