# Run cleanup after other skills

Installing a skill makes it discoverable; it does not register a guaranteed end-of-task callback. For routine use, add the [bundled repository instruction](../skills/codex-cleanup/references/integration.md) to the project's existing `AGENTS.md`, preserving other instructions and project conventions. The snippet is shipped with the skill so it remains available after installation.

This is agent guidance, not a scheduler or crash handler. Run cleanup again explicitly if the task was interrupted, using its recorded run ID and resource record. Do not clean another still-active task's run.

## When another skill uses its own temporary directory

Prefer giving that skill this run's `temp/` or `cache/` path when its tools support it. Do not rewrite installed skills globally or redirect shared caches. If the tool requires its own directory, record its exact creation identity and use its supported cleanup method. The bounded file helper deliberately cannot adopt arbitrary existing directories.

## Optional hooks

Current [official hooks documentation](https://learn.chatgpt.com/docs/hooks) describes lifecycle events and trust review. A `Stop` event can occur at the end of a turn before the overall task is done. This package therefore does not provide an unconditional deletion hook. If a deployment adds a hook later, it must distinguish task completion and active writers, scope by session/run identity, preserve evidence, obey version-specific behavior and undergo the platform's review/trust process. Never disable hook trust to install cleanup.
