#!/usr/bin/env python3
"""Generate the checked-in OpenAPI contract without a web-framework dependency."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
point = {"type": "object", "required": ["lat", "lon"], "properties": {
    "lat": {"type": "number", "minimum": -90, "maximum": 90},
    "lon": {"type": "number", "minimum": -180, "maximum": 180}}}
place = {"type": "object", "required": ["id", "name", "lat", "lon", "kind", "source"], "properties": {
    "id": {"type": "string"}, "name": {"type": "string"}, "kind": {"type": "string"},
    "source": {"type": "string"}, **point["properties"]}}
position = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "[longitude, latitude]"}
error = {"type": "object", "required": ["error"], "properties": {"error": {"type": "object", "required": ["code", "message"],
    "properties": {"code": {"type": "string"}, "message": {"type": "string"}}}}}
snap = {"type": "object", "required": ["lat", "lon", "osm_id", "distance_m"], "properties": {
    **point["properties"], "osm_id": {"type": "integer", "format": "int64"}, "distance_m": {"type": "number", "minimum": 0}}}
route = {"type": "object", "required": ["geometry", "distance_m", "duration_s", "steps", "snapped", "algorithm", "mode", "cached", "visited_nodes", "search_ms", "data_version", "warnings"], "properties": {
    "geometry": {"type": "object", "required": ["type", "coordinates"], "properties": {
        "type": {"type": "string", "enum": ["LineString"]}, "coordinates": {"type": "array", "items": position, "minItems": 2}}},
    "distance_m": {"type": "number", "minimum": 0}, "duration_s": {"type": "number", "minimum": 0},
    "steps": {"type": "array", "items": {"type": "object", "required": ["maneuver", "instruction", "road", "distance_m", "duration_s", "coordinate"], "properties": {
        "maneuver": {"type": "string", "enum": ["depart", "continue", "left", "right", "uturn", "arrive"]},
        "instruction": {"type": "string"}, "road": {"type": "string"}, "distance_m": {"type": "number"}, "duration_s": {"type": "number"}, "coordinate": position}}},
    "snapped": {"type": "object", "properties": {"source": snap, "destination": snap}},
    "mode": {"type": "string", "enum": ["driving", "walking", "cycling"]},
    "algorithm": {"type": "string", "enum": ["astar", "dijkstra"]}, "cached": {"type": "boolean"},
    "visited_nodes": {"type": "integer"}, "search_ms": {"type": "number"}, "data_version": {"type": "string"},
    "warnings": {"type": "array", "items": {"type": "string"}}}}

def response(schema, description="Successful response"):
    return {"description": description, "content": {"application/json": {"schema": schema}}}


def operation(summary, schema, parameters=None, body=None):
    result = {"summary": summary, "responses": {"200": response(schema)}}
    for code, message in {400: "Malformed JSON or query", 403: "Origin denied", 404: "No route or endpoint not found", 413: "Body too large", 415: "Unsupported content type", 422: "Invalid values or outside coverage", 429: "Rate limited", 500: "Internal error"}.items():
        result["responses"][str(code)] = response({"$ref": "#/components/schemas/Error"}, message)
    result["responses"]["429"]["headers"] = {"Retry-After": {"schema": {"type": "integer"}, "description": "Seconds until another token is available"}}
    if parameters:
        result["parameters"] = parameters
    if body:
        result["requestBody"] = {"required": True, "content": {"application/json": {"schema": body, "example": {
            "source": {"lat": 28.609, "lon": 77.040}, "destination": {"lat": 28.602, "lon": 77.025}, "mode": "driving", "algorithm": "astar"}}}}
    return result


def query(name, schema, required=True):
    return {"name": name, "in": "query", "required": required, "schema": schema}


document = {"openapi": "3.0.3", "info": {"title": "Navic C++ Routing API", "version": "1.0.0",
    "description": "Shortest-distance routing within the Delhi pilot. Distances are meters, times seconds. Place search is a local OSM gazetteer. ETA has no live traffic. Data © OpenStreetMap contributors, ODbL."},
    "servers": [{"url": "/", "description": "This API server"}],
    "components": {"schemas": {"Point": point, "Place": place, "Error": error, "Route": route}}, "paths": {}}
paths = document["paths"]
paths["/health"] = {"get": operation("Graph readiness and counts", {"type": "object", "required": ["status", "nodes", "edges"], "properties": {
    "status": {"type": "string", "enum": ["ok"]}, "service": {"type": "string"}, "version": {"type": "string"}, "nodes": {"type": "integer"}, "edges": {"type": "integer"}, "places": {"type": "integer"}, "uptime_s": {"type": "number"}, "data_version": {"type": "string"}}})}
paths["/coverage"] = {"get": operation("Coverage and data provenance", {"type": "object", "required": ["bbox", "modes", "algorithms"], "properties": {
    "bbox": {"type": "array", "minItems": 4, "maxItems": 4, "items": {"type": "number"}, "description": "south, west, north, east"},
    "name": {"type": "string"}, "modes": {"type": "array", "items": {"type": "string"}}, "algorithms": {"type": "array", "items": {"type": "string"}}, "max_snap_m": {"type": "number"}}})}
paths["/geocode"] = {"get": operation("Search the bundled place index", {"type": "object", "properties": {"results": {"type": "array", "items": place}, "provider": {"type": "string"}}},
    [query("q", {"type": "string", "minLength": 2, "maxLength": 120, "example": "NSUT", "description": "Implementation checks UTF-8 byte length"}), query("limit", {"type": "integer", "minimum": 1, "maximum": 10, "default": 6}, False)])}
paths["/reverse-geocode"] = {"get": operation("Find the nearest named place (approximate)", {"type": "object", "properties": {
    "result": {**place, "nullable": True, "properties": {**place["properties"], "distance_m": {"type": "number"}}}, "approximate": {"type": "boolean"}, "provider": {"type": "string"}}},
    [query("lat", {"type": "number", "example": 28.609}), query("lon", {"type": "number", "example": 77.040})])}
paths["/route"] = {"post": operation("Compute a shortest-distance route", {"$ref": "#/components/schemas/Route"}, body={"type": "object", "required": ["source", "destination"], "properties": {
    "source": {"$ref": "#/components/schemas/Point"}, "destination": {"$ref": "#/components/schemas/Point"},
    "mode": {"type": "string", "enum": ["driving", "walking", "cycling"], "default": "driving"}, "algorithm": {"type": "string", "enum": ["dijkstra", "astar"], "default": "astar"}}})}
paths["/network"] = {"get": {"summary": "Road geometry for the offline map backdrop", "responses": {"200": {"description": "GeoJSON FeatureCollection", "content": {"application/geo+json": {"schema": {"type": "object", "properties": {"type": {"type": "string", "enum": ["FeatureCollection"]}, "features": {"type": "array", "items": {"type": "object"}}}}}}}}}}
paths["/openapi.json"] = {"get": {"summary": "This machine-readable API contract", "responses": {"200": response({"type": "object"})}}}
paths["/docs"] = {"get": {"summary": "Interactive Swagger UI", "responses": {"200": {"description": "HTML documentation", "content": {"text/html": {"schema": {"type": "string"}}}}}}}
(ROOT / "docs/openapi.json").write_text(json.dumps(document, indent=2) + "\n")
