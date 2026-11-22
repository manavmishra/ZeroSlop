#!/usr/bin/env python3
"""Run a fixed small portable-skill panel with balanced block/arm scheduling."""
import argparse
import concurrent.futures
import json
from pathlib import Path
import random
import subprocess
import run as matched
import order as frozen_order


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,required=True)
    p.add_argument('--arms',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--order',type=Path,required=True)
    p.add_argument('--groups',type=Path,required=True)
    p.add_argument('--suite',type=Path,required=True)
    p.add_argument('--seed',type=int,default=20261122)
    p.add_argument('--model',default=matched.MODEL)
    p.add_argument('--reasoning',default='high')
    p.add_argument('--timeout',type=int,default=600)
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--codex',default=matched.CODEX)
    args=p.parse_args();args.batch_size=4
    if not 1<=args.workers<=2:p.error('At most two concurrent CLI calls')
    suite=args.suite.resolve()
    if suite.exists():p.error('Choose a new output directory')
    suite.mkdir(parents=True)
    source=json.loads(args.corpus.read_text());source=source['drafts'] if isinstance(source,dict) else source
    if len(source)!=12:p.error('The frozen small panel requires exactly12 drafts')
    selection=json.loads(args.selection.read_text())
    if {row['id'] for row in source}!=set(selection['draft_ids']):p.error('Input does not match frozen panel selection set')
    if args.seed!=selection['seed']:p.error('Seed differs from frozen panel metadata')
    order_metadata=json.loads(args.order.read_text());groups=json.loads(args.groups.read_text())
    try:ids=frozen_order.validate(order_metadata,groups,'panel',[row['id'] for row in source])
    except ValueError as error:p.error(str(error))
    if all('source_group' in row for row in source) and any(row['source_group']!=groups['source_group_by_id'][row['id']] for row in source):p.error('Source groups differ from owner metadata')
    lookup={row['id']:row for row in source};source=[lookup[id] for id in ids]
    corpus=[{key:row[key] for key in matched.FIELDS if key in row} for row in source]
    arms=json.loads(args.arms.read_text())
    if len(arms)!=4:p.error('The frozen small panel requires exactly4 arms')
    rng=random.Random(args.seed);jobs=[]
    for offset in range(0,len(corpus),4):
        ordered=list(arms);rng.shuffle(ordered)
        for arm in ordered:
            root=suite/'jobs'/f'block-{offset//4+1:03d}'/arm[0]
            matched.write(root/'schema.json',matched.SCHEMA)
            jobs.append((arm,corpus[offset:offset+4],root))
    matched.write(suite/'input.json',corpus)
    matched.write(suite/'plan.json',{'kind':'matched_portable_skill_panel_not_product_policy','seed':args.seed,'model':args.model,'reasoning':args.reasoning,'timeout_seconds':args.timeout,'workers':args.workers,'input_sha256':matched.sha(args.corpus.read_bytes()),'arms_sha256':matched.sha(args.arms.read_bytes()),'selection_metadata_sha256':matched.sha(args.selection.read_bytes()),'order_metadata_sha256':matched.sha(args.order.read_bytes()),'group_metadata_sha256':matched.sha(args.groups.read_bytes()),'order_sha256':order_metadata['panel']['order_sha256'],'scheduler_sha256':matched.sha(Path(__file__).read_bytes()),'worker_sha256':matched.sha(Path(matched.__file__).read_bytes()),'jobs':[{'method':arm[0],'ids':[row['id'] for row in rows],'path':str(root)} for arm,rows,root in jobs]})
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures=[executor.submit(matched.run_arm,arm,rows,args,root) for arm,rows,root in jobs]
        records=[future.result() for future in futures]
    methods={};receipts={}
    for arm in arms:
        name=arm[0];rows=[];runs=[]
        for (job_arm,_,root),record in zip(jobs,records):
            if job_arm[0]==name:
                rows.extend(json.loads((root/'outputs'/f'{name}.json').read_text())['rewrites']);runs.append(record)
        matched.write(suite/'outputs'/f'{name}.json',{'rewrites':rows})
        methods[name]=rows;receipts[name]=runs
    matched.packets(suite,corpus)
    matched.write(suite/'evaluation-runs.json',{'methods':methods})
    matched.write(suite/'manifest.json',{'kind':'matched_portable_skill_panel_not_product_policy','codex_cli':subprocess.check_output([args.codex,'--version'],text=True).strip(),'plan_sha256':matched.sha((suite/'plan.json').read_bytes()),'evaluation_sha256':matched.sha((suite/'evaluation-runs.json').read_bytes()),'packet_sha256':matched.sha((suite/'judge-packets'/'anonymous.json').read_bytes()),'mapping_sha256':matched.sha((suite/'private-maps'/'mapping.json').read_bytes()),'runs':receipts})

if __name__=='__main__':main()
