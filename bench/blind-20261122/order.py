#!/usr/bin/env python3
"""Validate frozen, metadata-only orders that separate paired variants."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys


def validate(metadata, grouping, scope, input_ids):
    if metadata.get('seed')!=20261122 or metadata.get('batch_size')!=4:
        raise ValueError('Unexpected frozen seed or batch size')
    ids=metadata[scope]['draft_ids'];groups=grouping['source_group_by_id']
    if hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()!=metadata[scope]['order_sha256']:raise ValueError('Frozen order hash mismatch')
    if len(set(input_ids))!=len(input_ids) or set(input_ids)!=set(ids):
        raise ValueError('Input ids differ from the frozen population')
    if any(item not in groups for item in ids):raise ValueError('Missing source-group metadata')
    blocks=[ids[offset:offset+4] for offset in range(0,len(ids),4)]
    if any(len(block)!=4 or len({groups[item] for item in block})!=4 for block in blocks):
        raise ValueError('Paired variants share a model batch')
    if metadata[scope]['batches']!=blocks:raise ValueError('Frozen blocks disagree with order')
    original=[item for item in grouping['original_draft_order'] if item in set(ids)]
    if len(original)!=len(ids):raise ValueError('Original ordering omits frozen ids')
    rng=random.Random(metadata['seed'])
    for attempt in range(1,100001):
        candidate=list(original);rng.shuffle(candidate)
        if all(len({groups[item] for item in candidate[offset:offset+4]})==4 for offset in range(0,len(candidate),4)):
            if candidate!=ids or attempt!=metadata[scope]['shuffle_attempts']:
                raise ValueError('Order does not match the frozen first-valid seeded permutation')
            break
    else:raise ValueError('Could not validate seeded order')
    return ids


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--groups',type=Path,required=True)
    p.add_argument('--scope',choices=['primary','panel'],required=True)
    args=p.parse_args()
    ids=validate(json.loads(args.metadata.read_text()),json.loads(args.groups.read_text()),args.scope,json.load(sys.stdin))
    print(json.dumps(ids))

if __name__=='__main__':main()
