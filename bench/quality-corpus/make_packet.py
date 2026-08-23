#!/usr/bin/env python3
"""Create the method-blind rating packet for the quality panel."""
import json
import sys

from common import ContractError, load_manifest


def main():
    if len(sys.argv) != 2:
        print("usage: make_packet.py MANIFEST", file=sys.stderr)
        return 2
    try:
        manifest = load_manifest(sys.argv[1])
    except ContractError as exc:
        print(f"quality packet: {exc}", file=sys.stderr)
        return 2
    packet = {
        "schema": 1,
        "protocol_sha256": manifest["label_protocol_sha256"],
        "items": [{"id": row["id"], "text": row["text"]}
                  for row in manifest["items"]],
    }
    print(json.dumps(packet, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
