import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("installer", Path(__file__).resolve().parents[1] / "installer.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.root = self.base / "kit"
        self.write(self.root / "rules/AGENTS.md", b"Use clear explanations.\n")
        self.write(self.root / "skills/ponytail/SKILL.md", b"Ponytail\n")
        self.write(self.root / "skills/ponytail/LICENSE", b"MIT\n")
        self.write(self.root / "skills/starter-scrapling/SKILL.md", b"Scrapling\n")

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def snapshot(self):
        return {str(p.relative_to(self.home)): p.read_bytes()
                for p in self.home.rglob("*") if p.is_file()}

    def install(self, **kwargs):
        changes, backup = installer.plan(self.home, root=self.root, **kwargs)
        if changes:
            installer.transact(self.home, changes, backup)
        return changes, backup

    def test_default_dry_run_writes_nothing(self):
        before = self.snapshot()
        with patch.object(installer, "plan", wraps=installer.plan) as spy:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(installer.main(["--home", str(self.home)]), 0)
            self.assertEqual(spy.call_count, 1)
        self.assertEqual(self.snapshot(), before)

    def test_preserves_rules_config_and_auth_with_hashed_backup(self):
        original = b"# Existing rules\nKeep this exactly."
        self.write(self.home / ".codex/AGENTS.md", original)
        self.write(self.home / ".codex/config.toml", b'model = "unchanged"\n')
        self.write(self.home / ".codex/auth.json", b'{"secret":"test-only"}')
        before = self.snapshot()
        _, backup = self.install()
        for name in (".codex/config.toml", ".codex/auth.json"):
            self.assertEqual((self.home / name).read_bytes(), before[name])
        self.assertTrue((self.home / ".codex/AGENTS.md").read_bytes().startswith(original))
        manifest = json.loads((backup / "manifest.json").read_text())
        entry = manifest[".codex/AGENTS.md"]
        self.assertEqual((backup / entry["backup"]).read_bytes(), original)
        self.assertEqual(entry["sha256"], installer.digest(original))
        after = self.snapshot()
        self.assertEqual(self.install()[0], {})
        self.assertEqual(self.snapshot(), after)

    def test_existing_identical_skill_is_adopted_but_never_deleted(self):
        for name in ("SKILL.md", "LICENSE"):
            self.write(self.home / ".agents/skills/ponytail" / name,
                       (self.root / "skills/ponytail" / name).read_bytes())
        self.install()
        self.install(uninstall=True)
        self.assertEqual((self.home / ".agents/skills/ponytail/SKILL.md").read_bytes(), b"Ponytail\n")

    def test_collision_has_no_partial_changes(self):
        self.write(self.home / ".agents/skills/ponytail/SKILL.md", b"My own skill")
        before = self.snapshot()
        with self.assertRaises(installer.Conflict):
            self.install()
        self.assertEqual(self.snapshot(), before)

    def test_optional_skill_installs_without_dependencies(self):
        self.install()
        self.assertFalse((self.home / ".agents/skills/starter-scrapling").exists())
        self.install(with_scrapling=True)
        self.assertTrue((self.home / ".agents/skills/starter-scrapling/SKILL.md").is_file())
        self.assertFalse((self.home / ".venv").exists())

    def test_uninstall_preserves_outside_edits(self):
        original = b"Original rules\n"
        self.write(self.home / ".codex/AGENTS.md", original)
        self.install()
        agents = self.home / ".codex/AGENTS.md"
        agents.write_bytes(b"New prefix\n" + agents.read_bytes() + b"New suffix\n")
        self.install(uninstall=True)
        self.assertEqual(agents.read_bytes(), b"New prefix\n" + original + b"New suffix\n")
        self.assertFalse((self.home / ".agents/skills/ponytail/SKILL.md").exists())
        self.assertEqual(self.install(uninstall=True)[0], {})

    def test_modified_skill_refuses_uninstall_without_partial_changes(self):
        self.install()
        (self.home / ".agents/skills/ponytail/SKILL.md").write_bytes(b"User edited")
        before = self.snapshot()
        with self.assertRaises(installer.Conflict):
            self.install(uninstall=True)
        self.assertEqual(self.snapshot(), before)

    def test_modified_managed_block_refuses_uninstall(self):
        self.install()
        agents = self.home / ".codex/AGENTS.md"
        agents.write_bytes(agents.read_bytes().replace(b"clear", b"detailed"))
        before = self.snapshot()
        with self.assertRaises(installer.Conflict):
            self.install(uninstall=True)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_parent_and_target_refused(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.home / ".codex").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(installer.Conflict):
            self.install()
        self.assertEqual(list(outside.iterdir()), [])
        (self.home / ".codex").unlink()
        self.write(outside / "rules", b"Do not touch")
        (self.home / ".codex").mkdir()
        (self.home / ".codex/AGENTS.md").symlink_to(outside / "rules")
        with self.assertRaises(installer.Conflict):
            self.install()
        self.assertEqual((outside / "rules").read_bytes(), b"Do not touch")

    def test_io_failure_rolls_back_original_content(self):
        self.write(self.home / ".codex/AGENTS.md", b"Original")
        before = self.snapshot()
        changes, backup = installer.plan(self.home, root=self.root)
        real_write = installer.atomic_write
        failed = False

        def fail_once(path, data, mode=0o600):
            nonlocal failed
            if path == self.home / ".agents/skills/ponytail/SKILL.md" and not failed:
                failed = True
                raise OSError("Simulated disk failure")
            return real_write(path, data, mode)

        with patch.object(installer, "atomic_write", side_effect=fail_once):
            with self.assertRaises(OSError):
                installer.transact(self.home, changes, backup)
        self.assertTrue(failed)
        self.assertEqual(self.snapshot(), before)

    def test_cli_apply_uninstall_and_reinstall(self):
        with contextlib.redirect_stdout(io.StringIO()):
            for flags in (["--apply"], ["--uninstall", "--apply"], ["--apply"]):
                self.assertEqual(installer.main(["--home", str(self.home), *flags]), 0)

    def test_custom_codex_home_requires_explicit_target(self):
        with patch.dict("os.environ", {"CODEX_HOME": str(self.base / "custom")}):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                installer.main([])


if __name__ == "__main__":
    unittest.main()
