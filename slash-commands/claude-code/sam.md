---
description: Shared project memory via samskriti-project (recap, tasks, log, search)
---

Use the `samskriti-project` MCP server to handle this request about the shared project memory:

$ARGUMENTS

Pick the most fitting tool:
- "catch me up" / recap / what's the state → `catchup`
- "what's open" / open tasks / todos → `open`
- "log ..." / record a quick decision → `log`
- record any entry (goal / bug / task / convention / update / rejected_idea) → `record_project_entry`
- read the full state → `get_project_state`
- find something → `search_project_state`
- change an existing entry → `update_project_entry`
- list known projects → `list_projects`

Default the `project` to the current working directory's project name unless I name a
different one. Pass `source_agent: "claude-code"` when you record or log anything.
