#!/usr/bin/env python3
"""Convert a cached Overpass extract to a small, auditable C++ routing graph.

Only Python's standard library is needed. Network access is an explicit --download
operation; rebuilding from data/raw/osm.json is deterministic and works offline.
"""
import argparse
import datetime as dt
import hashlib
import gzip
import json
import math
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BBOX = (28.50, 76.98, 28.70, 77.25)  # south, west, north, east
ROAD_SPEEDS = {"motorway": 70, "trunk": 50, "primary": 40, "secondary": 35,
               "tertiary": 30, "residential": 25, "living_street": 10,
               "service": 15, "unclassified": 25}
DRIVE = set(ROAD_SPEEDS) | {"motorway_link", "trunk_link", "primary_link",
                                "secondary_link", "tertiary_link"}
WALK = (DRIVE - {"motorway", "motorway_link", "trunk", "trunk_link"}) | {
    "footway", "pedestrian", "path", "steps", "track", "cycleway"}
CYCLE = (WALK - {"steps", "footway"}) | {"cycleway"}
DENIED = {"no", "private", "agricultural", "forestry", "customers", "delivery", "destination"}
ALLOWED = {"yes", "designated", "permissive", "official"}


def haversine(a, b):
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat, dlon = lat2 - lat1, math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def permissions(tags):
    """Apply specific mode permissions after general access, then direction rules.

    This intentionally conservative profile is not a complete OSM rules engine.
    Conditional restrictions, barriers and turn-restriction relations are excluded.
    """
    highway = tags.get("highway", "")
    if highway not in DRIVE | WALK | CYCLE or tags.get("area") == "yes":
        return (0, 0)
    flags = [highway in DRIVE, highway in WALK, highway in CYCLE]
    hierarchy = [("access", "vehicle", "motor_vehicle", "motorcar"),
                 ("access", "foot"), ("access", "vehicle", "bicycle")]
    for i, keys in enumerate(hierarchy):
        for key in keys:
            value = tags.get(key, "").lower()
            if value in DENIED:
                flags[i] = False
            elif value in ALLOWED:
                flags[i] = True
    mask = sum((1 << i) for i, permitted in enumerate(flags) if permitted)
    forward, reverse = mask, mask
    one = tags.get("oneway", "yes" if tags.get("junction") == "roundabout" or
                   highway in {"motorway", "motorway_link"} else "no")
    if one in {"yes", "1", "true"}:
        reverse &= ~5  # walking is not bound by normal vehicle one-way tags
    elif one == "-1":
        forward &= ~5
    if tags.get("oneway:bicycle") in {"no", "0", "false"} and flags[2]:
        forward |= 4
        reverse |= 4
    elif tags.get("oneway:bicycle") in {"yes", "1", "true"}:
        reverse &= ~4
    elif tags.get("oneway:bicycle") == "-1":
        forward &= ~4
    if tags.get("oneway:foot") in {"yes", "1", "true"}:
        reverse &= ~2
    elif tags.get("oneway:foot") == "-1":
        forward &= ~2
    return forward, reverse


def speeds(tags):
    base = tags.get("highway", "residential").replace("_link", "")
    driving = ROAD_SPEEDS.get(base, 20)
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(mph|km/h|kph)?\s*", tags.get("maxspeed", ""))
    if match:
        limit = float(match[1]) * (1.609344 if match[2] == "mph" else 1)
        if limit > 0:
            driving = min(driving, limit)
    return max(1, driving), 3 if base == "steps" else 4.8, 10 if base in {"path", "track"} else 15


def make_query(bbox):
    box = ",".join(map(str, bbox))
    return (f'[out:json][timeout:180];(way["highway"]({box});'
            f'node["name"]["amenity"]({box});node["name"]["railway"]({box});'
            f'node["name"]["place"]({box});node["name"]["shop"]({box});'
            f'way["name"]["amenity"]({box});way["name"]["leisure"]({box});'
            f'way["name"]["shop"]({box});nwr["name"]["tourism"]({box});'
            f'rel["name"]["amenity"]({box});rel["name"]["shop"]({box}););'
            'out body center;>;out skel qt;')


