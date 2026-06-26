# samskriti-project

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-stdio%20server-7c3aed.svg)](https://modelcontextprotocol.io/)

A local MCP server that lets multiple AI coding tools share structured project state — decisions, tasks, bugs — so they coordinate without re-explaining.

```
   Claude Code      Cursor        Codex
       │              │             │
       │  read/write  │  read/write │
       └──────────────┼─────────────┘
                      ▼
            ┌───────────────────────┐
            │   samskriti-project   │   (local MCP server, stdio)
            └───────────┬───────────┘
                        ▼
              ┌───────────────────┐
              │   SQLite store    │   ~/.samskriti/  (100% local)
              └───────────────────┘
```

## The problem

You make a decision with one AI tool, then switch to another and have to re-explain everything from scratch. Each assistant starts cold, with no idea what was already decided, tried, or rejected. This server gives them a shared, structured ledger of your project so any tool can read what the others wrote.

## Install

Install with **pipx** (recommended — this puts the `samskriti-project` command on your PATH so your AI tools can find it):

```bash
pipx install git+https://github.com/Escalate17/samskriti-project
```

Don't have pipx? Install it first: `python3 -m pip install --user pipx && python3 -m pipx ensurepath` (then restart your terminal).

To verify the install worked:

```bash
samskriti-project --help
```

If you see the help text, you're ready to connect it.

## Connect

Add the server to your AI tool's MCP config, then **fully restart the tool**.

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

> If your tool can't find the command, it's a PATH issue — run `which samskriti-project` to get the full path, and use that full path as the `command` value instead.

## Verify it's connected

In **Claude Code**, type `/mcp` — you should see `samskriti-project` listed with its 8 tools. (Cursor and Codex have similar MCP status indicators in their settings.)

## Tools

- **record_project_entry** — store an entry (goal, update, decision, convention, bug, task, rejected_idea).
- **get_project_state** — read a readable summary, grouped by category.
- **search_project_state** — keyword search across entries.
- **update_project_entry** — edit an entry's title, content, or status.
- **list_projects** — list all tracked projects.

Quick shortcuts for common actions:

- **catchup** — "catch me up": a fast recap of a project (latest entries + open-task count).
- **open** — "what's open": list the active tasks, each with its ID.
- **log** — quick-log a decision; the title is auto-derived from the content if you omit it.

> **Already installed?** Run `pipx reinstall samskriti-project` to pick up the new commands.
> If you installed an earlier build (it shows up as `samskriti-project-local` in `pipx list`),
> migrate once: `pipx uninstall samskriti-project-local && pipx install git+https://github.com/Escalate17/samskriti-project`.

## Faster access: a `/sam` slash command

Typing *"use the samskriti-project MCP …"* every time is tedious. Both Claude Code and
Cursor support **custom slash commands** — Markdown prompt files you drop in a folder.
They don't bind directly to a tool, but they inject a prompt that tells the agent to use
this server, so `/sam <message>` does the right thing. (Codex has no slash-command
mechanism for MCP; just say *"use samskriti-project to …"* — the agent picks the tool.)

**Claude Code** — save [`slash-commands/claude-code/sam.md`](slash-commands/claude-code/sam.md) to one of:
- `~/.claude/commands/sam.md` (available in every project), or
- `<your-project>/.claude/commands/sam.md` (that project only).

Then in Claude Code: `/sam what's open` or `/sam log we're dropping the Redis cache`.
The `$ARGUMENTS` placeholder in the file receives everything you type after `/sam`.

**Cursor** (1.6+) — save [`slash-commands/cursor/sam.md`](slash-commands/cursor/sam.md) to:
- `~/.cursor/commands/sam.md` (global), or
- `<your-project>/.cursor/commands/sam.md` (that project only).

Then type `/` in Cursor's Agent box, pick **sam**, and add your message.

No true client feature binds a slash command straight to an MCP call yet — this command
file is the closest supported equivalent, and it works today.

## Try it in 30 seconds

1. In **tool A** (e.g. Claude Code): *"Record a decision in project 'demo': we're using SQLite for local storage."*
2. In **tool B** (e.g. Cursor): *"Get the project state for 'demo'."*

Tool B reads back the decision tool A just wrote — no re-explaining.

## Demo

<img width="2880" height="1800" alt="Image" src="https://github.com/user-attachments/assets/514bcdc0-4219-4987-bf3b-9fe273b1728e" />

<img width="2880" height="1800" alt="Image" src="https://github.com/user-attachments/assets/3e862787-0809-40f5-af33-742fc5a48050" />

## Privacy

100% local. No cloud, no account, your data never leaves your machine. State is stored in a SQLite database under `~/.samskriti/` (override with the `SAMSKRITI_HOME` or `SAMSKRITI_PROJECT_DB` environment variable). Your AI client's own data and privacy policies still apply.

## Status

Early / validating. This is a working prototype being tested with real workflows. Bugs, rough edges, and missing features are expected — issues and feedback are very welcome.

## License

MIT — see [LICENSE](LICENSE).
