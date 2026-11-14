# Codex Cleanup implementation plan

1. Research official skill discovery and lifecycle hooks; compare first-person reports of retained memory. Separate disk cleanup, task resource disposal, and application memory leaks.
2. Provide a normally discoverable `codex-cleanup` skill, with an optional repository instruction for end-of-task use. No background service or automatic global configuration changes.
3. Implement a Python 3.10+ standard-library helper: create a new owned run, inventory only its temporary/cache directories, preview deletion, revalidate a saved plan, then delete the exact files. Preserve evidence, manifests, plans, receipts, and explicit keeps.
4. Guide runtime cleanup through the owning tool's supported close/stop/dispose operation. Require proof of task ownership. Never bulk-kill processes or reset shared runtimes.
5. Test real deletions and refusals in isolated workspaces, including changed plans, tracked files, traversal, links, Windows junctions, evidence, and repeated cleanup. Capture results without promising RAM savings.
6. Prepare a public repository with installation/use instructions, sources, CI, license, and a factual X draft. Install the validated skill locally. Publish destinations and final public wording can be chosen once the result is reviewable.

Acceptance: no deletion outside a freshly initialized run's `temp/` or `cache/`; no deletion of Git-tracked files; no following links; preview is non-destructive; evidence survives; stale/tampered plans fail closed; receipts distinguish logical file bytes from RAM and physical free space.
