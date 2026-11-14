"""Behavioral checks using isolated real filesystem fixtures."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/codex-cleanup/scripts/cleanup.py"
spec = importlib.util.spec_from_file_location("cleanup", SCRIPT)
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        scratch = os.environ.get("CLEANUP_TEST_TMPDIR")
        if scratch:
            Path(scratch).mkdir(parents=True, exist_ok=True)
        self.fixture = tempfile.TemporaryDirectory(prefix="cleanup-test-", dir=scratch)
        self.addCleanup(self.fixture.cleanup)
        self.workspace = Path(self.fixture.name).resolve()
        # Isolate fixtures from any enclosing repository or user Git configuration.
        subprocess.run(["git", "init", str(self.workspace)], check=True, capture_output=True)
        self.workspace, self.base = cleanup.locations(self.workspace, "task-1")
        cleanup.init(self.workspace, self.base)

    def put(self, rel, text="temporary"):
        target = self.base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def plan(self, *keeps):
        return cleanup.plan(self.workspace, self.base, list(keeps))

    def apply(self, plan):
        return cleanup.apply(self.workspace, self.base, plan["plan"])

    def test_preview_preserves_files_and_apply_keeps_evidence_and_other_work(self):
        scratch = self.put("temp/tests/fixture.txt", "12345")
        cache = self.put("cache/entry.bin", "abc")
        evidence = self.put("evidence/failure.log", "important failure")
        output = self.workspace / "outputs/final.txt"
        output.parent.mkdir()
        output.write_text("deliverable")
        source = self.workspace / "untracked-source.py"
        source.write_text("important code")
        plan = self.plan()
        self.assertTrue(scratch.exists())
        self.assertEqual((plan["delete_files"], plan["logical_bytes"]), (2, 8))
        result, code = self.apply(plan)
        self.assertEqual((result["status"], code), ("complete", 0))
        self.assertFalse(scratch.exists())
        self.assertFalse(cache.exists())
        self.assertEqual(evidence.read_text(), "important failure")
        self.assertEqual(output.read_text(), "deliverable")
        self.assertEqual(source.read_text(), "important code")
        for name in ("temp", "cache", "plans", "receipts", "evidence"):
            self.assertTrue((self.base / name).is_dir())
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertEqual(receipt["logical_bytes"], 8)
        self.assertEqual(len(receipt["deleted"]), 2)

    def test_explicit_keep_is_persistent_and_covers_descendants(self):
        keep = self.put("temp/repro/input.txt")
        disposable = self.put("temp/not-repro/file.txt")
        first = self.plan("temp/repro")
        self.apply(first)
        self.assertTrue(keep.exists())
        self.assertFalse(disposable.exists())
        self.assertEqual(self.plan()["delete_files"], 0)

    def test_keep_entire_cache(self):
        kept = self.put("cache/shared-for-review/blob")
        self.apply(self.plan("cache"))
        self.assertTrue(kept.exists())

    def test_protected_names_survive(self):
        protected = [self.put(rel) for rel in (
            "temp/.env.local", "temp/outputs/final", "cache/evidence/trace",
            "temp/credentials.json", "temp/.codex/config.toml")]
        self.apply(self.plan())
        self.assertTrue(all(p.exists() for p in protected))

    def test_refuse_adopting_existing_directory(self):
        sentinel = self.put("temp/important")
        with self.assertRaises(FileExistsError):
            cleanup.init(self.workspace, self.base)
        self.assertTrue(sentinel.exists())

    def test_traversal_run_and_plan_ids_are_refused(self):
        for run in ("../other", ".", "task/x", "task\\x", "/tmp", "x:" ):
            with self.subTest(run=run), self.assertRaises(cleanup.Refusal):
                cleanup.locations(self.workspace, run)
        with self.assertRaises(cleanup.Refusal):
            cleanup.apply(self.workspace, self.base, "../../manifest")

    def test_bad_keep_paths_are_refused(self):
        for keep in ("temp/../evidence", "evidence", "/temp/foo", "temp//x", "temp\\x", "cache/C:foo"):
            with self.subTest(keep=keep), self.assertRaises(cleanup.Refusal):
                self.plan(keep)

    def test_added_or_deleted_file_invalidates_plan_before_any_delete(self):
        original = self.put("temp/a")
        plan = self.plan()
        new = self.put("cache/new")
        with self.assertRaises(cleanup.Refusal):
            self.apply(plan)
        self.assertTrue(original.exists())
        new.unlink()
        plan = self.plan()
        original.unlink()
        other = self.put("temp/other")
        with self.assertRaises(cleanup.Refusal):
            self.apply(plan)
        self.assertTrue(other.exists())

    def test_hash_detects_same_size_edit_with_restored_mtime(self):
        original = self.put("temp/a", "first")
        plan = self.plan()
        stamp = original.stat()
        original.write_text("other")
        os.utime(original, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaises(cleanup.Refusal):
            self.apply(plan)
        self.assertEqual(original.read_text(), "other")

    def test_changed_keeps_invalidate_old_plan(self):
        original = self.put("temp/a")
        old = self.plan()
        self.plan("temp/a")
        with self.assertRaises(cleanup.Refusal):
            self.apply(old)
        self.assertTrue(original.exists())

    def test_plan_tampering_is_refused(self):
        original = self.put("temp/a")
        plan = self.plan()
        path = Path(plan["report"])
        value = json.loads(path.read_text())
        value["entries"][1]["path"] = "../outside"
        path.write_bytes(cleanup.encode(value))
        with self.assertRaises(cleanup.Refusal):
            self.apply(plan)
        # Even recomputing the digest cannot introduce arbitrary deletion paths.
        value.pop("digest")
        value["digest"] = cleanup.digest(value)
        path.write_bytes(cleanup.encode(value))
        with self.assertRaises(cleanup.Refusal):
            self.apply(plan)
        self.assertTrue(original.exists())

    def test_manifest_location_mismatch_is_refused(self):
        self.put("temp/a")
        target = self.base / "manifest.json"
        value = json.loads(target.read_text())
        value["workspace"] = str(self.workspace.parent)
        target.write_bytes(cleanup.encode(value))
        with self.assertRaises(cleanup.Refusal):
            self.plan()

    def test_replay_cannot_delete_recreated_files(self):
        self.put("temp/a")
        plan = self.plan()
        self.apply(plan)
        recreated = self.put("temp/a", "new work")
        result, code = self.apply(plan)
        self.assertEqual((result["status"], code), ("already_applied", 0))
        self.assertEqual(recreated.read_text(), "new work")

    def test_second_fresh_cleanup_is_empty(self):
        self.put("temp/a")
        self.apply(self.plan())
        result, code = self.apply(self.plan())
        self.assertEqual((result["deleted_files"], result["logical_bytes"], code), (0, 0, 0))

    def test_nested_git_is_blocker_even_inside_keep(self):
        self.put("temp/repo/.git/config")
        with self.assertRaises(cleanup.Refusal):
            self.plan("temp/repo")

    def test_git_tracked_file_is_retained(self):
        tracked = self.put("temp/tracked.txt")
        loose = self.put("temp/loose.txt")
        subprocess.run(["git", "init", str(self.workspace)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.workspace), "add", "--", str(tracked)], check=True, capture_output=True)
        self.apply(self.plan())
        self.assertTrue(tracked.exists())
        self.assertFalse(loose.exists())

    def test_git_missing_fails_closed(self):
        original = self.put("temp/a")
        with patch.object(cleanup.subprocess, "run", side_effect=FileNotFoundError("git unavailable")):
            with self.assertRaises(cleanup.Refusal):
                self.plan()
        self.assertTrue(original.exists())

    def test_git_broken_metadata_fails_closed(self):
        (self.workspace / ".git/HEAD").write_text("invalid head\n")
        with self.assertRaises(cleanup.Refusal):
            self.plan()

    def test_audit_failure_does_not_claim_no_deletion(self):
        self.put("temp/a")
        plan = self.plan()
        native = cleanup.replace_json

        def replace(path, value):
            if path.parent.name == "receipts":
                raise PermissionError("fixture simulates receipt write failure")
            return native(path, value)

        with patch.object(cleanup, "replace_json", replace):
            with self.assertRaises(cleanup.AuditFailure) as error:
                self.apply(plan)
        self.assertEqual(error.exception.result["status"], "partial")
        self.assertEqual(error.exception.result["deleted_files"], 1)

    def test_nonrepository_workspace_is_supported_when_git_confirms_it(self):
        response = subprocess.CompletedProcess([], 128, b"", b"fatal: not a git repository")
        native = cleanup.os.path.lexists

        def exists(path):
            return False if Path(path).name == ".git" else native(path)

        with patch.object(cleanup.os.path, "lexists", exists), patch.object(cleanup.subprocess, "run", return_value=response):
            self.assertEqual(cleanup.tracked_files(self.workspace, self.base), set())

    def test_symbolic_link_attribute_is_rejected_without_following(self):
        target = self.put("temp/link")
        native = Path.lstat

        def lstat(path, *args, **kwargs):
            result = native(path, *args, **kwargs)
            if path == target:
                fields = list(result)
                fields[0] = (fields[0] & ~0o170000) | 0o120000
                return os.stat_result(fields)
            return result

        with patch.object(Path, "lstat", lstat):
            with self.assertRaises(cleanup.Refusal):
                self.plan()
        self.assertTrue(target.exists())

    def test_hardlinks_are_blockers(self):
        external = self.workspace / "original"
        external.write_text("keep me")
        os.link(external, self.base / "temp/link")
        with self.assertRaises(cleanup.Refusal):
            self.plan()
        self.assertEqual(external.read_text(), "keep me")

    def test_symlink_and_dangling_symlink_are_blockers(self):
        link = self.base / "temp/link"
        outside = self.workspace / "outside"
        outside.write_text("keep")
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"OS does not permit symlink creation: {exc}")
        for _ in range(2):
            with self.assertRaises(cleanup.Refusal):
                self.plan()
            if outside.exists():
                outside.unlink()

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_windows_junction_is_blocker_and_target_survives(self):
        target = self.workspace / "outside-dir"
        target.mkdir()
        sentinel = target / "important.txt"
        sentinel.write_text("keep")
        junction = self.base / "temp/junction"
        # One fixed shell command creates a test junction; deletion stays in Python.
        subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
                       check=True, capture_output=True)
        self.addCleanup(lambda: os.rmdir(junction) if os.path.lexists(junction) else None)
        with self.assertRaises(cleanup.Refusal):
            self.plan()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_link_added_after_plan_prevents_all_deletion(self):
        original = self.put("temp/a")
        plan = self.plan()
        outside = self.workspace / "outside"
        outside.write_text("keep")
        os.link(outside, self.base / "cache/link")
        with self.assertRaises(cleanup.Refusal):
            self.apply(plan)
        self.assertTrue(original.exists())

    def test_other_run_is_untouched(self):
        _, other = cleanup.locations(self.workspace, "other-task")
        cleanup.init(self.workspace, other)
        sentinel = other / "temp/user.txt"
        sentinel.write_text("other task")
        self.put("temp/a")
        self.apply(self.plan())
        self.assertEqual(sentinel.read_text(), "other task")

    def test_busy_lock_refuses_without_deletion(self):
        original = self.put("temp/a")
        (self.base / ".cleanup.lock").write_text("another process")
        with self.assertRaises(cleanup.Refusal):
            self.plan()
        self.assertTrue(original.exists())

    def test_partial_cleanup_has_receipt_and_stops_on_failure(self):
        self.put("temp/a")
        blocked = self.put("temp/b")
        untouched = self.put("temp/c")
        plan = self.plan()
        native = Path.unlink

        def unlink(path, *args, **kwargs):
            if path == blocked:
                raise PermissionError("fixture simulates busy file")
            return native(path, *args, **kwargs)

        with patch.object(Path, "unlink", unlink):
            result, code = self.apply(plan)
        self.assertEqual((result["status"], code, result["deleted_files"]), ("partial", 1, 1))
        self.assertTrue(blocked.exists())
        self.assertTrue(untouched.exists())
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertEqual(receipt["deleted"], ["temp/a"])
        self.assertEqual(receipt["errors"][0]["path"], "temp/b")

    def test_cli_runs_from_unrelated_cwd(self):
        self.put("cache/a", "abc")
        command = [sys.executable, "-B", str(SCRIPT), "plan", "--workspace", str(self.workspace), "--run", "task-1"]
        result = subprocess.run(command, cwd=self.workspace.parent, check=True, text=True, capture_output=True)
        plan = json.loads(result.stdout)
        self.assertEqual((plan["status"], plan["delete_files"]), ("planned", 1))


if __name__ == "__main__":
    unittest.main()
