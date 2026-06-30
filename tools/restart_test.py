import argparse
import contextlib
import importlib.util
import io
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RESTART_PATH = Path(__file__).resolve().parent / "restart.py"
SPEC = importlib.util.spec_from_file_location("restart", RESTART_PATH)
restart = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(restart)


def make_args(*, restart_only=False, no_cache=False, wait_timeout=180, docker_bin=""):
    return argparse.Namespace(
        restart_only=restart_only,
        no_cache=no_cache,
        wait_timeout=wait_timeout,
        docker_bin=docker_bin,
    )


def completed(returncode=0, stdout="", stderr=""):
    return restart.subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


class ResolveDockerBinTest(unittest.TestCase):
    def test_returns_override_when_executable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_docker = Path(tmpdir) / "docker"
            fake_docker.write_text("#!/bin/sh\n", encoding="utf-8")
            fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)

            resolved = restart.resolve_docker_bin(str(fake_docker))

        self.assertEqual(str(fake_docker), resolved)

    def test_fails_when_docker_missing_everywhere(self):
        with mock.patch.object(restart.shutil, "which", return_value=""):
            with mock.patch.dict(restart.os.environ, {}, clear=True):
                with mock.patch.object(restart, "DOCKER_EXTRA_PATHS", ["/nope/docker"]):
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as exc:
                            restart.resolve_docker_bin("")

        self.assertEqual(1, exc.exception.code)
        self.assertIn("cannot find `docker`", stderr.getvalue())


