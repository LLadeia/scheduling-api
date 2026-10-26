"""Single-worker load experiment, 9 independent runs; requires running API and seed."""

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


def run(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    environment = {
        "timestamp": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "host": args.host,
        "cpu_count": os.cpu_count(),
        "warmup_seconds": 30,
        "measurement_seconds": 180,
        "notes": args.environment_notes,
    }
    (output / "environment.json").write_text(json.dumps(environment, indent=2))
    results = []
    for index, (users, repetition) in enumerate(
        ((users, repetition) for users in (1, 10, 25) for repetition in (1, 2, 3)), 1
    ):
        refresh = subprocess.run(
            [sys.executable, "-m", "scripts.seed_load", "--refresh", "--output", args.credentials]
        )
        if refresh.returncode:
            raise SystemExit(refresh.returncode)
        prefix = output / f"u{users}-r{repetition}"
        web_port = 8090
        env = {**os.environ, "LOAD_CREDENTIALS": args.credentials, "LOAD_RUN_INDEX": str(index)}
        # Start via UI API so stats can be reset precisely after warmup.
        cmd = [
            sys.executable,
            "-m",
            "locust",
            "-f",
            "scripts/locustfile.py",
            "--host",
            args.host,
            "--web-host",
            "127.0.0.1",
            "--web-port",
            str(web_port),
            "--csv",
            str(prefix),
            "--csv-full-history",
        ]
        with (output / f"u{users}-r{repetition}.log").open("w") as log:
            process = subprocess.Popen(cmd, env=env, stdout=log, stderr=log)
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Locust encerrou; confira log")
                    try:
                        urlopen(f"http://127.0.0.1:{web_port}/", timeout=2).close()
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Locust não iniciou")
                form = f"user_count={users}&spawn_rate={users}&host={args.host}".encode()
                with urlopen(
                    Request(f"http://127.0.0.1:{web_port}/swarm", data=form), timeout=5
                ) as response:
                    if not json.load(response)["success"]:
                        raise RuntimeError("Falha iniciando carga")
                time.sleep(30)
                urlopen(f"http://127.0.0.1:{web_port}/stats/reset", timeout=5).close()
                time.sleep(180)
                urlopen(f"http://127.0.0.1:{web_port}/stop", timeout=5).close()
                with urlopen(f"http://127.0.0.1:{web_port}/stats/requests", timeout=5) as response:
                    stats = json.load(response)
                (output / f"u{users}-r{repetition}-final.json").write_text(
                    json.dumps(stats, indent=2)
                )
                for row in stats["stats"]:
                    if row["name"] in ("/appointments [read]", "Aggregated"):
                        results.append(
                            {
                                "users": users,
                                "repetition": repetition,
                                "endpoint": row["name"],
                                "p50_ms": row["median_response_time"],
                                "p95_ms": row["response_time_percentile_0.95"],
                                "requests": row["num_requests"],
                                "rps": row["total_rps"],
                                "unexpected_errors": row["num_failures"],
                            }
                        )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        print(f"Concluído: {users} usuários, repetição {repetition}", flush=True)
    with (output / "summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    if any(row["unexpected_errors"] for row in results):
        raise SystemExit("Ensaio registrou erros inesperados; veja summary.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--credentials", default="reports/load_users.json")
    parser.add_argument("--output", default="reports/load")
    parser.add_argument(
        "--environment-notes",
        required=True,
        help="CPU, RAM, Docker/host, versões, rede e configuração do banco",
    )
    run(parser.parse_args())
