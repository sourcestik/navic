import copy
import json
import math
import urllib.request
import pytest
from conftest import call


def test_health_and_coverage(api):
    status, health, _ = call(api, "/health")
    assert status == 200 and health["status"] == "ok"
    assert health["nodes"] > 100000 and health["edges"] > health["nodes"]
    _, coverage, _ = call(api, "/coverage")
    assert coverage["bbox"] == [-90,-180,90,180]
    assert coverage["local_bbox"] == [28.5, 76.98, 28.7, 77.25]
    assert coverage["turn_restrictions"] is False


@pytest.mark.parametrize("mode", ["driving", "walking", "cycling"])
def test_real_routes_and_algorithm_agreement(api, journey, mode):
    answers = []
    for algorithm in ("dijkstra", "astar"):
        status, result, _ = call(api, "/route", {**journey, "mode": mode, "algorithm": algorithm})
        assert status == 200, result
        assert result["distance_m"] > 0 and result["duration_s"] > 0
        assert result["geometry"]["type"] == "LineString"
        coords = result["geometry"]["coordinates"]
        assert len(coords) >= 2 and 76 < coords[0][0] < 78 and 28 < coords[0][1] < 29
        assert coords[0] == [result["snapped"]["source"]["lon"], result["snapped"]["source"]["lat"]]
        assert result["steps"][-1]["maneuver"] == "arrive"
        assert sum(step["distance_m"] for step in result["steps"]) == pytest.approx(result["distance_m"])
        assert sum(step["duration_s"] for step in result["steps"]) == pytest.approx(result["duration_s"])
        answers.append(result)
    assert answers[0]["distance_m"] == pytest.approx(answers[1]["distance_m"], abs=1e-6)


def test_same_point(api, journey):
    status, result, _ = call(api, "/route", {"source": journey["source"], "destination": journey["source"]})
    assert status == 200
    assert result["distance_m"] == 0 and result["duration_s"] == 0
    assert len(result["geometry"]["coordinates"]) == 2


def test_cached_route(api, journey):
    call(api, "/route", journey)
    status, result, _ = call(api, "/route", journey)
    assert status == 200 and result["cached"] is True
    assert result["visited_nodes"] == 0 and result["search_ms"] == 0


@pytest.mark.parametrize("field,value,expected", [
    ("mode", "flying", "INVALID_MODE"), ("algorithm", "bfs", "INVALID_ALGORITHM"),
    ("algorithm", 12, "INVALID_FIELD"), ("mode", None, "INVALID_FIELD")])
def test_bad_enums(api, journey, field, value, expected):
    status, result, _ = call(api, "/route", {**journey, field: value})
    assert status == 422 and result["error"]["code"] == expected


@pytest.mark.parametrize("source,code", [
    ({"lat": 200, "lon": 77}, "INVALID_COORDINATE"),
    ({"lat": "28.6", "lon": 77}, "INVALID_COORDINATE"),
    ({"lat": True, "lon": 77}, "INVALID_COORDINATE"),
    ({"lat": None, "lon": 77}, "INVALID_COORDINATE"),
    ({"lat": 28.6}, "INVALID_COORDINATE"),
    ({"lat": 19, "lon": 181}, "INVALID_COORDINATE")])
def test_bad_coordinates(api, journey, source, code):
    status, result, _ = call(api, "/route", {**journey, "source": source})
    assert status == 422 and result["error"]["code"] == code


@pytest.mark.parametrize("body", [{}, [], {"source": {}}])
def test_missing_endpoints(api, body):
    assert call(api, "/route", body)[0] == 422


def test_malformed_json(api):
    assert call(api, "/route", raw=b"{not json", headers={"Content-Type": "application/json"})[0] == 400


def test_content_type_and_size(api, journey):
    assert call(api, "/route", journey, headers={"Content-Type": "text/plain"})[0] == 415
    assert call(api, "/route", raw=b"x" * 17000, headers={"Content-Type": "application/json"})[0] == 413