class ReadEnvValueTest(unittest.TestCase):
    def test_reads_key_and_ignores_comments_and_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text(
                "\n".join(
                    [
                        "# comment",
                        "",
                        "BIND_HOST=127.0.0.1",
                        'SERVER_PORT="8080"',
                        "EMPTY=",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual("127.0.0.1", restart.read_env_value(env_file, "BIND_HOST", "0.0.0.0"))
            self.assertEqual("8080", restart.read_env_value(env_file, "SERVER_PORT", "9999"))
            self.assertEqual("fallback", restart.read_env_value(env_file, "EMPTY", "fallback"))
            self.assertEqual("fallback", restart.read_env_value(env_file, "MISSING", "fallback"))

    def test_returns_default_when_file_missing(self):
        missing = Path("/nonexistent/.env")
        self.assertEqual("8080", restart.read_env_value(missing, "SERVER_PORT", "8080"))


class ComposeCommandTest(unittest.TestCase):
    def test_base_command_includes_base_file_and_project(self):
        command = restart.compose_base_command("/usr/bin/docker")

        self.assertEqual(["/usr/bin/docker", "compose"], command[:2])
        self.assertIn("-p", command)
        self.assertIn(restart.PROJECT_NAME, command)
        self.assertIn(restart.BASE_COMPOSE_FILE, " ".join(command))

    def test_override_layered_only_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deploy_dir = Path(tmpdir)
            (deploy_dir / restart.BASE_COMPOSE_FILE).write_text("services: {}\n", encoding="utf-8")
            with mock.patch.object(restart, "DEPLOY_DIR", deploy_dir):
                # Override absent -> base only.
                absent = restart.compose_base_command("/usr/bin/docker")
                self.assertEqual(1, absent.count("-f"))
                self.assertNotIn(restart.OVERRIDE_COMPOSE_FILE, " ".join(absent))

                # Override present -> layered on top of the base.
                (deploy_dir / restart.OVERRIDE_COMPOSE_FILE).write_text("services: {}\n", encoding="utf-8")
                present = restart.compose_base_command("/usr/bin/docker")
                self.assertEqual(2, present.count("-f"))
                self.assertIn(restart.OVERRIDE_COMPOSE_FILE, " ".join(present))

    def test_compose_up_builds_wait_command(self):
        with mock.patch.object(restart, "run_command") as run_command:
            restart.compose_up("/usr/bin/docker", 120)

        command = run_command.call_args.args[0]
        self.assertIn("up", command)
        self.assertIn("-d", command)
        self.assertIn("--wait", command)
        self.assertIn("--wait-timeout", command)
        self.assertIn("120", command)
        self.assertEqual(restart.DEPLOY_DIR, run_command.call_args.kwargs["cwd"])


class CollectPreflightIssuesTest(unittest.TestCase):
    def test_reports_unreachable_daemon_and_missing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deploy_dir = Path(tmpdir)
            with mock.patch.object(restart, "DEPLOY_DIR", deploy_dir):
                with mock.patch.object(restart, "ENV_FILE", deploy_dir / ".env"):
                    with mock.patch.object(restart.subprocess, "run") as run_cmd:
                        # 1) docker version fails, 2) docker compose version fails
                        run_cmd.side_effect = [completed(returncode=1), completed(returncode=1)]
                        issues = restart.collect_preflight_issues("/usr/bin/docker")

        joined = "\n".join(issues)
        self.assertIn("daemon not reachable", joined)
        self.assertIn("v2 plugin not available", joined)
        self.assertIn("compose file not found", joined)
        self.assertIn(".env`: env file not found", joined)

    def test_no_issues_when_everything_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            deploy_dir = Path(tmpdir)
            (deploy_dir / restart.BASE_COMPOSE_FILE).write_text("services: {}\n", encoding="utf-8")
            (deploy_dir / ".env").write_text("POSTGRES_PASSWORD=x\n", encoding="utf-8")

            with mock.patch.object(restart, "DEPLOY_DIR", deploy_dir):
                with mock.patch.object(restart, "ENV_FILE", deploy_dir / ".env"):
                    with mock.patch.object(restart.subprocess, "run") as run_cmd:
                        run_cmd.side_effect = [completed(stdout="29.4.1"), completed(stdout="v5.1.3")]
                        issues = restart.collect_preflight_issues("/usr/bin/docker")

        self.assertEqual([], issues)


class BuildImageTest(unittest.TestCase):
    def test_build_image_passes_version_commit_and_buildkit(self):
        with mock.patch.object(restart, "read_version", return_value="0.1.130"):
            with mock.patch.object(restart, "git_commit", return_value="abc1234"):
                with mock.patch.object(restart, "run_command") as run_command:
                    restart.build_image("/usr/bin/docker", no_cache=True)

        command = run_command.call_args.args[0]
        self.assertEqual(["/usr/bin/docker", "build", "-t", restart.IMAGE_TAG], command[:4])
        self.assertIn("VERSION=0.1.130", command)
        self.assertIn("COMMIT=abc1234", command)
        self.assertIn("--no-cache", command)
        self.assertEqual(".", command[-1])
        self.assertEqual(restart.REPO_ROOT, run_command.call_args.kwargs["cwd"])
        self.assertEqual("1", run_command.call_args.kwargs["env"]["DOCKER_BUILDKIT"])

    def test_build_image_without_no_cache(self):
        with mock.patch.object(restart, "read_version", return_value="0.1.130"):
            with mock.patch.object(restart, "git_commit", return_value="abc1234"):
                with mock.patch.object(restart, "run_command") as run_command:
                    restart.build_image("/usr/bin/docker", no_cache=False)

        command = run_command.call_args.args[0]
        self.assertNotIn("--no-cache", command)


class RunCommandTest(unittest.TestCase):
    def test_run_command_surfaces_child_output_before_exiting(self):
        command = ["docker", "build", "."]
        result = completed(returncode=1, stdout="build output\n", stderr="build error\n")

        with mock.patch.object(restart.subprocess, "run", return_value=result) as run_cmd:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as exc:
                        restart.run_command(command)

        self.assertEqual(1, exc.exception.code)
        run_cmd.assert_called_once()
        self.assertIn("build output", stdout.getvalue())
        self.assertIn("build error", stderr.getvalue())
        self.assertIn("command failed with exit code 1", stderr.getvalue())


class HealthCheckTest(unittest.TestCase):
    @staticmethod
    def _urlopen_cm(code, body):
        response = mock.MagicMock()
        response.getcode.return_value = code
        response.read.return_value = body
        context = mock.MagicMock()
        context.__enter__.return_value = response
        return context

    def test_health_check_ok_on_200(self):
        with mock.patch.object(
            restart.urllib.request, "urlopen", return_value=self._urlopen_cm(200, b'{"status":"ok"}')
        ):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                restart.health_check("0.0.0.0", "8080")
        self.assertIn("health OK", stdout.getvalue())

    def test_health_check_fails_on_non_200(self):
        with mock.patch.object(restart.urllib.request, "urlopen", return_value=self._urlopen_cm(503, b"down")):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    restart.health_check("127.0.0.1", "8080")
        self.assertEqual(1, exc.exception.code)
        self.assertIn("HTTP 503", stderr.getvalue())

    def test_health_check_fails_on_connection_error(self):
        with mock.patch.object(restart.urllib.request, "urlopen", side_effect=OSError("refused")):
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exc:
                    restart.health_check("127.0.0.1", "8080")
        self.assertEqual(1, exc.exception.code)
        self.assertIn("health check failed", stderr.getvalue())


class MainFlowTest(unittest.TestCase):
    def test_main_builds_then_deploys(self):
        with mock.patch.object(restart, "parse_args", return_value=make_args(restart_only=False)):
            with mock.patch.object(restart, "resolve_docker_bin", return_value="/usr/bin/docker"):
                with mock.patch.object(restart, "ensure_preflight_ready"):
                    with mock.patch.object(restart, "build_image") as build_image:
                        with mock.patch.object(restart, "compose_up") as compose_up:
                            with mock.patch.object(restart, "compose_ps"):
                                with mock.patch.object(restart, "read_env_value", side_effect=["127.0.0.1", "8080"]):
                                    with mock.patch.object(restart, "health_check") as health_check:
                                        restart.main()

        build_image.assert_called_once()
        compose_up.assert_called_once()
        health_check.assert_called_once()

    def test_main_restart_only_skips_build(self):
        with mock.patch.object(restart, "parse_args", return_value=make_args(restart_only=True)):
            with mock.patch.object(restart, "resolve_docker_bin", return_value="/usr/bin/docker"):
                with mock.patch.object(restart, "ensure_preflight_ready"):
                    with mock.patch.object(restart, "build_image") as build_image:
                        with mock.patch.object(restart, "compose_up") as compose_up:
                            with mock.patch.object(restart, "compose_ps"):
                                with mock.patch.object(restart, "read_env_value", side_effect=["127.0.0.1", "8080"]):
                                    with mock.patch.object(restart, "health_check"):
                                        restart.main()

        build_image.assert_not_called()
        compose_up.assert_called_once()


if __name__ == "__main__":
    unittest.main()
