"""Start an isolated real C++ HTTP process for integration tests."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request
import pytest

ROOT = Path(__file__).resolve().parents[1]


def call(base, path, data=None, headers=None, raw=None):
    body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(base + path, data=body, headers=headers or ({"Content-Type": "application/json"} if body is not None else {}))
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        payload = response.read()
        result = json.loads(payload) if "json" in response.headers.get("Content-Type", "") else payload.decode()
        return response.status, result, response.headers


@pytest.fixture(scope="session")
def api_factory():
    processes = []
    logs = []

    def start(rate=10000, graph_path=None):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        environment = {**os.environ, "PORT": str(port), "HOST": "127.0.0.1", "RATE_LIMIT_PER_MINUTE": str(rate),
            "ALLOWED_ORIGINS": "http://localhost:5173"}
        if graph_path is not None:
            environment["GRAPH_PATH"] = str(graph_path)
        log = (ROOT / "artifacts" / f"test-server-{port}.log").open("w")
        logs.append(log)
        process = subprocess.Popen([str(ROOT / "build/navic-api")], cwd=ROOT, env=environment, stdout=log, stderr=log)
        processes.append(process)
        base = f"http://127.0.0.1:{port}"
        for _ in range(200):
            if process.poll() is not None:
                pytest.fail(f"Test API exited; inspect artifacts/test-server-{port}.log")
            try:
                if call(base, "/health")[0] == 200:
                    return base
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(.1)
        pytest.fail("Test API failed to become ready within 20 seconds")

    yield start
    for process in processes:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for log in logs:
        log.close()


@pytest.fixture(scope="session")
def api(api_factory):
    return api_factory()


@pytest.fixture(scope="session")
def journey(api):
    first = call(api, "/geocode?q=NSUT")[1]["results"][0]
    second = call(api, "/geocode?q=Vegas")[1]["results"][0]
    return {"source": {k: first[k] for k in ("lat", "lon")}, "destination": {k: second[k] for k in ("lat", "lon")}}
