#!/usr/bin/env python3
"""Offline, dry-run-first installer for the Codex starter kit (Python 3.9+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parent
BEGIN = "<!-- codex-starter-kit:begin -->"
END = "<!-- codex-starter-kit:end -->"


class Conflict(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe(path):
    """Do not follow symlinks, including existing ancestors of a new file."""
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise Conflict(f"Symlink refused: {part}")
    for parent in path.parents:
        if parent.exists() and not parent.is_dir():
            raise Conflict(f"Parent is not a directory: {parent}")


def read(path):
    safe(path)
    if path.exists() and not path.is_file():
        raise Conflict(f"Expected a regular file: {path}")
    return path.read_bytes() if path.exists() else None


def inside(home, relative):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise Conflict("Invalid path in receipt")
    result = home / relative
    safe(result)
    return result


def atomic_write(path, data, mode=0o600):
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as stream:
            os.chmod(temporary, mode)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def transact(home, changes, backup):
    """Snapshot first; roll back ordinary I/O failures without losing user files."""
    snapshots = {p: (read(p), p.stat().st_mode & 0o777 if p.exists() else 0o600)
                 for p in changes}
    created_dirs = []

    def mkdir(path):
        safe(path)
        if not path.exists():
            mkdir(path.parent)
            path.mkdir(mode=0o700)
            created_dirs.append(path)

    completed = []
    try:
        mkdir(backup)
        manifest = {}
        for number, (path, (data, mode)) in enumerate(snapshots.items()):
            name = str(number) + ".bin"
            manifest[str(path.relative_to(home))] = {
                "backup": name if data is not None else None,
                "sha256": digest(data) if data is not None else None,
                "mode": mode,
            }
            if data is not None:
                atomic_write(backup / name, data)
        atomic_write(backup / "manifest.json", json.dumps(manifest, indent=2).encode())
        for path, data in changes.items():
            safe(path)
            mkdir(path.parent)
            if data is None:
                path.unlink()
            else:
                atomic_write(path, data, snapshots[path][1])
            completed.append(path)
    except Exception:
        for path in reversed(completed):
            old, mode = snapshots[path]
            if old is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, old, mode)
        if backup.exists():
            for child in backup.iterdir():
                child.unlink()
        for path in reversed(created_dirs):
            path.rmdir()
        raise


def plan(home, with_scrapling=False, uninstall=False, root=ROOT):
    safe(home)
    agents = home / ".codex/AGENTS.md"
    state = home / ".codex/starter-kit/receipt.json"
    raw = read(state)
    receipt = json.loads(raw) if raw is not None else None
    if receipt is not None and receipt.get("version") != 1:
        raise Conflict("Unsupported installer receipt")
    current = read(agents)
    owned = dict(receipt["files"]) if receipt else {}
    for relative, expected in owned.items():
        parts = Path(relative).parts
        if len(parts) < 4 or parts[:2] != (".agents", "skills") or parts[2] not in ("ponytail", "starter-scrapling"):
            raise Conflict("Invalid owned skill path in receipt")
        data = read(inside(home, relative))
        if data is None or digest(data) != expected:
            raise Conflict(f"Installed file changed or missing: {relative}; restore it before continuing")
    segment = receipt["agents_segment"].encode() if receipt else None
    if segment and (segment.count(BEGIN.encode()) != 1 or segment.count(END.encode()) != 1):
        raise Conflict("Invalid managed block in receipt")
    if segment and (current is None or current.count(segment) != 1):
        raise Conflict("Managed AGENTS.md block changed or missing; restore it before continuing")
    changes = {}
    if uninstall:
        if receipt is None:
            return {}, None
        remaining = current.replace(segment, b"", 1)
        changes[agents] = remaining if remaining or receipt["agents_existed"] else None
        for relative in owned:
            changes[inside(home, relative)] = None
        changes[state] = None
    else:
        if receipt is None:
            if current and (BEGIN.encode() in current or END.encode() in current):
                raise Conflict("Managed marker exists without a receipt; refusing to replace it")
            template = read(root / "rules/AGENTS.md")
            if template is None:
                raise Conflict("Missing rules/AGENTS.md")
            text = template.decode("utf-8").strip()
            if BEGIN in text or END in text:
                raise Conflict("Template contains reserved managed markers")
            separator = b"\n\n" if current else b""
            segment = separator + (BEGIN + "\n" + text + "\n" + END + "\n").encode()
            changes[agents] = (current or b"") + segment
        skills = ["ponytail"] + (["starter-scrapling"] if with_scrapling else [])
        for name in skills:
            source = root / "skills" / name
            safe(source)
            if not source.is_dir() or read(source / "SKILL.md") is None:
                raise Conflict(f"Missing source skill: {source}")
            target = home / ".agents/skills" / name
            safe(target)
            if target.exists() and not target.is_dir():
                raise Conflict(f"Skill destination is not a directory: {target}")
            sources = {}
            for file in source.rglob("*"):
                safe(file)
                if not file.is_dir():
                    sources[file.relative_to(source)] = read(file)
            if target.exists():
                existing = {}
                for file in target.rglob("*"):
                    safe(file)
                    if not file.is_dir():
                        existing[file.relative_to(target)] = read(file)
                if existing != sources:
                    raise Conflict(f"Existing skill differs: {target}; no files were changed")
            else:
                for relative, data in sources.items():
                    destination = target / relative
                    changes[destination] = data
                    owned[str(destination.relative_to(home))] = digest(data)
        if not changes:
            return {}, None
        receipt = {
            "version": 1, "agents_segment": segment.decode(), "files": owned,
            "agents_existed": receipt["agents_existed"] if receipt else current is not None,
        }
    backup = home / ".codex/starter-kit/backups" / uuid.uuid4().hex
    safe(backup)
    if not uninstall:
        receipt["backup"] = str(backup.relative_to(home))
        receipt["installed_hashes"] = {str(p.relative_to(home)): digest(data)
                                       for p, data in changes.items() if data is not None}
        changes[state] = (json.dumps(receipt, indent=2) + "\n").encode()
    for path in changes:
        read(path)
    return changes, backup


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home(), help="Target home directory (default: your home)")
    parser.add_argument("--apply", action="store_true", help="Apply changes; otherwise only show a plan")
    parser.add_argument("--with-scrapling", action="store_true", help="Copy the optional skill; installs no dependencies")
    parser.add_argument("--uninstall", action="store_true", help="Remove only unchanged content owned by this installer")
    arguments = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(arguments)
    explicit_home = any(arg == "--home" or arg.startswith("--home=") for arg in arguments)
    configured_home = os.environ.get("CODEX_HOME")
    if configured_home and not explicit_home and Path(configured_home).expanduser().absolute() != Path.home() / ".codex":
        parser.error("Custom CODEX_HOME is not supported. Use --home PATH explicitly to target PATH/.codex and PATH/.agents.")
    if args.uninstall and args.with_scrapling:
        parser.error("--uninstall and --with-scrapling cannot be combined")
    home = Path(os.path.abspath(args.home.expanduser()))
    try:
        changes, backup = plan(home, args.with_scrapling, args.uninstall)
        if not changes:
            print("No changes needed.")
            return 0
        for path, data in changes.items():
            print(f"{'DELETE' if data is None else 'WRITE '} {path}")
        print(f"Backup and SHA-256 manifest: {backup}")
        if args.apply:
            transact(home, changes, backup)
            if args.uninstall:
                for path in changes:
                    if ".agents/skills/" in str(path.relative_to(home)):
                        parent = path.parent
                        while parent != home / ".agents/skills":
                            try:
                                parent.rmdir()
                            except OSError:
                                break
                            parent = parent.parent
            print("Completed. Existing configuration and authentication files were not changed.")
        else:
            print("Dry run only; nothing changed. Add --apply to execute.")
        return 0
    except (Conflict, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Refused: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
