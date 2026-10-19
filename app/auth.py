"""Inloggen: bescherming tegen raden, veilige doorverwijzing en een veilig sessiecookie achter HTTPS."""
import threading
import time
from collections import deque


class LoginGuard:
    """Remt het raden van het wachtwoord af.

    Per IP-adres: na 5 foute pogingen binnen 15 minuten volgt een blokkade van 15 minuten.
    Daarnaast een grens voor alle pogingen samen (30 per 15 minuten), omdat een aanvaller
    achter een proxy zijn IP-adres kan vervalsen. Een geslaagde login wist de teller van dat adres.
    """
    MAX_PER_IP = 5
    MAX_TOTAL = 30
    WINDOW = 15 * 60
    LOCK = 15 * 60

    def __init__(self):
        self._lock = threading.Lock()
        self._ips = {}           # ip -> {"count", "first", "until"}
        self._all = deque()      # tijdstippen van foute pogingen

    def wait_time(self, ip: str) -> int:
        """Aantal seconden dat dit adres nog moet wachten (0 = mag proberen)."""
        now = time.monotonic()
        with self._lock:
            while self._all and now - self._all[0] > self.WINDOW:
                self._all.popleft()
            waits = []
            if len(self._all) >= self.MAX_TOTAL:
                waits.append(self.WINDOW - (now - self._all[0]))
            entry = self._ips.get(ip)
            if entry and entry["until"] > now:
                waits.append(entry["until"] - now)
            return int(max(waits)) + 1 if waits else 0

    def failed(self, ip: str):
        now = time.monotonic()
        with self._lock:
            self._all.append(now)
            entry = self._ips.get(ip)
            if not entry or now - entry["first"] > self.WINDOW:
                entry = {"count": 0, "first": now, "until": 0.0}
            entry["count"] += 1
            if entry["count"] >= self.MAX_PER_IP:
                entry.update(count=0, first=now, until=now + self.LOCK)
            self._ips[ip] = entry
            if len(self._ips) > 10_000:   # geheugen begrenzen
                for key in [k for k, e in self._ips.items() if e["until"] < now and now - e["first"] > self.WINDOW]:
                    del self._ips[key]

    def succeeded(self, ip: str):
        with self._lock:
            self._ips.pop(ip, None)


def safe_next(value: str) -> str:
    """Alleen doorverwijzen naar een pad op Linker zelf, nooit naar een andere site."""
    value = (value or "").strip()
    if (not value.startswith("/") or value.startswith("//") or "\\" in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or value.startswith(("/login", "/logout"))):
        return "/"
    return value[:2000]


class SecureCookieOnHttps:
    """Zet de vlag Secure op het sessiecookie als de pagina via HTTPS binnenkomt
    (ook achter een reverse proxy, via X-Forwarded-Proto). Via http in je thuisnetwerk blijft inloggen werken."""

    def __init__(self, app, cookie_name: str):
        self.app = app
        self.prefix = cookie_name.encode() + b"="

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("scheme") != "https":
            return await self.app(scope, receive, send)

        async def send_secure(message):
            if message["type"] == "http.response.start":
                headers = []
                for key, value in message.get("headers", []):
                    if key.lower() == b"set-cookie" and value.startswith(self.prefix):
                        attrs = [a.strip().lower() for a in value.split(b";")[1:]]
                        if b"secure" not in attrs:
                            value += b"; Secure"
                    headers.append((key, value))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_secure)
