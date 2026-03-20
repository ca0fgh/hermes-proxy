#!/usr/bin/env python3

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / ".hermes-proxy-runtime" / "redis"
REDIS_EXTRA_PATHS = [
    "/Users/money/.local/bin/redis-server",
    "/opt/homebrew/bin/redis-server",
    "/usr/local/bin/redis-server",
]


def find_redis_server_bin(override: str) -> str:
    candidates: list[str] = []
    if override:
        candidates.append(override)
    env_override = os.environ.get("REDIS_SERVER_BIN")
    if env_override:
        candidates.append(env_override)
    discovered = shutil.which("redis-server")
    if discovered:
        candidates.append(discovered)
    candidates.extend(REDIS_EXTRA_PATHS)

    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return ""


def resolve_redis_server_bin(override: str) -> str:
    redis_server_bin = find_redis_server_bin(override)
    if redis_server_bin:
        return redis_server_bin
    checked = ", ".join(["PATH", *REDIS_EXTRA_PATHS])
    print(
        "ERROR: cannot find `redis-server`. "
        "Install Redis 7+ or set `REDIS_SERVER_BIN` / `--redis-server-bin`. "
        f"Checked {checked}",
        file=sys.stderr,
    )
    raise SystemExit(1)


def build_command(
    redis_server_bin: str,
    data_dir: Path,
    port: int,
    requirepass: str,
    daemonize: bool,
) -> list[str]:
    command = [
        redis_server_bin,
        "--dir",
        str(data_dir),
        "--dbfilename",
        "dump.rdb",
        "--appendonly",
        "yes",
        "--appenddirname",
        "appendonlydir",
        "--appendfsync",
        "everysec",
        "--save",
        "60",
        "1",
        "--port",
        str(port),
    ]
    if requirepass:
        command.extend(["--requirepass", requirepass])
    if daemonize:
        command.extend(["--daemonize", "yes"])
    return command


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start a local Redis server with project-scoped persistence under .hermes-proxy-runtime/redis.",
    )
    parser.add_argument("--redis-server-bin", help="path to the redis-server executable")
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="directory for dump.rdb and appendonly files",
    )
    parser.add_argument("--port", type=int, default=6379, help="Redis port (default: 6379)")
    parser.add_argument("--requirepass", default="", help="optional Redis password")
    parser.add_argument(
        "--daemonize",
        action="store_true",
        help="run Redis in the background by passing --daemonize yes",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    redis_server_bin = resolve_redis_server_bin(args.redis_server_bin)
    data_dir = Path(args.data_dir).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    command = build_command(
        redis_server_bin=redis_server_bin,
        data_dir=data_dir,
        port=args.port,
        requirepass=args.requirepass,
        daemonize=args.daemonize,
    )
    print(f"[redis] data dir: {data_dir}")
    print(f"[redis] run: {' '.join(command)}")
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
