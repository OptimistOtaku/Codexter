# Research and design decisions

Reviewed: 2026-11-15. Sources describe different releases and environments; these reports do not diagnose this user's installation.

## What cleanup can achieve

OpenAI's [Build skills documentation](https://learn.chatgpt.com/docs/build-skills) describes skill discovery and on-demand loading. Skills provide a workflow; they do not themselves install a reliable finalizer after every other skill. Repository instructions can request end-of-task use. A crash or interrupted execution can bypass that workflow.

The [Hooks documentation](https://learn.chatgpt.com/docs/hooks) documents lifecycle events including `Stop` and `Interrupt`, plus review and trust for non-managed hooks. `Stop` can continue a turn, and does not establish that a multi-turn task has finished. An unconditional deletion hook would therefore be a poor default. Version-specific, separately reviewed hooks may be a future integration; this package installs none.

The first-person [Windows worker report #43405](https://github.com/openai/codex/issues/43405) describes high committed memory in runtime workers and Codex, with lower readings after normal exit. Its author explicitly says the observations do not prove a memory leak. That supports investigating worker lifetime, without concluding that deleting caches fixes it.

The first-person [desktop resource-lifecycle report #56868](https://github.com/openai/codex/issues/56868) reports lower aggregate memory after closing views and restarting, while noting workload differences and the absence of a demonstrated allocation leak. Renderer counts and summed per-process memory should not be presented as deduplicated RAM savings.

The [CLI TurnDiffTracker report #39231](https://github.com/openai/codex/issues/39231) describes a suspected internal allocation issue in a particular CLI release. This package neither reproduces nor patches that reported issue.

## Engineering conclusions

These are design inferences, not guarantees from OpenAI:

- Dispose of task-owned browser contexts, test servers, containers, and other handles through supported APIs. This can remove unnecessary work and release their associated resources.
- Treat disk cache removal separately. It reclaims disposable file data and may make later runs slower; it does not repair a live application's heap.
- Create temporary directories before use, with explicit ownership. A directory name, age, idle state, or ignored Git status is insufficient evidence that old material is disposable.
- Preserve compact validation results and failure diagnostics before teardown. Existing evidence is retained without automatic age or size pruning.
- Plan exact deletions and reject stale plans. Never infer task ownership from a process name or a large memory reading.
- If host memory pressure persists, preserve diagnostics and offer a normal restart after active work is saved. Do not terminate the running Codex host from the skill.

## Deliberate limits

The helper handles files only. Runtime teardown remains tool-specific and must be reported separately. It does not scan global temp directories, purge browser profiles or package-manager caches, erase Codex history/state/authentication, or clean up unrelated runs. It is not a memory-leak fix or a memory benchmark.

The helper rejects observed links/reparse points and rechecks paths before deletion. It is intended for a quiescent, trusted workspace, not as a security boundary against concurrent adversarial filesystem replacement. Git inspection fails closed when unavailable or inconclusive. Files deleted after explicit apply are not recoverable through this tool.
