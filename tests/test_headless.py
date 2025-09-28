import pytest
from pathlib import Path
import json
import tempfile
from tui.app import App, Arg, Opt
from tui.transcript import TranscriptRecorder


def test_headless_basic_transcript(tmp_path):
    """Test basic headless mode with transcript recording."""
    transcript_path = tmp_path / "transcript.md"
    
    app = App(
        "test_headless",
        headless=True,
        transcript_path=transcript_path
    )
    
    # Add a simple command
    @app.command("/echo", args=[Arg("message", str)])
    def echo(message: str):
        app.ok(f"Echo: {message}")
    
    # Run script
    commands = ["/echo hello", "/echo world"]
    app.run_script(commands)
    
    # Check transcript was created
    assert transcript_path.exists()
    content = transcript_path.read_text()
    assert "# TUI Session Transcript" in content
    assert "/echo hello" in content
    assert "✓ Echo: hello" in content
    assert "/echo world" in content
    assert "✓ Echo: world" in content


def test_headless_with_prompts(tmp_path):
    """Test headless mode with interactive prompts."""
    transcript_path = tmp_path / "transcript.md"
    
    app = App(
        "test_prompts",
        headless=True,
        transcript_path=transcript_path,
        interactive_prompts=True
    )
    
    collected = []
    
    @app.command("/greet", args=[Arg("name", str, prompt=True)])
    def greet(name: str):
        collected.append(name)
        app.ok(f"Hello, {name}!")
    
    # Run with prompt responses
    app.run_script(["/greet"], prompt_responses={"name": "Alice"})
    
    assert collected == ["Alice"]
    content = transcript_path.read_text()
    assert "Enter name: Alice" in content
    assert "✓ Hello, Alice!" in content


def test_headless_json_format(tmp_path):
    """Test JSON transcript format."""
    transcript_path = tmp_path / "transcript.json"
    
    app = App(
        "test_json",
        headless=True,
        transcript_path=transcript_path,
        transcript_format="json"
    )
    
    @app.command("/test", args=[])
    def test():
        app.info("Testing")
        app.ok("Success")
    
    app.run_script(["/test"])
    
    # Load and verify JSON
    with open(transcript_path) as f:
        data = json.load(f)
    
    assert "session" in data
    assert "entries" in data
    assert len(data["entries"]) == 1
    assert data["entries"][0]["command"] == "/test"
    assert len(data["entries"][0]["outputs"]) == 2


def test_headless_ui_elements(tmp_path):
    """Test recording of UI elements in transcript."""
    transcript_path = tmp_path / "transcript.md"
    
    app = App(
        "test_ui",
        headless=True,
        transcript_path=transcript_path
    )
    
    @app.command("/show", args=[])
    def show():
        app.markdown("# Hello Markdown")
        app.table("Test Table", [
            {"id": 1, "name": "foo"},
            {"id": 2, "name": "bar"}
        ], columns=["id", "name"])
        app.text("Plain text output")
    
    app.run_script(["/show"])
    
    content = transcript_path.read_text()
    assert "# Hello Markdown" in content
    assert "### Test Table" in content
    assert "| id | name |" in content
    assert "| 1 | foo |" in content
    assert "| 2 | bar |" in content
    assert "Plain text output" in content


def test_headless_error_handling(tmp_path):
    """Test error handling in headless mode."""
    transcript_path = tmp_path / "transcript.md"
    
    app = App(
        "test_errors",
        headless=True,
        transcript_path=transcript_path
    )
    
    @app.command("/fail", args=[])
    def fail():
        app.err("Something went wrong!")
    
    # Test fail-fast mode
    app.run_script(["/fail", "/fail"], fail_on_error=True)
    
    content = transcript_path.read_text()
    # Should only have one command due to fail-fast
    assert content.count("/fail") == 1
    assert "❌ Error: Something went wrong!" in content


def test_script_from_file(tmp_path):
    """Test running script from file."""
    script_path = tmp_path / "script.txt"
    script_path.write_text("""
# This is a comment
/echo first
/echo second

# Another comment
/echo third
""")
    
    transcript_path = tmp_path / "transcript.md"
    
    app = App(
        "test_file",
        headless=True,
        transcript_path=transcript_path
    )
    
    @app.command("/echo", args=[Arg("msg", str)])
    def echo(msg: str):
        app.ok(msg)
    
    app.run_script(script_path)
    
    content = transcript_path.read_text()
    assert "✓ first" in content
    assert "✓ second" in content
    assert "✓ third" in content
    # Comments should not be executed
    assert "# This is a comment" not in content