def test_search_and_reverse(api, journey):
    status, result, _ = call(api, "/geocode?scope=local&q=NSUT")
    assert status == 200 and any("Netaji" in place["name"] for place in result["results"])
    assert call(api, "/geocode?scope=local&q=zxyqvbnnoresults")[1]["results"] == []
    p = journey["source"]
    status, result, _ = call(api, f'/reverse-geocode?lat={p["lat"]}&lon={p["lon"]}')
    assert status == 200 and result["approximate"] is True and result["result"]["distance_m"] < 1


@pytest.mark.parametrize("query", ["/geocode", "/geocode?q=a", "/geocode?scope=local&q=NSUT&limit=0", "/geocode?scope=local&q=NSUT&limit=2.5", "/reverse-geocode?lat=nan&lon=77", "/reverse-geocode?lat=28.6x&lon=77"])
def test_bad_queries(api, query):
    assert call(api, query)[0] == 400


def test_cors(api, journey):
    status, _, headers = call(api, "/route", journey, headers={"Content-Type": "application/json", "Origin": "https://navic.example"})
    assert status == 200 and headers["Access-Control-Allow-Origin"] == "https://navic.example"
    status, _, headers = call(api, "/health", headers={"Origin": "http://localhost:5173"})
    assert status == 200 and headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    status, _, headers = call(api, "/route", journey, headers={"Content-Type": "application/json", "Origin": "https://untrusted.invalid"})
    assert status == 403 and headers.get("Access-Control-Allow-Origin") is None
    request = urllib.request.Request(api + "/route", method="OPTIONS", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    with urllib.request.urlopen(request) as response:
        assert response.status == 204 and "POST" in response.headers["Access-Control-Allow-Methods"]


def test_rate_limit_and_untrusted_forwarded_headers(api_factory):
    base = api_factory(rate=2)
    assert call(base, "/geocode?scope=local&q=NSUT")[0] == 200
    assert call(base, "/geocode?scope=local&q=NSUT")[0] == 200
    status, result, headers = call(base, "/geocode?scope=local&q=NSUT", headers={"X-Forwarded-For": "1.2.3.4"})
    assert status == 429 and result["error"]["code"] == "RATE_LIMITED"
    assert int(headers["Retry-After"]) > 0
    assert call(base, "/health")[0] == 200


def test_documentation_and_not_found(api):
    status, document, _ = call(api, "/openapi.json")
    assert status == 200 and document["openapi"] == "3.0.3"
    assert "/route" in document["paths"]
    assert "SwaggerUIBundle" in call(api, "/docs")[1]
    assert call(api, "/missing-endpoint")[0] == 404


def test_unreachable_and_excessive_snapping(api_factory, tmp_path):
    # Synthetic fixture is deliberately separate from the shipped real map.
    header = {"metadata": {"schema_version": 1, "bbox": [28.5, 76.98, 28.7, 77.25],
        "nodes": 4, "edges": 4, "data_version": "synthetic-test-only"}, "names": ["Fixture road"], "places": []}
    records = [header, [1, 28.6, 77.0], [2, 28.601, 77.001], [3, 28.65, 77.2], [4, 28.651, 77.201],
        [0, 1, 200, 20, 120, 50, 0, 7], [1, 0, 200, 20, 120, 50, 0, 7],
        [2, 3, 200, 20, 120, 50, 0, 7], [3, 2, 200, 20, 120, 50, 0, 7]]
    graph = tmp_path / "fixture.ndjson"
    graph.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    base = api_factory(graph_path=graph)
    body = {"source": {"lat": 28.6, "lon": 77.0}, "destination": {"lat": 28.65, "lon": 77.2}}
    status, result, _ = call(base, "/route", body)
    assert status == 404 and result["error"]["code"] == "NO_ROUTE"
    body["destination"] = {"lat": 28.69, "lon": 77.24}
    status, result, _ = call(base, "/route", body)
    assert status == 422 and result["error"]["code"] == "SNAP_TOO_FAR"
