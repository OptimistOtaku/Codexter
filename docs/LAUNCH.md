# Publication drafts

Repository: `OptimistOtaku/Codexter`.

Description: Codexter cleans up after your mess.

Publication status: [public repository](https://github.com/OptimistOtaku/Codexter) published; initial six-job CI matrix passed. X post remains a draft.

## Release copy

Codexter helps Codex finish a task by cleaning up its own disposable resources. It preserves deliverables and diagnostic evidence, uses a preview-and-apply file helper, and guides runtime teardown through verified task ownership. Invoke its installed skill as `$codex-cleanup`.

The helper requires Python 3.10+ and Git. It has no third-party Python dependencies. Tests cover deletion boundaries, preservation, stale plans, tracked files, links and partial failure. See `docs/VALIDATION.md` for the executed results and platform limits.

This is resource hygiene, not a fix for internal Codex memory leaks. It installs no background service or unconditional deletion hooks. Independent community project, MIT licensed.

## X post draft

Meet Codexter. Codexter cleans up after your mess.

A Codex skill for task-owned temp files, caches, test servers and browser sessions. Preserves work + evidence. Preview-first, no bulk process kills.

Resource hygiene, not a memory-leak fix.

https://github.com/OptimistOtaku/Codexter

Verify the repository is public before posting. This post is a draft and has not been posted.

## Publish sequence

1. Choose the GitHub owner and public repository destination; review the package and MIT license.
2. Publish this directory's source files, including tests and documentation. Keep local raw diagnostics, absolute-path receipts and test scratch data out of GitHub.
3. Run the configured CI matrix on GitHub. Do not claim macOS/Linux execution before those jobs finish.
4. Use the live repository link in the X draft, then post from the intended account after final wording is approved.
