#!/bin/bash
# Research mode - Claude with ONLY validation script access
# NO file reading, NO writing, NO web access, NO editing
# ONLY execute validation scripts through Bash

claude --dangerously-skip-permissions \
  --disallowed-tools \
    Read \
    Write \
    Edit \
    MultiEdit \
    NotebookEdit \
    Glob \
    Grep \
    WebFetch \
    WebSearch \
  --allowed-tools \
    Bash \
    BashOutput \
    KillShell \
    TodoWrite \
    Task \
    SlashCommand \
    ExitPlanMode \
    ListMcpResourcesTool \
    ReadMcpResourceTool \
  --system-prompt "You are in RESEARCH MODE. You can ONLY:
1. Use browser (MCP tools) to find companies
2. Execute validation scripts via Bash
3. Provide data to scripts via stdin
4. Manage tasks with TodoWrite

You CANNOT:
- Read files directly (use 'cat' via Bash if needed)
- Write files directly (only through validation scripts)
- Edit files directly
- Search with Grep/Glob
- Use WebFetch/WebSearch

Workflow:
1. Browse to find companies
2. Extract data from what you see
3. Pipe data to validation scripts:
   echo 'url' | python scripts/add_link.py --subdir [category]
   cat << EOF | python scripts/validate_and_save.py --subdir [category]
   {json data}
   EOF

All data MUST go through validation scripts."
