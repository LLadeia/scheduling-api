from collections import OrderedDict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException


class LoginLimiter:
    """Fixed rolling window by socket IP; bounded, process-local storage."""

    def __init__(self, limit: int, window: int):
        self.limit, self.window = limit, window
        self.attempts: OrderedDict[str, deque[float]] = OrderedDict()
        self.lock = Lock()

    def check(self, ip: str) -> None:
        now = monotonic()
        with self.lock:
            # Entries ordered by last access; remove only expired keys.
            while self.attempts:
                key, values = next(iter(self.attempts.items()))
                if values and values[-1] > now - self.window:
                    break
                self.attempts.pop(key)
            if ip not in self.attempts and len(self.attempts) >= 10000:
                raise HTTPException(
                    429, "Limite de tentativas excedido", headers={"Retry-After": str(self.window)}
                )
            attempts = self.attempts.setdefault(ip, deque())
            self.attempts.move_to_end(ip)
            while attempts and attempts[0] <= now - self.window:
                attempts.popleft()
            if len(attempts) >= self.limit:
                raise HTTPException(
                    429,
                    "Limite de tentativas excedido",
                    headers={
                        "Retry-After": str(max(1, int(self.window - (now - attempts[0])) + 1))
                    },
                )
            attempts.append(now)