def build(raw, bbox, target):
    s, w, n, e = bbox
    inside = lambda p: s <= p[0] <= n and w <= p[1] <= e
    elements = {}
    for item in raw["elements"]:
        key = (item["type"], item["id"])
        # Recursive output can repeat nodes without tags. Keep the richer record.
        if key not in elements or "tags" in item:
            elements[key] = item
    coords = {item["id"]: (item["lat"], item["lon"]) for item in elements.values()
              if item["type"] == "node" and inside((item["lat"], item["lon"]))}
    nodes, edges, names, indices, name_ids = [], [], [], {}, {}
    features, places, seen_places = [], [], set()

    def node_index(osm_id):
        if osm_id not in indices:
            indices[osm_id] = len(nodes)
            nodes.append([osm_id, *coords[osm_id]])
        return indices[osm_id]

    def add_place(item, pos, kind):
        tags = item.get("tags", {})
        name = tags.get("name:en", tags.get("name", ""))
        if not name or not inside(pos):
            return
        key = (name.lower(), round(pos[0], 3), round(pos[1], 3))
        if key in seen_places:
            return
        seen_places.add(key)
        aliases = [tags[k] for k in ("name", "short_name", "alt_name", "official_name", "name:hi") if k in tags]
        if "netaji subhas" in name.lower() and ("university" in name.lower() or "institute" in name.lower()):
            aliases += ["NSUT", "NSIT"]
        places.append({"id": f'{item["type"]}/{item["id"]}', "name": name,
                       "lat": pos[0], "lon": pos[1], "kind": kind,
                       "aliases": " ".join(aliases), "source": "OpenStreetMap"})

    for item in sorted(elements.values(), key=lambda it: (it["type"], it["id"])):
        tags = item.get("tags", {})
        if item["type"] == "relation" and "center" in item:
            add_place(item, (item["center"]["lat"], item["center"]["lon"]), tags.get("amenity", tags.get("shop", tags.get("tourism", "place"))))
        elif item["type"] == "node" and item["id"] in coords:
            add_place(item, coords[item["id"]], tags.get("amenity", tags.get("railway", tags.get("place", tags.get("shop", tags.get("tourism", "place"))))))
        elif item["type"] == "way":
            points = [coords[i] for i in item["nodes"] if i in coords]
            if points:
                center = item.get("center")
                pos = (center["lat"], center["lon"]) if center else points[len(points) // 2]
                add_place(item, pos, tags.get("amenity", tags.get("leisure", tags.get("shop", tags.get("tourism", "road")))))
            forward, reverse = permissions(tags)
            if not (forward or reverse):
                continue
            name = tags.get("name:en", tags.get("name", tags.get("ref", "Unnamed road")))
            if name not in name_ids:
                name_ids[name] = len(names)
                names.append(name)
            speed = speeds(tags)
            line = []
            for a, b in zip(item["nodes"], item["nodes"][1:]):
                if a not in coords or b not in coords or a == b:
                    if len(line) > 1:
                        features.append({"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": line}})
                    line = []
                    continue
                length = haversine(coords[a], coords[b])
                if length < 0.001:
                    continue
                ai, bi = node_index(a), node_index(b)
                times = [length / (kph / 3.6) for kph in speed]
                if forward:
                    edges.append([ai, bi, length, *times, name_ids[name], forward])
                if reverse:
                    edges.append([bi, ai, length, *times, name_ids[name], reverse])
                if not line:
                    line.append([coords[a][1], coords[a][0]])
                line.append([coords[b][1], coords[b][0]])
            if len(line) > 1:
                features.append({"type": "Feature", "properties": {}, "geometry": {"type": "LineString", "coordinates": line}})
    if len(nodes) < 100 or not edges:
        raise ValueError("Extract is too small or empty; refusing to overwrite the real graph")
    timestamp = raw.get("osm3s", {}).get("timestamp_osm_base", "unknown")
    metadata = {"schema_version": 1, "name": "Delhi · Dwarka to Central Delhi pilot",
                "bbox": list(bbox), "osm_timestamp": timestamp, "data_version": timestamp,
                "attribution": "© OpenStreetMap contributors", "license": "ODbL-1.0",
                "source_url": "https://www.openstreetmap.org/copyright",
                "nodes": len(nodes), "edges": len(edges), "places": len(places),
                "objective": "shortest_distance", "turn_restrictions": False}
    target.mkdir(parents=True, exist_ok=True)
    # One header, then N node records, then E edge records. Streaming this file in
    # C++ avoids a huge temporary JSON document while the graph is resident.
    graph_path = target / "graph.ndjson"
    header = {"metadata": metadata, "names": names, "places": places}
    with graph_path.open("w", encoding="utf-8") as stream:
        for record in [header]:
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        for rows in (nodes, edges):
            for record in rows:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    payload = graph_path.read_bytes()
    (target / "graph.ndjson.gz").write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    (target / "network.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))
    metadata["sha256"] = hashlib.sha256(payload).hexdigest()
    (target / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    print(f"Graph size: {len(payload) / 1048576:.2f} MiB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX, metavar=("S", "W", "N", "E"))
    parser.add_argument("--input", type=Path, default=ROOT / "data/raw/osm.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data")
    parser.add_argument("--endpoint", default="https://overpass-api.de/api/interpreter")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--query-only", action="store_true")
    args = parser.parse_args()
    s, w, n, e = args.bbox
    if not (-90 <= s < n <= 90 and -180 <= w < e <= 180):
        parser.error("bbox must be south west north east in valid WGS84 ranges")
    query = make_query(args.bbox)
    args.input.parent.mkdir(parents=True, exist_ok=True)
    (args.input.parent / "query.overpass").write_text(query)
    if args.query_only:
        return
    if args.download:
        request = urllib.request.Request(args.endpoint,
            data=urllib.parse.urlencode({"data": query}).encode(),
            headers={"User-Agent": "Navic-MinorProject/1.0 (academic OSM graph preparation)"})
        with urllib.request.urlopen(request, timeout=240) as response:
            content = response.read()
        parsed = json.loads(content)
        if "remark" in parsed:
            raise RuntimeError(f'Overpass did not complete: {parsed["remark"]}')
        args.input.write_bytes(content)
    raw = json.loads(args.input.read_text())
    if "remark" in raw:
        raise RuntimeError(f'Overpass extract incomplete: {raw["remark"]}')
    build(raw, args.bbox, args.output)


if __name__ == "__main__":
    main()
