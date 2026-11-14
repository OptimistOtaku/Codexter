"""Install the complete skill with gh into a disposable directory and use it.

Defaults to the local checkout; --github tests the published package instead.
Uses --dir so no user skill directories or home environment variables change.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def run(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github", action="store_true", help="Install from OptimistOtaku/Codexter")
    args = parser.parse_args()
    source_root = Path(__file__).resolve().parents[1]
    scratch = os.environ.get("CLEANUP_TEST_TMPDIR")
    if scratch:
        Path(scratch).mkdir(parents=True, exist_ok=True)
    print(run("gh", "--version").splitlines()[0])
    with tempfile.TemporaryDirectory(prefix="codexter-install-", dir=scratch) as temporary:
        fixture = Path(temporary).resolve()
        destination = fixture / "installed-skills"
        source = "OptimistOtaku/Codexter" if args.github else str(source_root)
        command = ["gh", "skill", "install", source, "codex-cleanup", "--agent", "codex",
                   "--scope", "user", "--dir", str(destination)]
        if not args.github:
            command.append("--from-local")
        print(run(*command).strip())
        installed = destination / "codex-cleanup"
        expected = source_root / "skills/codex-cleanup"
        for path in expected.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(expected)
            copied = installed / relative
            if not copied.is_file():
                raise RuntimeError(f"Installer omitted required file: {relative}")
            # gh injects source metadata into SKILL.md, so its bytes differ by design.
            if relative.as_posix() != "SKILL.md" and not args.github:
                if copied.read_bytes() != path.read_bytes():
                    raise RuntimeError(f"Installer altered a supporting file: {relative}")
        if "name: codex-cleanup" not in (installed / "SKILL.md").read_text(encoding="utf-8"):
            raise RuntimeError("Installed skill lost its discoverable name.")
        workspace = fixture / "project"
        workspace.mkdir()
        run("git", "init", str(workspace))
        helper = installed / "scripts/cleanup.py"

        def helper_command(action, *extra):
            return json.loads(run(sys.executable, "-B", str(helper), action,
                                  "--workspace", str(workspace), "--run", "smoke", *extra,
                                  cwd=fixture))

        created = helper_command("init")
        disposable = Path(created["temp"]) / "test-resource.txt"
        disposable.write_text("scratch", encoding="utf-8")
        evidence = Path(created["evidence"]) / "validation.txt"
        evidence.write_text("keep this evidence", encoding="utf-8")
        plan = helper_command("plan")
        if not disposable.exists() or plan["delete_files"] != 1:
            raise RuntimeError("Installed helper failed its non-destructive preview.")
        result = helper_command("apply", "--plan", plan["plan"])
        if result["status"] != "complete" or disposable.exists():
            raise RuntimeError("Installed helper did not clean its disposable resource.")
        if evidence.read_text(encoding="utf-8") != "keep this evidence":
            raise RuntimeError("Installed helper failed to preserve evidence.")
        print("PASS: complete skill installed; helper ran from another directory; evidence preserved.")
    print("PASS: isolated installation and test resources removed.")


if __name__ == "__main__":
    main()
