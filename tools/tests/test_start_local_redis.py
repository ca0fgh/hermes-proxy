import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "start_local_redis.py"
SPEC = importlib.util.spec_from_file_location("start_local_redis", SCRIPT_PATH)
start_local_redis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(start_local_redis)


class StartLocalRedisTests(unittest.TestCase):
    def test_default_data_dir_uses_runtime_directory(self) -> None:
        expected = start_local_redis.REPO_ROOT / ".hermes-proxy-runtime" / "redis"
        self.assertEqual(start_local_redis.DEFAULT_DATA_DIR, expected)

    def test_build_command_uses_repo_scoped_persistence(self) -> None:
        cmd = start_local_redis.build_command(
            redis_server_bin="/opt/homebrew/bin/redis-server",
            data_dir=Path("/tmp/hermes-runtime/redis"),
            port=6380,
            requirepass="secret",
            daemonize=True,
        )

        self.assertEqual(cmd[0], "/opt/homebrew/bin/redis-server")
        self.assertIn("--dir", cmd)
        self.assertIn("/tmp/hermes-runtime/redis", cmd)
        self.assertIn("--dbfilename", cmd)
        self.assertIn("dump.rdb", cmd)
        self.assertIn("--appendonly", cmd)
        self.assertIn("yes", cmd)
        self.assertIn("--port", cmd)
        self.assertIn("6380", cmd)
        self.assertIn("--requirepass", cmd)
        self.assertIn("secret", cmd)
        self.assertIn("--daemonize", cmd)

    def test_main_creates_data_dir_and_runs_redis(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "redis"
            args = mock.Mock(
                redis_server_bin="/opt/homebrew/bin/redis-server",
                data_dir=str(target_dir),
                port=6379,
                requirepass="",
                daemonize=False,
            )

            with mock.patch.object(start_local_redis, "parse_args", return_value=args), \
                 mock.patch.object(start_local_redis, "resolve_redis_server_bin", return_value="/opt/homebrew/bin/redis-server"), \
                 mock.patch.object(start_local_redis.subprocess, "run") as run_cmd:
                start_local_redis.main()
                self.assertTrue(target_dir.exists())
                run_cmd.assert_called_once()
                command = run_cmd.call_args.args[0]
                self.assertIn("--dir", command)
                self.assertIn(str(target_dir.resolve()), command)


if __name__ == "__main__":
    unittest.main()
