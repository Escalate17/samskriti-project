# samskriti-project

A local MCP server that lets multiple AI coding tools share structured project state — decisions, tasks, bugs — so they coordinate without re-explaining.

## The problem

You make a decision with one AI tool, then switch to another and have to re-explain everything from scratch. Each assistant starts cold, with no idea what was already decided, tried, or rejected. This server gives them a shared, structured ledger of your project so any tool can read what the others wrote.

## Install

One command, cross-platform (macOS, Linux, Windows):

```bash
# With uv (recommended)
uvx --from git+https://github.com/Escalate17/samskriti-project samskriti-project

# Or install the CLI with pipx
pipx install git+https://github.com/Escalate17/samskriti-project
```

This installs the `samskriti-project` executable.

## Connect

Add the server to your tool's MCP config.

**Claude Code** (`~/.claude.json`):
```json
{
  "mcpServers": {
    "samskriti-project": {
      "command": "samskriti-project",
      "args": []
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "samskriti-project": {
      "command": "samskriti-project",
      "args": []
    }
  }
}
```

**Codex** (`~/.codex/config.toml`):
```toml
[mcp_servers.samskriti-project]
command = "samskriti-project"
args = []
```

## Tools

- **record_project_entry** — store an entry (goal, update, decision, convention, bug, task, rejected_idea).
- **get_project_state** — read a readable summary, grouped by category.
- **search_project_state** — keyword search across entries.
- **update_project_entry** — edit an entry's title, content, or status.
- **list_projects** — list all tracked projects.

## Try it in 30 seconds

1. In **tool A** (e.g. Claude Code): *"Record a decision in project 'demo': we're using SQLite for local storage."*
2. In **tool B** (e.g. Cursor): *"Get the project state for 'demo'."*

Tool B reads back the decision tool A just wrote — no re-explaining.

## Privacy

100% local. No cloud, no account, your data never leaves your machine. State is stored in a SQLite database under `~/.samskriti/` (override with the `SAMSKRITI_HOME` or `SAMSKRITI_PROJECT_DB` environment variable). Your AI client's own data and privacy policies still apply.

## Status

Early / validating. This is a working prototype being tested with real workflows. Bugs, rough edges, and missing features are expected — issues and feedback are very welcome.

## License

MIT — see [LICENSE](LICENSE).
