# File helper

Requires Python 3.10+, standard library only, and Git on PATH. Run the helper by its actual installed path. Git checks run read-only with optional locks disabled. It refuses to proceed if Git is missing or the workspace's repository status cannot be established.

## Commands

```text
python <skill-dir>/scripts/cleanup.py init --workspace <absolute-workspace> --run task-42
python <skill-dir>/scripts/cleanup.py plan --workspace <absolute-workspace> --run task-42 --keep temp/repro
python <skill-dir>/scripts/cleanup.py apply --workspace <absolute-workspace> --run task-42 --plan <plan-id>
```

`init` refuses an existing run directory. It creates the ownership manifest and empty `temp`, `cache`, `evidence`, `plans`, and `receipts` directories. No existing material is adopted. A run ID is 1–64 ASCII letters/digits/hyphens/underscores, starting with a letter/digit.

`plan` reads only the run and writes a new JSON plan under `plans/`. It deletes nothing. `--keep` is repeatable, literal and run-relative; it accepts only a path inside `temp/` or `cache/`, including either whole root. A keep covers descendants, and keeps used in any plan remain in the manifest for future plans. To remove a keep requires manual review/edit of the manifest; the CLI never clears retention rules. Default preservation includes Git-tracked files and protected names such as `.git`, `.env*`, credentials, evidence, outputs, plans and receipts.

`apply` takes the returned hexadecimal plan ID, not an arbitrary path. It recomputes the complete disposable-tree inventory, file hashes, identities and Git protection before any deletion. Added/deleted/modified files or changed retention rules invalidate the plan. A plan digest detects accidental/tampered edits; it is not a signature or protection from someone who can rewrite the entire workspace. Never edit a plan to add deletion targets.

Links, Windows reparse points/junctions, nested repositories and special files are blockers. Hard-linked files are blockers too. The helper never follows them. Protected ordinary files/directories stay in place. No recursive delete is used: individual validated files are unlinked and only then are validated empty directories removed. The `temp/` and `cache/` roots stay available.

Evidence, manifests, plans and receipts are retained with no automatic pruning. stdout reports only counts, logical file bytes and report locations. Receipts record deleted paths and per-path failures; do not publish local reports without reviewing paths and diagnostics. Logical bytes are file lengths, not physical disk-space gain or RAM saved.

Stop all writers before plan/apply. This is a cleanup helper for a trusted quiescent workspace, not an adversarial filesystem sandbox. It rechecks paths before each mutation, but cannot eliminate every OS-level time-of-check/time-of-use race on all supported platforms.

## Failure and recovery

Validation errors exit `2` without deletion. A filesystem failure during apply may leave partial deletion; exit `1` and a receipt report exactly what succeeded. Already-applied plans return their existing receipt, preventing replay from re-deleting recreated files. Use a new plan for new scratch data. An unexpectedly missing/tampered receipt is not proof of completion.

Nothing touches old unregistered scratch files, shared caches or other runs. Review those separately using creation records. Do not move important material into this helper's disposable trees to bypass its scope.
