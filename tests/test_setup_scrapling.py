import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("setup_scrapling", Path(__file__).resolve().parents[1] / "setup_scrapling.py")
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class ScraplingSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve() / "home"
        self.home.mkdir()
        self.target = self.home / ".local/share/codex-starter-kit/scrapling"

    def tearDown(self):
        self.temp.cleanup()

    def run_setup(self, *flags):
        with patch.object(setup.sys, "argv", ["setup_scrapling.py", "--home", str(self.home), *flags]):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return setup.main()

    def test_dry_run_creates_nothing_and_starts_no_process(self):
        with patch.object(setup.venv, "EnvBuilder") as builder, patch.object(setup.subprocess, "run") as run:
            self.run_setup()
        builder.assert_not_called()
        run.assert_not_called()
        self.assertEqual(list(self.home.iterdir()), [])

    def test_symlink_ancestor_refused(self):
        outside = self.home.parent / "outside"
        outside.mkdir()
        (self.home / ".local").symlink_to(outside, target_is_directory=True)
        with patch.object(setup.venv, "EnvBuilder") as builder:
            with self.assertRaises(SystemExit) as error:
                self.run_setup("--apply")
        self.assertEqual(error.exception.code, 2)
        builder.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_directory_refused_and_preserved(self):
        self.target.mkdir(parents=True)
        sentinel = self.target / "user-file"
        sentinel.write_bytes(b"Leave unchanged")
        with patch.object(setup.venv, "EnvBuilder") as builder:
            with self.assertRaises(SystemExit):
                self.run_setup("--apply")
        builder.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), b"Leave unchanged")

    def test_pip_failure_removes_partial_runtime(self):
        def create_partial(path):
            path.mkdir()
            (path / "partial-package").write_bytes(b"Partial")

        failure = subprocess.CalledProcessError(1, ["pip", "install"])
        with patch.object(setup.venv, "EnvBuilder") as builder:
            builder.return_value.create.side_effect = create_partial
            with patch.object(setup.subprocess, "run", side_effect=failure) as run:
                with self.assertRaises(subprocess.CalledProcessError) as error:
                    self.run_setup("--apply")
        self.assertIs(error.exception, failure)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(self.target.exists())

    def test_venv_failure_before_creation_preserves_original_exception(self):
        failure = OSError("Cannot create virtual environment")
        with patch.object(setup.venv, "EnvBuilder") as builder:
            builder.return_value.create.side_effect = failure
            with self.assertRaises(OSError) as error:
                self.run_setup("--apply")
        self.assertIs(error.exception, failure)
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()
