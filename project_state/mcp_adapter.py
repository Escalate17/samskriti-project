#!/usr/bin/env python3
"""
Samskriti Local Project State MCP Server.
Exposes project-state sharing tools locally over stdio.
"""
import sqlite3
import os
import uuid
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# 1. Database Configuration
DEFAULT_DB_DIR = Path(os.environ.get("SAMSKRITI_HOME", str(Path.home() / ".samskriti")))
DEFAULT_DB_FILE = DEFAULT_DB_DIR / "project_state.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL UNIQUE,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL,
    source_agent TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_entries_project_id ON entries(project_id);
CREATE INDEX IF NOT EXISTS idx_entries_category ON entries(category);
CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status);
"""

class ProjectStateRepository:
    def __init__(self, db_path=None):
        if db_path is None:
            env_db = os.environ.get("SAMSKRITI_PROJECT_DB")
            if env_db:
                self.db_path = Path(env_db)
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                self.db_path = DEFAULT_DB_FILE
                DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
        else:
            self.db_path = Path(db_path)
            if self.db_path != Path(":memory:"):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                
        self.conn = self._get_connection()
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        if self.db_path != Path(":memory:"):
            conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        with self.conn:
            self.conn.executescript(SCHEMA_SQL)

    def get_or_create_project(self, name: str, root_path: str) -> dict:
        name = name.strip()
        root_path = os.path.abspath(root_path)
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE root_path = ?", (root_path,))
        row = cursor.fetchone()
        if row:
            if row["name"] != name:
                with self.conn:
                    self.conn.execute("UPDATE projects SET name = ? WHERE id = ?", (name, row["id"]))
                cursor.execute("SELECT * FROM projects WHERE id = ?", (row["id"],))
                return dict(cursor.fetchone())
            return dict(row)
            
        project_id = str(uuid.uuid4())
        with self.conn:
            self.conn.execute(
                "INSERT INTO projects (id, name, root_path) VALUES (?, ?, ?)",
                (project_id, name, root_path)
            )
            
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        return dict(cursor.fetchone())

    def get_project_by_id(self, project_id: str) -> dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_project_by_name_or_path(self, identifier: str) -> dict:
        cursor = self.conn.cursor()
        abs_path = os.path.abspath(identifier)
        cursor.execute(
            "SELECT * FROM projects WHERE name = ? OR root_path = ?",
            (identifier, abs_path)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
            
        cursor.execute("SELECT * FROM projects")
        for r in cursor.fetchall():
            proj = dict(r)
            if proj["name"].lower() == identifier.lower() or os.path.basename(proj["root_path"]).lower() == identifier.lower():
                return proj
        return None

    def list_projects(self) -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY name ASC")
        return [dict(r) for r in cursor.fetchall()]

    def create_entry(self, project_id: str, category: str, title: str, content: str, status: str, source_agent: str = None) -> dict:
        entry_id = str(uuid.uuid4())
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO entries (id, project_id, category, title, content, status, source_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (entry_id, project_id, category, title, content, status, source_agent)
            )
            self.conn.execute(
                "UPDATE projects SET updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) WHERE id = ?",
                (project_id,)
            )
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        return dict(cursor.fetchone())

    def get_entry(self, entry_id: str) -> dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_entry(self, entry_id: str, title: str = None, content: str = None, status: str = None) -> dict:
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if content is not None:
            updates.append("content = ?")
            params.append(content)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
            
        if not updates:
            return self.get_entry(entry_id)
            
        updates.append("updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")
        params.append(entry_id)
        
        query = f"UPDATE entries SET {', '.join(updates)} WHERE id = ?"
        with self.conn:
            self.conn.execute(query, params)
            self.conn.execute(
                """
                UPDATE projects 
                SET updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) 
                WHERE id = (SELECT project_id FROM entries WHERE id = ?)
                """,
                (entry_id,)
            )
            
        return self.get_entry(entry_id)

    def get_entries_by_project(self, project_id: str, category: str = None) -> list:
        cursor = self.conn.cursor()
        if category:
            cursor.execute(
                "SELECT * FROM entries WHERE project_id = ? AND category = ? ORDER BY created_at DESC",
                (project_id, category)
            )
        else:
            cursor.execute(
                "SELECT * FROM entries WHERE project_id = ? ORDER BY category ASC, created_at DESC",
                (project_id,)
            )
        return [dict(r) for r in cursor.fetchall()]

    def search_entries(self, project_id: str, query: str) -> list:
        cursor = self.conn.cursor()
        like_query = f"%{query}%"
        cursor.execute(
            """
            SELECT * FROM entries 
            WHERE project_id = ? 
              AND (title LIKE ? OR content LIKE ? OR category LIKE ? OR source_agent LIKE ?)
            ORDER BY created_at DESC
            """,
            (project_id, like_query, like_query, like_query, like_query)
        )
        return [dict(r) for r in cursor.fetchall()]

    def close(self):
        self.conn.close()

# 2. Service Layer Configuration
VALID_CATEGORIES = {"goal", "update", "decision", "convention", "bug", "task", "rejected_idea"}
VALID_STATUSES = {"active", "completed", "resolved", "superseded"}

class ProjectStateService:
    def __init__(self, repo: ProjectStateRepository):
        self.repo = repo

    def resolve_project(self, identifier: str) -> dict:
        identifier = identifier.strip()
        if not identifier:
            raise ValueError("Project identifier cannot be empty")
            
        proj = self.repo.get_project_by_name_or_path(identifier)
        if proj:
            return proj
            
        if "/" in identifier or "\\" in identifier or os.path.exists(identifier):
            root_path = os.path.abspath(identifier)
            name = os.path.basename(root_path.rstrip("/\\"))
            if not name:
                name = identifier
        else:
            name = identifier
            root_path = str(DEFAULT_DB_DIR / "projects" / name)
            
        return self.repo.get_or_create_project(name, root_path)

    def record_entry(self, project_identifier: str, category: str, title: str, content: str, status: str = None, source_agent: str = None) -> dict:
        category = category.strip().lower()
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
            
        if status is not None:
            status = status.strip().lower()
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
        else:
            status = "active"
            
        title = title.strip()
        if not title:
            raise ValueError("Title cannot be empty")
            
        content = content.strip()
        if not content:
            raise ValueError("Content cannot be empty")
            
        project = self.resolve_project(project_identifier)
        return self.repo.create_entry(
            project_id=project["id"],
            category=category,
            title=title,
            content=content,
            status=status,
            source_agent=source_agent
        )

    def update_entry(self, entry_id: str, title: str = None, content: str = None, status: str = None) -> dict:
        if status is not None:
            status = status.strip().lower()
            if status not in VALID_STATUSES:
                raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}")
                
        entry = self.repo.get_entry(entry_id)
        if not entry:
            raise ValueError(f"Entry with id '{entry_id}' not found")
            
        return self.repo.update_entry(entry_id, title=title, content=content, status=status)

    def get_project_state_summary(self, project_identifier: str, category: str = None) -> str:
        project = self.resolve_project(project_identifier)
        
        if category:
            category = category.strip().lower()
            if category not in VALID_CATEGORIES:
                raise ValueError(f"Invalid category '{category}'. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
                
        entries = self.repo.get_entries_by_project(project["id"], category)
        if not entries:
            cat_suffix = f" in category '{category}'" if category else ""
            return f"Project: {project['name']} ({project['root_path']})\nNo state recorded yet{cat_suffix}."
            
        grouped = {}
        for entry in entries:
            cat = entry["category"]
            grouped.setdefault(cat, []).append(entry)
            
        lines = []
        lines.append(f"=== Project State: {project['name']} ===")
        lines.append(f"Root path: {project['root_path']}")
        lines.append("")
        
        cats_to_display = [category] if category else sorted(grouped.keys())
        for cat in cats_to_display:
            if cat not in grouped:
                continue
            lines.append(f"## {cat.upper().replace('_', ' ')}")
            for entry in grouped[cat]:
                status_str = f" [{entry['status']}]" if entry['status'] != 'active' else ""
                agent_str = f" (by {entry['source_agent']})" if entry['source_agent'] else ""
                lines.append(f"- **{entry['title']}**{status_str}{agent_str}")
                content_lines = entry['content'].splitlines()
                for cl in content_lines:
                    lines.append(f"  {cl}")
                lines.append("")
                
        return "\n".join(lines).strip()

    def search_project_state(self, project_identifier: str, query: str) -> str:
        project = self.resolve_project(project_identifier)
        query = query.strip()
        if not query:
            return self.get_project_state_summary(project_identifier)
            
        entries = self.repo.search_entries(project["id"], query)
        if not entries:
            return f"No results matching '{query}' found for project '{project['name']}'."
            
        lines = []
        lines.append(f"=== Search results for '{query}' in project '{project['name']}' ===")
        lines.append("")
        for entry in entries:
            agent_str = f" by {entry['source_agent']}" if entry['source_agent'] else ""
            lines.append(f"[{entry['category'].upper()}] {entry['title']} (status: {entry['status']}{agent_str})")
            lines.append(f"ID: {entry['id']}")
            content_lines = entry['content'].splitlines()
            for cl in content_lines:
                lines.append(f"  {cl}")
            lines.append("")
            
        return "\n".join(lines).strip()

    def list_projects(self) -> list:
        return self.repo.list_projects()

# 3. MCP JSON-RPC Server
SERVER_INFO = {"name": "samskriti-project-state", "version": "0.1.0"}
DEFAULT_PROTOCOL = "2024-11-05"

TOOLS = [
    {
        "name": "record_project_entry",
        "description": "Stores a structured project-state entry (goal, update, decision, convention, bug, task, rejected_idea).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name or absolute root path"},
                "category": {
                    "type": "string", 
                    "description": "Category: goal, update, decision, convention, bug, task, rejected_idea"
                },
                "title": {"type": "string", "description": "Concise summary title"},
                "content": {"type": "string", "description": "Detailed description or payload"},
                "source_agent": {"type": "string", "description": "Optional name of the agent calling this tool (e.g. 'claude-code')"},
                "status": {"type": "string", "description": "Optional status: active, completed, resolved, superseded"}
            },
            "required": ["project", "category", "title", "content"]
        }
    },
    {
        "name": "get_project_state",
        "description": "Returns a concise, readable summary of project state, grouped by category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name or absolute root path"},
                "category": {"type": "string", "description": "Optional specific category to filter by"}
            },
            "required": ["project"]
        }
    },
    {
        "name": "search_project_state",
        "description": "Search the project state ledger using a simple keyword query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name or absolute root path"},
                "query": {"type": "string", "description": "Keywords to match against title/content"}
            },
            "required": ["project", "query"]
        }
    },
    {
        "name": "update_project_entry",
        "description": "Update an existing project entry's title, content, or status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Unique UUID of the entry to edit"},
                "title": {"type": "string", "description": "Optional new title"},
                "content": {"type": "string", "description": "Optional new content"},
                "status": {"type": "string", "description": "Optional new status (active, completed, resolved, superseded)"}
            },
            "required": ["id"]
        }
    },
    {
        "name": "list_projects",
        "description": "Returns a list of all known projects tracked by Samskriti V1.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

repo = ProjectStateRepository()
service = ProjectStateService(repo)

def _call_tool(name: str, args: dict) -> str:
    if name == "record_project_entry":
        entry = service.record_entry(
            project_identifier=args["project"],
            category=args["category"],
            title=args["title"],
            content=args["content"],
            status=args.get("status"),
            source_agent=args.get("source_agent")
        )
        return f"Successfully recorded entry: [{entry['category'].upper()}] '{entry['title']}' (ID: {entry['id']})."
        
    elif name == "get_project_state":
        return service.get_project_state_summary(
            project_identifier=args["project"],
            category=args.get("category")
        )
        
    elif name == "search_project_state":
        return service.search_project_state(
            project_identifier=args["project"],
            query=args["query"]
        )
        
    elif name == "update_project_entry":
        entry = service.update_entry(
            entry_id=args["id"],
            title=args.get("title"),
            content=args.get("content"),
            status=args.get("status")
        )
        return f"Successfully updated entry {entry['id']}. New status: {entry['status']}."
        
    elif name == "list_projects":
        projs = service.list_projects()
        if not projs:
            return "No projects registered yet."
        lines = []
        for p in projs:
            lines.append(f"- {p['name']} ({p['root_path']}) ID: {p['id']}")
        return "\n".join(lines)
        
    raise ValueError(f"unknown tool: {name}")

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()

def _result(req_id, result: dict) -> None:
    _send({"jsonrpc": "2.0", "id": req_id, "result": result})

def _error(req_id, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})

HELP_TEXT = """\
samskriti-project — local MCP server for shared AI project state

