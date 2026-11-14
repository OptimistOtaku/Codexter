#!/usr/bin/env python3
"""Bounded, plan-first cleanup of newly created task scratch trees."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import uuid

VERSION = 1
RUN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
ROOTS = ("temp", "cache")
PROTECTED = {
    ".git", ".agents", ".codex", ".ssh", ".aws", ".gnupg", ".azure",
    "evidence", "outputs", "deliverables", "credentials", "credentials.json",
    "auth.json", "secrets", "secrets.json", "plans", "receipts",
}


class Refusal(Exception):
    """A precondition failed; no deletion should be attempted."""


class AuditFailure(Exception):
    """Deletion may have begun but the audit record could not be updated."""

    def __init__(self, path, receipt, error):
        self.result = {"status": "partial", "receipt": str(path),
                       "deleted_files": len(receipt["deleted"]),
                       "logical_bytes": receipt["logical_bytes"],
                       "error": f"Audit update failed: {error}; inspect before retrying."}
        super().__init__(self.result["error"])


def save_receipt(path, receipt):
    try:
        replace_json(path, receipt)
    except (OSError, Refusal) as exc:
        raise AuditFailure(path, receipt, exc) from exc


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def check_path(path):
    """Check every existing component without first resolving through links."""
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise Refusal(f"Link or reparse point: {part}")


def plain_file(path):
    check_path(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise Refusal(f"Not a single-link regular file: {path}")
    return info


def read_json(path):
    plain_file(path)
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise Refusal(f"Expected JSON object: {path}")
    return value


def write_new(path, value):
    check_path(path)
    with path.open("xb") as handle:
        handle.write(encode(value))


def replace_json(path, value):
    plain_file(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    write_new(temporary, value)
    try:
        check_path(path)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def locations(workspace, run):
    if not RUN_RE.fullmatch(run):
        raise Refusal("Invalid run ID (use 1-64 ASCII letters/digits/hyphens/underscores).")
    workspace = Path(os.path.abspath(workspace))
    check_path(workspace)
    if not workspace.is_dir() or workspace == Path(workspace.anchor):
        raise Refusal("Workspace must be an existing directory other than a filesystem root.")
    base = workspace / "work" / "codex-cleanup" / run
    check_path(base)
    return workspace, base


def init(workspace, base):
    base.parent.mkdir(parents=True, exist_ok=True)
    check_path(base.parent)
    base.mkdir()  # Exclusive: never adopt existing files.
    for name in (*ROOTS, "evidence", "plans", "receipts"):
        (base / name).mkdir()
    manifest = {
        "schema": VERSION, "owner": uuid.uuid4().hex, "created_at": now(),
        "workspace": str(workspace), "base": str(base), "keep": [],
    }
    write_new(base / "manifest.json", manifest)
    return {"status": "initialized", "run": base.name, "base": str(base),
            **{name: str(base / name) for name in (*ROOTS, "evidence")}}


@contextmanager
def locked(base):
    check_path(base)
    lock = base / ".cleanup.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Refusal("Run is locked; inspect its owner before removing a stale lock.") from exc
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(f"pid={os.getpid()} time={now()}\n")
        yield
    finally:
        check_path(lock)
        lock.unlink()


def keep_path(value):
    if not isinstance(value, str) or "\\" in value or ":" in value:
        raise Refusal("Keep paths must use forward slashes and be run-relative.")
    parts = value.split("/")
    if not parts or parts[0] not in ROOTS or any(p in ("", ".", "..") for p in parts):
        raise Refusal("Keep paths must be literal paths in temp/ or cache/.")
    return str(PurePosixPath(value))


def manifest_for(workspace, base):
    manifest = read_json(base / "manifest.json")
    if (manifest.get("schema") != VERSION or manifest.get("workspace") != str(workspace)
            or manifest.get("base") != str(base)
            or not ID_RE.fullmatch(str(manifest.get("owner", "")))):
        raise Refusal("Manifest ownership or location mismatch.")
    if not isinstance(manifest.get("keep"), list):
        raise Refusal("Invalid keep list.")
    for value in manifest["keep"]:
        keep_path(value)
    for name in (*ROOTS, "evidence", "plans", "receipts"):
        target = base / name
        check_path(target)
        if not target.is_dir():
            raise Refusal(f"Missing run directory: {target}")
    return manifest


def tracked_files(workspace, base):
    nearest_metadata = next((parent for parent in (workspace, *workspace.parents)
                             if os.path.lexists(parent / ".git")), None)
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C", "LANG": "C"})

    def git(*args):
        try:
            return subprocess.run(
                ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", str(workspace), *args],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Refusal("Git inspection unavailable; preserve files until it can complete.") from exc

    result = git("rev-parse", "--show-toplevel")
    if result.returncode:
        if b"not a git repository" in result.stderr.lower():
            if nearest_metadata is not None:
                raise Refusal("Git metadata exists but repository inspection failed.")
            return set()
        raise Refusal("Cannot establish repository state; Git inspection failed.")
    repo = Path(os.fsdecode(result.stdout).strip())
    if nearest_metadata is None or repo != nearest_metadata:
        raise Refusal("Git resolved past the nearest metadata boundary; inspect repository state.")
    try:
        relative = base.relative_to(repo).as_posix()
    except ValueError as exc:
        raise Refusal("Repository root does not contain the cleanup run.") from exc
    result = git("ls-files", "--cached", "--full-name", "-z", "--",
                 f":(literal){relative}/temp", f":(literal){relative}/cache")
    if result.returncode:
        raise Refusal("Cannot inspect tracked files.")
    return {os.path.normcase(str(repo / os.fsdecode(p))) for p in result.stdout.split(b"\0") if p}


def signature(path):
    before = plain_file(path)
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    after = plain_file(path)
    attrs = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if attrs(before) != attrs(after):
        raise Refusal(f"File changed during inspection: {path}")
    return {"size": after.st_size, "mtime_ns": after.st_mtime_ns,
            "ctime_ns": after.st_ctime_ns, "device": after.st_dev,
            "inode": after.st_ino, "sha256": checksum.hexdigest()}


def snapshot(workspace, base, manifest):
    tracked = tracked_files(workspace, base)
    keeps = [value.casefold() for value in manifest["keep"]]
    entries = []

    def visit(path, inherited=None):
        check_path(path)
        info = path.lstat()
        rel = path.relative_to(base).as_posix()
        folded = rel.casefold()
        name = path.name.casefold()
        if name == ".git":
            raise Refusal(f"Nested Git metadata in disposable tree: {path}")
        reason = inherited
        if any(folded == keep or folded.startswith(keep + "/") for keep in keeps):
            reason = "explicit keep"
        if name in PROTECTED or name.startswith(".env"):
            reason = "protected name"
        if stat.S_ISDIR(info.st_mode):
            entry = {"path": rel, "kind": "directory", "device": info.st_dev,
                     "inode": info.st_ino, "action": "keep" if reason else "delete"}
            if reason:
                entry["reason"] = reason
            entries.append(entry)
            for child in sorted(path.iterdir(), key=lambda p: p.name):
                visit(child, reason)
        elif stat.S_ISREG(info.st_mode):
            if os.path.normcase(str(path)) in tracked:
                reason = "Git tracked"
            entry = {"path": rel, "kind": "file", **signature(path),
                     "action": "keep" if reason else "delete"}
            if reason:
                entry["reason"] = reason
            entries.append(entry)
        else:
            raise Refusal(f"Special file in disposable tree: {path}")

    for root in ROOTS:
        visit(base / root)
    return entries


def plan(workspace, base, extra_keeps):
    with locked(base):
        manifest = manifest_for(workspace, base)
        keeps = sorted(set(manifest["keep"] + [keep_path(value) for value in extra_keeps]))
        if keeps != manifest["keep"]:
            manifest["keep"] = keeps
            replace_json(base / "manifest.json", manifest)
        entries = snapshot(workspace, base, manifest)
        plan_id = uuid.uuid4().hex
        value = {"schema": VERSION, "id": plan_id, "created_at": now(),
                 "manifest_digest": digest(manifest), "entries": entries}
        value["digest"] = digest(value)
        target = base / "plans" / f"{plan_id}.json"
        write_new(target, value)
        files = [e for e in entries if e["kind"] == "file" and e["action"] == "delete"]
        return {"status": "planned", "plan": plan_id, "report": str(target),
                "delete_files": len(files), "logical_bytes": sum(e["size"] for e in files),
                "kept_files": sum(e["kind"] == "file" and e["action"] == "keep" for e in entries)}


def apply(workspace, base, plan_id):
    if not ID_RE.fullmatch(plan_id):
        raise Refusal("Use a hexadecimal plan ID returned by plan, not a path.")
    with locked(base):
        manifest = manifest_for(workspace, base)
        value = read_json(base / "plans" / f"{plan_id}.json")
        checksum = value.pop("digest", None)
        if value.get("schema") != VERSION or value.get("id") != plan_id or checksum != digest(value):
            raise Refusal("Plan integrity check failed.")
        if value.get("manifest_digest") != digest(manifest):
            raise Refusal("Manifest or retention rules changed; create a fresh plan.")
        receipt_path = base / "receipts" / f"{plan_id}.json"
        if os.path.lexists(receipt_path):
            receipt = read_json(receipt_path)
            if receipt.get("plan") != plan_id or receipt.get("plan_digest") != checksum:
                raise Refusal("Receipt identity mismatch.")
            if receipt.get("status") == "in_progress":
                raise Refusal("Previous apply was interrupted; inspect receipt and make a fresh plan.")
            return {"status": "already_applied", "result": receipt.get("status"),
                    "receipt": str(receipt_path)}, 0 if receipt.get("status") == "complete" else 1
        # Full preflight before the first deletion. Never execute targets supplied only by JSON.
        entries = snapshot(workspace, base, manifest)
        if value.get("entries") != entries:
            raise Refusal("Disposable tree changed; stop writers and create a fresh plan.")
        receipt = {"schema": VERSION, "plan": plan_id, "plan_digest": checksum,
                   "started_at": now(), "status": "in_progress", "deleted": [],
                   "removed_directories": [], "errors": [], "logical_bytes": 0}
        write_new(receipt_path, receipt)
        for entry in entries:
            if entry["kind"] != "file" or entry["action"] != "delete":
                continue
            path = base / entry["path"]
            try:
                manifest_for(workspace, base)
                if signature(path) != {key: entry[key] for key in signature_keys()}:
                    raise Refusal("File changed after preflight.")
                path.unlink()
                receipt["deleted"].append(entry["path"])
                receipt["logical_bytes"] += entry["size"]
            except (OSError, Refusal) as exc:
                receipt["errors"].append({"path": entry["path"], "error": str(exc)})
                break  # Preserve remaining material on the first unexpected condition.
            finally:
                save_receipt(receipt_path, receipt)
        if not receipt["errors"]:
            directories = sorted((e for e in entries if e["kind"] == "directory"),
                                 key=lambda e: e["path"].count("/"), reverse=True)
            for entry in directories:
                if entry["path"] in ROOTS or entry["action"] == "keep":
                    continue
                path = base / entry["path"]
                try:
                    check_path(path)
                    info = path.lstat()
                    if (info.st_dev, info.st_ino) != (entry["device"], entry["inode"]):
                        raise Refusal("Directory identity changed.")
                    if not any(path.iterdir()):
                        path.rmdir()
                        receipt["removed_directories"].append(entry["path"])
                except (OSError, Refusal) as exc:
                    receipt["errors"].append({"path": entry["path"], "error": str(exc)})
                    break
        receipt["status"] = "partial" if receipt["errors"] else "complete"
        receipt["finished_at"] = now()
        save_receipt(receipt_path, receipt)
        return {"status": receipt["status"], "receipt": str(receipt_path),
                "deleted_files": len(receipt["deleted"]), "logical_bytes": receipt["logical_bytes"],
                "errors": len(receipt["errors"])}, 1 if receipt["errors"] else 0


def signature_keys():
    return ("size", "mtime_ns", "ctime_ns", "device", "inode", "sha256")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "plan", "apply"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", required=True)
        command.add_argument("--run", required=True)
        if name == "plan":
            command.add_argument("--keep", action="append", default=[])
        if name == "apply":
            command.add_argument("--plan", required=True)
    args = parser.parse_args()
    try:
        workspace, base = locations(args.workspace, args.run)
        code = 0
        if args.command == "init":
            result = init(workspace, base)
        elif args.command == "plan":
            result = plan(workspace, base, args.keep)
        else:
            result, code = apply(workspace, base, args.plan)
        print(json.dumps(result, sort_keys=True))
        return code
    except AuditFailure as exc:
        print(json.dumps(exc.result, sort_keys=True))
        return 1
    except (Refusal, OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"status": "refused", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
