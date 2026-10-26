import json
import os
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

from locust import HttpUser, between, events, task

credentials = deque()
run_index = int(os.environ.get("LOAD_RUN_INDEX", "1"))


@events.test_start.add_listener
def prepare(environment, **kwargs):
    credentials.clear()
    credentials.extend(
        json.loads(Path(os.environ.get("LOAD_CREDENTIALS", "reports/load_users.json")).read_text())
    )


class SchedulingUser(HttpUser):
    wait_time = between(0.05, 0.2)

    def on_start(self):
        self.account = credentials.popleft()
        self.client.headers["Authorization"] = f"Bearer {self.account['token']}"
        self.counter = 0

    @task(4)
    def read_appointments(self):
        self.client.get("/appointments?limit=20", name="/appointments [read]")

    @task(1)
    def create_appointment(self):
        # Distinct slots by run, user and per-user counter, in one Locust worker.
        slot = self.account["index"] // 10 + self.counter * 10
        self.counter += 1
        base = datetime.fromisoformat(self.account["base"])
        start = base + timedelta(minutes=(10000 + run_index * 10000 + slot) * 30)
        with self.client.post(
            "/appointments",
            name="/appointments [write]",
            catch_response=True,
            json={
                "resource_id": self.account["resource_id"],
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(minutes=20)).isoformat(),
            },
        ) as response:
            if response.status_code != 201:
                response.failure(f"Unexpected status {response.status_code}")
