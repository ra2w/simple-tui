from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO
import json
from rich.console import Console
from rich.table import Table
from io import StringIO


class TranscriptRecorder:
    """Records TUI session commands and outputs to create a dribble-like transcript."""
    
    def __init__(self, output_path: Optional[Path] = None, format: str = "markdown"):
        self.output_path = output_path
        self.format = format
        self.entries: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self._file_handle: Optional[TextIO] = None
        self._console_buffer = StringIO()
        self._buffered_console = Console(file=self._console_buffer, force_terminal=False)
        
        if self.output_path:
            self._file_handle = open(self.output_path, "w", encoding="utf-8")
            self._write_header()
    
    def _write_header(self):
        """Write transcript header based on format."""
        if self.format == "markdown":
            self._write(f"# TUI Session Transcript\n")
            self._write(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        elif self.format == "json":
            # JSON header written at the end
            pass
            
    def _write(self, content: str):
        """Write content to transcript file."""
        if self._file_handle:
            self._file_handle.write(content)
            self._file_handle.flush()
    
    def record_command(self, command: str):
        """Record a command being executed."""
        entry = {
            "type": "command",
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "outputs": []
        }
        self.entries.append(entry)
        
        if self.format == "markdown":
            self._write(f"## Command: {command}\n")
            self._write(f"> {command}\n")
    
    def record_output(self, output_type: str, content: str):
        """Record command output (info, ok, warn, err)."""
        if self.entries and self.entries[-1]["type"] == "command":
            self.entries[-1]["outputs"].append({
                "type": output_type,
                "content": content
            })
        
        if self.format == "markdown":
            # Format based on output type
            if output_type == "ok":
                self._write(f"✓ {content}\n")
            elif output_type == "err":
                self._write(f"❌ Error: {content}\n")
            elif output_type == "warn":
                self._write(f"⚠️  {content}\n")
            elif output_type == "info":
                self._write(f"ℹ️  {content}\n")
            else:
                self._write(f"{content}\n")
    
    def record_ui_element(self, element_type: str, element_data: Dict[str, Any]):
        """Record UI elements like tables, markdown, etc."""
        if self.entries and self.entries[-1]["type"] == "command":
            self.entries[-1]["outputs"].append({
                "type": f"ui_{element_type}",
                "data": element_data
            })
        
        if self.format == "markdown":
            if element_type == "table":
                self._write_table_markdown(element_data)
            elif element_type == "markdown":
                self._write(f"\n{element_data.get('content', '')}\n")
            elif element_type == "text":
                self._write(f"{element_data.get('content', '')}\n")
    
    def _write_table_markdown(self, table_data: Dict[str, Any]):
        """Convert table data to markdown format."""
        title = table_data.get("title", "")
        rows = table_data.get("rows", [])
        columns = table_data.get("columns", [])
        
        if title:
            self._write(f"\n### {title}\n")
        
        if not rows:
            self._write("*(empty table)*\n")
            return
            
        # Auto-detect columns if not provided
        if not columns and rows:
            columns = list(rows[0].keys())
        
        # Write header
        self._write("| " + " | ".join(columns) + " |\n")
        self._write("|" + "|".join(["-" * (len(col) + 2) for col in columns]) + "|\n")
        
        # Write rows
        for row in rows:
            values = [str(row.get(col, "")) for col in columns]
            self._write("| " + " | ".join(values) + " |\n")
        
        self._write("\n")
    
    def record_prompt_response(self, prompt: str, response: str):
        """Record interactive prompt and response."""
        if self.entries and self.entries[-1]["type"] == "command":
            self.entries[-1]["outputs"].append({
                "type": "prompt",
                "prompt": prompt,
                "response": response
            })
        
        if self.format == "markdown":
            self._write(f"🔤 {prompt}: {response}\n")
    
    def finalize(self):
        """Finalize the transcript and close the file."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        if self.format == "markdown":
            self._write(f"\n---\nSession ended: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._write(f"Duration: {duration:.2f} seconds\n")
            self._write(f"Commands executed: {len(self.entries)}\n")
        elif self.format == "json":
            # Write complete JSON output
            output = {
                "session": {
                    "start_time": self.start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration
                },
                "entries": self.entries
            }
            self._write(json.dumps(output, indent=2))
        
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finalize()