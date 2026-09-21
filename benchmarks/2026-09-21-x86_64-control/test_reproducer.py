"""Exercise cache integrity and run isolation without downloading or measuring."""
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "linux", "the reproducer requires Linux")
class ReproducerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.workdir = self.root / "cache with spaces"
        downloads = self.workdir / "downloads"
        models = self.workdir / "model"
        downloads.mkdir(parents=True)
        models.mkdir()
        self.archive = downloads / "llama-b11065-bin-ubuntu-x64.tar.gz"
        self.model = models / "SmolLM2-135M-Q4_K_M.gguf"
        self.model.write_bytes(b"synthetic model fixture")
        binary = b'#!/usr/bin/env bash\nprintf "verified fixture executable\\n"\n'
        with tarfile.open(self.archive, "w:gz") as archive:
            member = tarfile.TarInfo("llama-b11065/llama-bench")
            member.size = len(binary)
            member.mode = 0o755
            archive.addfile(member, io.BytesIO(binary))

        script = Path(__file__).with_name("run.sh").read_text()
        for key, artifact in (("asset_sha", self.archive), ("model_sha", self.model)):
            original = next(line for line in script.splitlines() if line.startswith(key + "="))
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            script = script.replace(original, f"{key}={digest}", 1)
        self.script = self.root / "fixture-run.sh"
        self.script.write_text(script)

        shims = self.root / "shims"
        shims.mkdir()
        for name, body in {
            "taskset": 'shift 2\nexec "$@"\n',
            "sleep": "exit 0\n",
            "curl": "echo 'unexpected download' >&2\nexit 89\n",
        }.items():
            path = shims / name
            path.write_text("#!/usr/bin/env bash\n" + body)
            path.chmod(0o755)
        self.environment = dict(os.environ, WORKDIR=str(self.workdir))
        self.environment["PATH"] = str(shims) + os.pathsep + os.environ["PATH"]

    def run_script(self):
        return subprocess.run(
            ["bash", str(self.script)], env=self.environment,
            capture_output=True, text=True, timeout=30,
        )

    def test_reused_cache_extracts_verified_binary_and_preserves_prior_results(self):
        stale = self.workdir / "bin" / "llama-b11065" / "llama-bench"
        stale.parent.mkdir(parents=True)
        stale.write_text("#!/usr/bin/env bash\nexit 86\n")
        stale.chmod(0o755)
        first = self.run_script()
        self.assertEqual(first.returncode, 0, first.stderr)
        first_dir, = self.workdir.glob("run.*")
        first_results = {
            path.name: path.read_bytes() for path in (first_dir / "results").iterdir()
        }
        self.assertEqual(first_results["run-01.jsonl"], b"verified fixture executable\n")
        # A tampered previous extraction must not become a subsequent run's tool.
        (first_dir / "bin" / "llama-b11065" / "llama-bench").write_text(stale.read_text())
        second = self.run_script()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(len(list(self.workdir.glob("run.*"))), 2)
        self.assertEqual(first_results, {
            path.name: path.read_bytes() for path in (first_dir / "results").iterdir()
        })
        for run_dir in self.workdir.glob("run.*"):
            verified = subprocess.run(
                ["sha256sum", "--check", "checksums.sha256"],
                cwd=run_dir / "results", capture_output=True, text=True,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_modified_archive_is_rejected_before_execution(self):
        self.archive.write_bytes(b"modified archive")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAILED", result.stdout)
        self.assertEqual(list(self.workdir.glob("run.*")), [])

    def test_modified_model_is_rejected_before_execution(self):
        self.model.write_bytes(b"modified model")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAILED", result.stdout)
        self.assertEqual(list(self.workdir.glob("run.*")), [])


if __name__ == "__main__":
    unittest.main()
