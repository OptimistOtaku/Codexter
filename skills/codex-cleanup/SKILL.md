---
name: codex-cleanup
license: MIT
description: Clean up task-owned temp files, caches, and runtime resources when a Codex task or skill finishes. Preserve deliverables and diagnostic evidence. Also use before resource-heavy work to establish ownership. Does not repair internal memory leaks or clean the whole system.
---

# Codex Cleanup

Reduce leftover task resources and disposable disk data. Disk cleanup and runtime disposal are separate outcomes; do not claim to fix a memory leak or recover RAM without appropriate measurements.

## Establish ownership

When loaded before work, create an isolated run with the bundled helper. Resolve `scripts/cleanup.py` relative to this skill's location, not the project directory. Use a fresh run ID per task, including simultaneous tasks.

```text
python <skill-dir>/scripts/cleanup.py init --workspace <workspace> --run <unique-task-id>
```

The command returns absolute paths under `work/codex-cleanup/<run>/`: `temp/`, `cache/`, and `evidence/`. Route only task-specific scratch data and disposable caches into the first two. Save deliverables in their intended output location. Keep evidence and reusable resources outside those disposable directories. If a cache supports per-invocation configuration, point it at this run's `cache/` without changing global configuration.

Record task-owned runtime handles and teardown commands in `evidence/resources.json` as they are created. Include the owning tool/session ID; for a process, also its launch time, command and working directory. Record whether the resource must stay alive for user review. Do not store credentials. Read [runtime cleanup](references/runtime-cleanup.md) for resources that exist.

When invoked only at the end, use the existing task record. Do not initialize an empty run as proof of ownership over pre-existing files, adopt an old cache, or relocate unknown files to make them eligible. Preserve unknown resources and report them.

## Preserve evidence, then release resources

Before teardown, retain validation commands, exit codes, concise results, relevant versions, and failure logs/screenshots needed for reproduction. Preserve all existing evidence unless the user expressly requests its removal. Verify required evidence copies completed. Keep credentials out of reports and public artifacts.

Finish active tests, downloads and writes. Close only resources created exclusively for this task, using supported dispose/close/stop APIs. Keep previews or servers the user still needs. Follow existing session authorization and tool-specific restrictions. Do not kill all `node`, `python`, browser, MCP, or Codex processes, and do not reset a runtime shared with another task. A task-specific REPL reset is appropriate only after its needed values and outputs are saved and no other operation uses it.

## Preview and apply file cleanup

The helper supports only its newly created `temp/` and `cache/` trees. Read [helper usage](references/helper.md) for flags, retention rules, failures, and recovery. Use Python 3.10+; on Windows, `py -3` may substitute for `python`. If no supported Python runtime exists, leave file cleanup pending rather than improvising a broad recursive delete.

```text
python <skill-dir>/scripts/cleanup.py plan --workspace <workspace> --run <run>
python <skill-dir>/scripts/cleanup.py apply --workspace <workspace> --run <run> --plan <returned-plan-id>
```

Review the plan before applying. Pin evidence accidentally left in a disposable tree with repeatable `--keep temp/path` or `--keep cache/path` arguments during planning, or copy it to `evidence/` and verify it before replanning. The helper permanently deletes only the exact approved snapshot. User authorization to clean task-owned disposable data covers this bounded cleanup; do not introduce a confirmation loop. If a tool or permission boundary requires approval, retain the preview for review and obey that boundary.

Never widen cleanup into Codex's user data, history, databases, authentication, skills/plugins, `.git`, source trees, dependencies, shared package caches, system temp, browser profiles, or unrelated runs. Size, age and ignored status do not make a resource disposable. For an explicitly requested broader cache cleanup, inspect exact scope and use its documented owner-specific mechanism separately; this helper must remain bounded.

If apply rejects a changed tree, stop writers and generate a fresh plan. If it reports partial cleanup, retain the receipt and retry from a new plan only after resolving the cause. Never force through a stale plan. Verify runtime resources individually and review the file receipt. A completed file cleanup does not prove that processes or memory have been reclaimed.

## Handoff

Report deleted file count and logical bytes, preserved evidence location, runtime resources released, and anything retained or unresolved with reasons. Distinguish logical file bytes from physical disk space and RAM. If memory pressure persists in Codex itself, retain diagnostics and suggest normal app restart after saving work; do not restart or terminate the host automatically. Do not perform a cache purge merely because memory is high.

For reliable routine invocation, users can adopt the optional [repository instruction](references/integration.md). Automatic skill discovery is enabled by default, but this skill is not an always-running service or a guaranteed crash finalizer.