A stdio Model Context Protocol (MCP) server. It is normally launched by your
AI tool (Claude Code, Cursor, Codex, ...) via an MCP config entry, not run
directly. Running it with no arguments starts the stdio JSON-RPC loop and waits
for an MCP client on stdin.

Usage:
  samskriti-project            Start the MCP server (stdio JSON-RPC)
  samskriti-project --help     Show this help and exit
  samskriti-project --version  Show version and exit

Tools exposed: record_project_entry, get_project_state, search_project_state,
update_project_entry, list_projects

State is stored locally in a SQLite database under ~/.samskriti/
(override with SAMSKRITI_HOME or SAMSKRITI_PROJECT_DB).
"""


def main() -> None:
    args = sys.argv[1:]
    if any(a in ("-h", "--help") for a in args):
        sys.stdout.write(HELP_TEXT)
        sys.stdout.flush()
        return
    if any(a in ("-V", "--version") for a in args):
        sys.stdout.write(f"{SERVER_INFO['name']} {SERVER_INFO['version']}\n")
        sys.stdout.flush()
        return

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        method = msg.get("method")
        req_id = msg.get("id")

        if method == "initialize":
            proto = (msg.get("params") or {}).get("protocolVersion", DEFAULT_PROTOCOL)
            _result(req_id, {
                "protocolVersion": proto,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            })
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            _result(req_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params") or {}
            try:
                text = _call_tool(params.get("name", ""), params.get("arguments") or {})
                _result(req_id, {"content": [{"type": "text", "text": text}], "isError": False})
            except Exception as e:
                _result(req_id, {"content": [{"type": "text", "text": f"error: {str(e)}"}], "isError": True})
        elif req_id is not None:
            _error(req_id, -32601, f"method not found: {method}")

if __name__ == "__main__":
    main()
