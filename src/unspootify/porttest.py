"""Is the Soulseek listen port reachable from the internet?

Opens the port locally (unless something, e.g. sockseek, already listens on it) and asks
Soulseek's own port checker to connect to it.
"""

from __future__ import annotations

import random
import re
import socket
import urllib.request
from contextlib import suppress
from typing import Any

CHECKER = "http://tools.slsknet.org/porttest.php?port={port}"
SERVER = ("server.slsknet.org", 2242)  # the Soulseek server every client logs in to
DEFAULT_PORT = 49998
_RESULT = re.compile(r"Port:\s*(\d+)/tcp\s+(OPEN|CLOSED)", re.I)


def parse(html: str, port: int) -> bool | None:
    for m in _RESULT.finditer(html):
        if int(m.group(1)) == port:
            return m.group(2).upper() == "OPEN"
    return None


def _listen(port: int) -> socket.socket | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen(5)
        return s
    except OSError:
        s.close()
        return None  # already in use (fine if sockseek is the one listening)


def suggest_port(rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    for _ in range(50):
        port = rng.randint(50000, 59999)
        s = _listen(port)
        if s:
            s.close()
            return port
    return 50000


def server_reachable(connect=socket.create_connection) -> bool:
    """Can we reach the Soulseek server at all? (Some networks block it outright.)"""
    try:
        connect(SERVER, timeout=8).close()
        return True
    except OSError:
        return False


def test_port(port: int | None, fetch=None, connect=socket.create_connection) -> dict[str, Any]:
    """{open, port, server, suggested_port?}. open=None means the checker couldn't answer."""
    port = port or DEFAULT_PORT
    if not 1024 <= port <= 65535:
        return {"open": False, "port": port, "error": "BAD_PORT"}
    server = server_reachable(connect)
    listener = _listen(port)
    try:
        if fetch is None:
            def fetch(url: str) -> str:
                req = urllib.request.Request(url, headers={"User-Agent": "unSpootify"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    return r.read().decode("utf-8", "replace")
        try:
            html = fetch(CHECKER.format(port=port))
        except OSError:
            return {"open": None, "port": port, "server": server, "error": "NO_NETWORK"}
        is_open = parse(html, port)
    finally:
        if listener:
            with suppress(OSError):
                listener.close()
    if is_open is None:
        return {"open": None, "port": port, "server": server, "error": "CHECKER_CHANGED"}
    result: dict[str, Any] = {"open": is_open, "port": port, "server": server}
    if not is_open:
        result["suggested_port"] = suggest_port()
    return result
