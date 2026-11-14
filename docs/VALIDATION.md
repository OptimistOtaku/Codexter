# Validation evidence

Executed on 2026-11-15 using Windows and Python 3.13.1, with Git 2.35.1.windows.2.

## Results

- Skill Creator's `quick_validate.py`: **Skill is valid!**
- `python -B -m unittest discover -s tests -v`: **29 tests run; 28 passed, 1 skipped.**
- Real Windows hard-link and directory-junction fixtures: passed. Their targets were preserved.
- Real symbolic-link fixture: skipped because this Windows account lacks symbolic-link creation privilege (WinError 1314). A separate simulated symbolic-link file-type test passed. This does not substitute for the skipped real symlink test.
- Tests used isolated fixtures; no existing user cache or Codex state was deleted. Test fixtures were removed after execution. Link fixture creation required running outside this session's restricted sandbox.

The suite checks preview without deletion, preservation of evidence/deliverables and untracked source outside the run, persistent keeps, protected filenames, Git-tracked files, malformed Git metadata and repository boundaries, missing Git, path traversal, changed/tampered plans, file-content changes, run isolation, lock contention, repeat cleanup, replay protection, partial deletion and audit-write failure reporting. A CLI invocation from a different working directory also passed.

## Corrections found during testing

Git could fall back to an enclosing repository when a nested repository's metadata was malformed. The helper now verifies that Git's resolved root matches the nearest metadata boundary. The behavior is covered by a regression test. Audit-write failures after deletion now report partial cleanup instead of implying that nothing changed.

## Unverified environments and outcomes

The GitHub Actions matrix is configured for Windows, macOS and Linux with Python 3.10 and 3.13; those remote jobs have not run as part of local validation. No live browser/server/container was terminated for these tests. Runtime teardown guidance is not an automated lifecycle test. No physical disk-space or RAM improvement was measured, and no internal Codex memory leak was reproduced or repaired.
