#!/usr/bin/env python3
"""Run prepared exact gateway-policy requests on one existing host; never production."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
CODEX = '/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def invoke(job, args, suite):
    name, prepared, batch = job
    request = (prepared / batch['file']).read_bytes()
    if sha(request) != batch['prompt_sha256']: raise ValueError('Prepared prompt hash mismatch')
    directory = suite/'calls'/name/f"block-{batch['block']:03d}"
    directory.mkdir(parents=True)
    (directory/'prompt.txt').write_bytes(request)
    record = {'method':name,'block':batch['block'],'ids':batch['ids'],'prompt_sha256':sha(request),'started_utc':dt.datetime.now(dt.timezone.utc).isoformat()}
    start=time.monotonic(); rows=[]
    with tempfile.TemporaryDirectory(prefix='zs-policy-host-') as empty_root:
        command=[args.codex,'exec','-m',args.model,'-c',f'model_reasoning_effort="{args.reasoning}"','-s','read-only','--ephemeral','--ignore-user-config','--ignore-rules','--skip-git-repo-check','--json','--output-schema',str(prepared/'response-schema.json'),'-o',str(directory/'response.json'),'-C',empty_root,'-']
        record['command']=command
        try:
            result=subprocess.run(command,input=request,capture_output=True,timeout=args.timeout)
            (directory/'stdout.jsonl').write_bytes(result.stdout);(directory/'stderr.log').write_bytes(result.stderr)
            record['returncode']=result.returncode
            if result.returncode: raise ValueError(f'CLI exited {result.returncode}')
            events=[json.loads(line) for line in result.stdout.decode().splitlines() if line.strip()]
            forbidden={'command_execution','mcp_tool_call','web_search','image_view','collab_tool_call'}
            record['tool_items']=[event.get('item',{}).get('type') for event in events if event.get('item',{}).get('type') in forbidden]
            if record['tool_items']:raise ValueError('No-tools policy violated')
            raw=(directory/'response.json').read_bytes();record['response_sha256']=sha(raw)
            payload=json.loads(raw); rows=payload['responses']
            if [row.get('id') for row in rows]!=batch['ids'] or any(not isinstance(row.get('provider_response'),str) or not row['provider_response'].strip() for row in rows):raise ValueError('Missing, reordered or empty provider response')
            record['status']='complete'
        except subprocess.TimeoutExpired as error:
            (directory/'stdout.jsonl').write_bytes(error.stdout or b'');(directory/'stderr.log').write_bytes(error.stderr or b'')
            record.update(status='failed',error=f'timeout after {args.timeout}s');rows=[]
        except (ValueError,KeyError,OSError) as error:record.update(status='failed',error=str(error));rows=[]
    record['elapsed_seconds']=round(time.monotonic()-start,3);record['finished_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    write(directory/'receipt.json',record)
    print(name,batch['block'],record['status'],record['elapsed_seconds'],flush=True)
    return record,rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arms',type=Path,required=True)
    parser.add_argument('--suite',type=Path,required=True)
    parser.add_argument('--model',default='gpt-6.2-astra')
    parser.add_argument('--reasoning',default='high')
    parser.add_argument('--timeout',type=int,default=600)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--codex',default=CODEX)
    parser.add_argument('--node',default='node')
    args=parser.parse_args()
    if not 1<=args.workers<=2:parser.error('At most two concurrent CLI calls')
    suite=args.suite.resolve()
    if suite.exists():parser.error('Choose a new suite directory')
    suite.mkdir(parents=True)
    arms=json.loads(args.arms.read_text()); manifests={};sources={}
    for arm in arms:
        prepared=Path(arm['prepared']).resolve();manifest=json.loads((prepared/'manifest.json').read_text())
        if manifest.get('response_schema_sha256')!=sha((prepared/'response-schema.json').read_bytes()):parser.error('Prepared schema hash missing or mismatched')
        manifests[arm['name']]=manifest;sources[arm['name']]=prepared
    if len({manifest['input_sha256'] for manifest in manifests.values()})!=1:parser.error('Policy arms do not share input artifact')
    if len({manifest['batch_size'] for manifest in manifests.values()})!=1:parser.error('Policy arms do not share batch size')
    if len({manifest['response_schema_sha256'] for manifest in manifests.values()})!=1:parser.error('Policy arms do not share output schema')
    jobs=[]
    for block in sorted({batch['block'] for manifest in manifests.values() for batch in manifest['batches']}):
        for arm in arms:
            for batch in manifests[arm['name']]['batches']:
                if batch['block']==block and batch['file']:jobs.append((arm['name'],sources[arm['name']],batch))
    write(suite/'plan.json',{'kind':'same_host_actual_gateway_policy_replay_not_production','model':args.model,'reasoning':args.reasoning,'timeout_seconds':args.timeout,'workers':args.workers,'harness_sha256':sha(Path(__file__).read_bytes()),'arms_config_sha256':sha(args.arms.read_bytes()),'prepared_manifests':{name:sha((directory/'manifest.json').read_bytes()) for name,directory in sources.items()},'jobs':[{'method':name,'block':batch['block'],'ids':batch['ids']} for name,_,batch in jobs]})
    results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures=[executor.submit(invoke,job,args,suite) for job in jobs]
        for future in concurrent.futures.as_completed(futures):results.append(future.result())
    methods={};receipts={}
    for arm in arms:
        name=arm['name']; responses=[];records=[]
        for record,rows in sorted(results,key=lambda value:value[0]['block']):
            if record['method']==name:responses.extend(rows);records.append(record)
        response_path=suite/'outputs'/f'{name}-provider-responses.json';write(response_path,{'responses':responses})
        replay=suite/'outputs'/f'{name}-pipeline.json';evaluation=suite/'outputs'/f'{name}-evaluation.json'
        subprocess.run([args.node,str(HERE/'gateway_policy_replay.mjs'),'replay','--prepared',str(sources[name]),'--responses',str(response_path),'--out',str(replay),'--method',name,'--evaluation-out',str(evaluation)],check=True)
        methods.update(json.loads(evaluation.read_text())['methods'])
        receipts[name]={'calls':records,'provider_responses_sha256':sha(response_path.read_bytes()),'pipeline_results_sha256':sha(replay.read_bytes()),'evaluation_sha256':sha(evaluation.read_bytes())}
    write(suite/'evaluation-runs.json',{'methods':methods})
    write(suite/'manifest.json',{'kind':'same_host_actual_gateway_policy_replay_not_production','model':args.model,'reasoning':args.reasoning,'timeout_seconds':args.timeout,'codex_version':subprocess.check_output([args.codex,'--version'],text=True).strip(),'plan_sha256':sha((suite/'plan.json').read_bytes()),'evaluation_sha256':sha((suite/'evaluation-runs.json').read_bytes()),'methods':receipts})

if __name__=='__main__':main()
