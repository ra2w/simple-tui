#!/usr/bin/env python3
"""Demonstration of headless mode functionality."""

import argparse
import pathlib
import json
from typing import Optional

from tui.app import App, Arg, Opt, Path


def create_demo_app(headless: bool = False, 
                   transcript_path: Optional[pathlib.Path] = None,
                   transcript_format: str = "markdown") -> App:
    """Create the demo application with headless support."""
    app = App(
        "headless_demo",
        title="🤖 Headless Mode Demo",
        append_only=True,
        interactive_prompts=True,
        headless=headless,
        transcript_path=transcript_path,
        transcript_format=transcript_format
    )
    
    # Initialize state
    app.state.setdefault("items", [])
    
    @app.command("/add", args=[
        Arg("name", str, history=True, prompt=True),
        Opt("description", str, default="No description")
    ])
    def add_item(name: str, description: str = "No description"):
        """Add a new item to the list"""
        items = app.state["items"]
        if any(item["name"] == name for item in items):
            app.err(f"Item '{name}' already exists!")
            return
        
        new_item = {
            "id": len(items) + 1,
            "name": name,
            "description": description
        }
        items.append(new_item)
        app.ok(f"Added item '{name}'")
    
    @app.command("/list", args=[])
    def list_items():
        """List all items"""
        items = app.state["items"]
        if not items:
            app.info("No items yet")
            return
        
        app.table(
            "Items",
            items,
            columns=["id", "name", "description"]
        )
    
    @app.command("/update", args=[
        Arg("name", str, prompt=True),
        Arg("description", str, prompt=True)
    ])
    def update_item(name: str, description: str):
        """Update an item's description"""
        items = app.state["items"]
        for item in items:
            if item["name"] == name:
                old_desc = item["description"]
                item["description"] = description
                app.ok(f"Updated '{name}' description from '{old_desc}' to '{description}'")
                return
        app.err(f"Item '{name}' not found!")
    
    @app.command("/delete", args=[Arg("name", str, prompt=True)])
    def delete_item(name: str):
        """Delete an item"""
        items = app.state["items"]
        original_count = len(items)
        app.state["items"] = [item for item in items if item["name"] != name]
        
        if len(app.state["items"]) < original_count:
            app.ok(f"Deleted item '{name}'")
        else:
            app.err(f"Item '{name}' not found!")
    
    @app.command("/stats", args=[])
    def show_stats():
        """Show statistics"""
        items = app.state["items"]
        app.markdown(f"### Statistics")
        app.write(f"Total items: {len(items)}")
        if items:
            avg_desc_length = sum(len(item["description"]) for item in items) / len(items)
            app.write(f"Average description length: {avg_desc_length:.1f} characters")
    
    return app


def main():
    parser = argparse.ArgumentParser(
        description="TUI application with headless mode support"
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode (default)"
    )
    mode_group.add_argument(
        "--script", "-s",
        type=pathlib.Path,
        help="Run commands from a script file"
    )
    mode_group.add_argument(
        "--commands", "-c",
        nargs="+",
        help="Execute specific commands"
    )
    
    # Headless options
    parser.add_argument(
        "--transcript", "-t",
        type=pathlib.Path,
        help="Path to save transcript (enables headless mode)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="Transcript output format (default: markdown)"
    )
    parser.add_argument(
        "--responses", "-r",
        type=pathlib.Path,
        help="JSON file with prompt responses for headless mode"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first error in headless mode"
    )
    
    args = parser.parse_args()
    
    # Determine if we're in headless mode
    headless = bool(args.script or args.commands or args.transcript)
    
    # Load prompt responses if provided
    prompt_responses = {}
    if args.responses:
        with open(args.responses) as f:
            prompt_responses = json.load(f)
    
    # Create the app
    app = create_demo_app(
        headless=headless,
        transcript_path=args.transcript,
        transcript_format=args.format
    )
    
    # Run based on mode
    if args.script:
        # Run from script file
        app.run_script(
            args.script,
            prompt_responses=prompt_responses,
            fail_on_error=args.fail_fast
        )
    elif args.commands:
        # Run specific commands
        app.run_script(
            args.commands,
            prompt_responses=prompt_responses,
            fail_on_error=args.fail_fast
        )
    else:
        # Interactive mode
        app.run()


if __name__ == "__main__":
    main()