# Runtime cleanup

Record resources at creation. Prefer the owning tool's lifecycle API over operating-system process control. Do not assume a tool exists: inspect its current documentation and capabilities.

| Resource | Ownership proof | End-of-task action |
| --- | --- | --- |
| Test/dev server | Recorded execution-session handle, launch command, cwd, start time | Stop through that session, allow graceful shutdown, verify exit. Preserve if needed for review. |
| Browser page/context | Exact page or context handle created for this task | Save required screenshots/downloads, close the owned page/context. Do not close pre-existing user tabs or a shared browser. |
| Playwright or similar local test browser | Browser/context object launched by this task | Await context/browser close in a `finally` block. Do not terminate unrelated browser processes. |
| REPL/tool runtime | Dedicated task-local session and no pending operations | Save outputs, dispose handles; use supported reset only if exclusive. Resetting bindings is not proof that native app resources closed. |
| Container/test database | Exact ID, task label and creation record | Gracefully stop and remove only the disposable instance. Retain volumes/data unless explicitly created as disposable. |
| Remote test resource | Exact owner/account, resource ID and task tag | Use its service API within existing authorization; verify final state. Never delete by name prefix alone. |
| Worktree/branch | Creation record and clean Git status | Preserve by default as work/evidence. Remove only within explicitly requested scope after confirming changes are saved. |
| Shared MCP/Codex runtime | Usually host-owned or shared | Leave running. Save diagnostics and report the limitation. |

For OS-level process stopping, require a recorded creation identity plus a fresh start-time/command/cwd match to prevent PID reuse mistakes. A port number or executable name alone is insufficient. Use graceful stop first; force termination needs explicit authorization for that exact verified resource. Never terminate the host, its shared runtime, or a process of uncertain ownership.

When memory pressure is relevant, record timestamp, OS, app/runtime version, process identity/start time, and the metric's name and unit before and after disposal. Working set, RSS and private committed bytes measure different things. Avoid summing shared memory and claiming a physical-RAM total. Do not collect raw environment variables, credentials or full private transcripts. No measurement means report resources closed, not MB of RAM saved.

A simple `evidence/resources.json` can contain a `resources` array with `kind`, `owner_session`, `id`, `created_at`, `command`, `cwd`, `keep_for_review`, `teardown`, and `status`. This is a human/agent record, not executable input to the file helper. Store exact IDs locally and redact public copies.
