# End-of-task integration

If the user wants routine cleanup after other skills, add this instruction to the project's existing `AGENTS.md`, preserving the other instructions:

```markdown
When a task creates temporary test files, disposable caches, test servers,
browser contexts, containers, or other temporary resources, use $codex-cleanup
to establish ownership before creating those resources when practical.
Before the final handoff, use $codex-cleanup to release resources owned only
by this task and clean its disposable files. Preserve deliverables, Git
changes, required previews, validation results, and failure evidence.
Report skipped resources and cleanup failures. Do not adopt unknown old
files, purge shared caches, or terminate Codex/shared runtimes.
```

Skill discovery and repository instructions guide the agent; they do not install a guaranteed callback or crash handler. After interruption, invoke cleanup explicitly using the recorded run and resource IDs, once active work is safe to stop. No hooks or global configuration changes are required.
