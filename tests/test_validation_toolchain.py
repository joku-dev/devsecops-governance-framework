from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap_validation_env.sh"
VALIDATE_ALL = ROOT / "scripts" / "validate_all.sh"
TOOLCHAIN = ROOT / "scripts" / "validation-toolchain.env"


def load_toolchain() -> dict[str, str]:
    values = {}
    for line in TOOLCHAIN.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


class ValidationToolchainTests(unittest.TestCase):
    def test_shell_scripts_are_valid_and_executable(self):
        for script in (BOOTSTRAP, VALIDATE_ALL):
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["bash", "-n", str(script)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertTrue(os.access(script, os.X_OK))

    def test_opa_version_and_platform_checksums_are_pinned(self):
        toolchain = load_toolchain()
        self.assertRegex(toolchain["OPA_VERSION"], r"^\d+\.\d+\.\d+$")

        checksum_keys = {
            "OPA_DARWIN_AMD64_SHA256",
            "OPA_DARWIN_ARM64_SHA256",
            "OPA_LINUX_AMD64_STATIC_SHA256",
            "OPA_LINUX_ARM64_STATIC_SHA256",
        }
        self.assertTrue(checksum_keys.issubset(toolchain))
        for key in checksum_keys:
            self.assertRegex(toolchain[key], r"^[0-9a-f]{64}$")

    def test_python_validation_dependencies_are_exactly_pinned(self):
        requirements = (ROOT / "requirements-validation.txt").read_text(encoding="utf-8").splitlines()
        self.assertTrue(requirements)
        for requirement in requirements:
            with self.subTest(requirement=requirement):
                self.assertRegex(requirement, r"^[A-Za-z0-9_.-]+==[^=\s]+$")

    def test_governance_ci_uses_the_pinned_validation_toolchain(self):
        workflow = (ROOT / ".github" / "workflows" / "governance-ci.yml").read_text(encoding="utf-8")
        opa_version = load_toolchain()["OPA_VERSION"]

        self.assertIn("python -m pip install -r requirements-validation.txt", workflow)
        self.assertIn(f"version: {opa_version}", workflow)
        self.assertNotIn("version: latest", workflow)

    def test_scripts_expose_help_without_creating_an_environment(self):
        with tempfile.TemporaryDirectory() as tempdir:
            env = dict(os.environ, VALIDATION_VENV=str(Path(tempdir) / "validation"))
            for script in (BOOTSTRAP, VALIDATE_ALL):
                with self.subTest(script=script.name):
                    result = subprocess.run(
                        [str(script), "--help"],
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, msg=result.stderr)
                    self.assertIn("Usage:", result.stdout)
                    self.assertFalse(Path(env["VALIDATION_VENV"]).exists())

    def test_validation_reports_an_unprepared_environment(self):
        with tempfile.TemporaryDirectory() as tempdir:
            missing_environment = Path(tempdir) / "missing"
            env = dict(os.environ, VALIDATION_VENV=str(missing_environment))
            result = subprocess.run(
                [str(VALIDATE_ALL), "--check-tools"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertFalse(missing_environment.exists())

        self.assertEqual(result.returncode, 1)
        self.assertIn("bootstrap_validation_env.sh", result.stderr)
