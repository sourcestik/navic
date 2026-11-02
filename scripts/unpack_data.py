#!/usr/bin/env python3
"""Verify and unpack the bundled graph without contacting any external server."""
import gzip
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
metadata = json.loads((root / "data/metadata.json").read_text())
payload = gzip.decompress((root / "data/graph.ndjson.gz").read_bytes())
if hashlib.sha256(payload).hexdigest() != metadata["sha256"]:
    raise SystemExit("Graph checksum mismatch. Obtain an intact data bundle.")
(root / "data/graph.ndjson").write_bytes(payload)
print(f'Graph verified and unpacked: {metadata["nodes"]} nodes, {metadata["edges"]} edges')
