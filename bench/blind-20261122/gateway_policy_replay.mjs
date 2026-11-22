#!/usr/bin/env node
/** Execute actual pinned gateway/scorer policy with a captured, local editor binding. */
import { execFileSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { snapshot, moduleFor, hash, save, load, options } from './web_policy_replay.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ENDPOINT = 'https://offline-policy-replay.invalid/editor';
// Public fixture key. This signs local captured packets only; never a production credential.
const FIXTURE_SIGNING_KEY = 'offline-benchmark-fixture-key-not-production-20261122';
const PYTHON_BRIDGE = `import json,sys\nsys.path.insert(0,sys.argv[1])\nimport scorer_core as s\np=json.load(sys.stdin); op=sys.argv[2]\nif op=='/report': r=s.report(p['text'],p.get('genre','general'))\nelif op=='/rank': r=s.rank(p['original'],p['candidates'],p.get('genre','general'))\nelif op=='/delta': r=s.delta(p['original'],p['rewrite'])\nelse: raise ValueError('unknown scorer operation')\nprint(json.dumps(r))\n`;
const genreFor = genre => ['social', 'email', 'research', 'general', 'professional'].includes(genre) ? genre : 'professional';
const logs = [];
console.log = (...values) => logs.push({ level: 'log', message: values.join(' ') });
console.warn = (...values) => logs.push({ level: 'warn', message: values.join(' ') });

async function stageCore(repo, revision, directory) {
  await mkdir(directory, { recursive: true });
  const script = `import importlib.util,json,sys\nfrom pathlib import Path\nspec=importlib.util.spec_from_file_location('matched_runner',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nprint(json.dumps(m.stage(Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4]),['mcp/gateway/src','mcp/scorer/src','bin/lib'])))`;
  const receipt = JSON.parse(execFileSync('python3', ['-c', script, join(HERE, 'run.py'), repo, revision, directory], { encoding: 'utf8' }));
  const esbuild = join(repo, 'mcp/gateway/node_modules/esbuild/bin/esbuild');
  const bundle = join(directory, 'pipeline.bundle.mjs');
  execFileSync(esbuild, [join(directory, 'mcp/gateway/src/pipeline.ts'), '--bundle', '--platform=node', '--format=esm', `--outfile=${bundle}`], { env: { ...process.env, NODE_PATH: join(repo, 'mcp/gateway/node_modules') }, stdio: ['ignore', 'pipe', 'pipe'] });
  return { ...receipt, bundle_sha256: hash(await readFile(bundle)), bundler_version: execFileSync(esbuild, ['--version'], { encoding: 'utf8' }).trim(), dependency_lock_sha256: hash(execFileSync('git', ['-C', repo, 'show', `${receipt.revision}:mcp/gateway/package-lock.json`])) };
}

async function actualPipeline(directory, source, editor) {
  const { runPipeline } = await import(pathToFileURL(join(directory, 'core/pipeline.bundle.mjs')).href);
  const scorerCalls = [];
  const scorerVersion = (await load(join(directory, 'core/mcp/scorer/src/scorer-manifest.json'))).version;
  const env = {
    EDITOR_ENDPOINT: ENDPOINT,
    EDITOR_SHARED_SECRET: FIXTURE_SIGNING_KEY,
    SCORER_VERSION: scorerVersion,
    SCORER: { fetch: async (input, init) => {
      const path = new URL(String(input)).pathname;
      const body = JSON.parse(String(init.body));
      const bytes = execFileSync('python3', ['-c', PYTHON_BRIDGE, join(directory, 'core/mcp/scorer/src'), path], { input: JSON.stringify(body), env: { ...process.env, ZERO_SLOP_HOME: join(directory, 'empty-private-state'), ZERO_SLOP_NO_NOTES: '1', PYTHONDONTWRITEBYTECODE: '1' }, maxBuffer: 4 * 1024 * 1024 });
      scorerCalls.push({ path, input_sha256: hash(JSON.stringify(body)), output_sha256: hash(bytes) });
      return Response.json(JSON.parse(bytes));
    } },
  };
  const requests = [];
  globalThis.fetch = async (input, init) => {
    if (String(input) !== ENDPOINT) throw new Error('network_disabled_in_gateway_replay');
    const body = JSON.parse(String(init.body));
    requests.push(body);
    return editor(body);
  };
  const start = logs.length;
  const result = await runPipeline(env, { text: source.text, genre: genreFor(source.genre) });
  globalThis.fetch = async () => { throw new Error('network_disabled_in_gateway_replay'); };
  return { result, editor_requests: requests, scorer_calls: scorerCalls, local_diagnostics: logs.slice(start) };
}

async function verify(directory, manifest) {
  if (hash(await readFile(join(directory, 'core/pipeline.bundle.mjs'))) !== manifest.core.bundle_sha256) throw new Error('Gateway bundle hash mismatch');
  for (const [relative, expected] of Object.entries(manifest.core.files)) {
    if (hash(await readFile(join(directory, 'core', relative))) !== expected) throw new Error(`Core source hash mismatch: ${relative}`);
  }
  for (const [relative, expected] of Object.entries(manifest.web.module_files)) {
    if (hash(await readFile(join(directory, 'web/module', relative))) !== expected) throw new Error(`Web module hash mismatch: ${relative}`);
  }
  if (hash(await readFile(join(directory, 'prepared-cases.json'))) !== manifest.prepared_cases_sha256) throw new Error('Prepared case hash mismatch');
}

async function prepare(args) {
  for (const key of ['core-repo', 'core-revision', 'web-repo', 'web-revision', 'input', 'out', 'contract']) if (!args[key]) throw new Error(`Missing --${key}`);
  if (!['plaintext', 'structured'].includes(args.contract)) throw new Error('Contract must be plaintext or structured');
  const out = resolve(args.out);
  try { await readFile(join(out, 'manifest.json')); throw new Error('Output already prepared'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const core = await stageCore(resolve(args['core-repo']), args['core-revision'], join(out, 'core'));
  const web = await snapshot(resolve(args['web-repo']), args['web-revision'], join(out, 'web/module'));
  web.module_files = {};
  for (const relative of Object.keys(web.files)) web.module_files[relative] = hash(await readFile(join(out, 'web/module', relative)));
  const module = await moduleFor(join(out, 'web'));
  const inputBytes = await readFile(args.input);
  const input = JSON.parse(inputBytes);
  const rows = (Array.isArray(input) ? input : input.drafts).slice(0, Number(args.limit ?? Infinity));
  const cachedManifest = args['protocol-cache'] ? await load(join(resolve(args['protocol-cache']), 'manifest.json')) : null;
  const cachedCaseBytes = args['protocol-cache'] ? await readFile(join(resolve(args['protocol-cache']), 'prepared-cases.json')) : null;
  if (cachedCaseBytes && hash(cachedCaseBytes) !== cachedManifest.prepared_cases_sha256) throw new Error('Protocol cache hash mismatch');
  const cachedCases = cachedCaseBytes ? JSON.parse(cachedCaseBytes) : [];
  if (cachedManifest && cachedManifest.system_prompt_sha256 !== hash(module.SYSTEM_PROMPT)) throw new Error('Protocol cache editorial policy differs');
  const cases = [];
  for (const row of rows) {
    const source = { id: row.id, text: row.text, genre: row.genre };
    if (typeof source.id !== 'string' || typeof source.text !== 'string' || typeof source.genre !== 'string') throw new Error('Invalid source');
    const capture = await actualPipeline(out, source, () => Response.json({ error: 'offline_capture_only', providerCalls: 0 }, { status: 503 }));
    if (capture.editor_requests.length > 1) throw new Error('Unexpected multiple gateway editor requests');
    let request = null;
    if (capture.editor_requests.length) {
      const body = capture.editor_requests[0];
      const cached = cachedCases.find(item => item.source.id === source.id);
      const generatedProtocol = await module.protectedProtocol(body.text);
      let protocol;
      if (cached?.request) {
        if (cached.request.body.text !== body.text || cached.request.body.genre !== body.genre || JSON.stringify(cached.request.body.diagnostics) !== JSON.stringify(body.diagnostics)) throw new Error(`Cached request context differs: ${source.id}`);
        protocol = { ...cached.request.protocol, removableFrames: new Map(cached.request.protocol.removableFrames) };
        const canonical = value => {
          const tokens = new Map(value.entries.map((entry, index) => [entry.token, `TOKEN_${index}`]));
          const normalize = text => { for (const [token, replacement] of tokens) text = text.split(token).join(replacement); return text; };
          return JSON.stringify({ entries: value.entries.map(entry => entry.text), masked: normalize(value.masked), removableFrames: [...value.removableFrames].map(([token, frame]) => [tokens.get(token), frame]), announcementGaps: value.announcementGaps.map(gap => ({ ...gap, before: tokens.get(gap.before), after: tokens.get(gap.after) })) });
        };
        if (canonical(protocol) !== canonical(generatedProtocol)) throw new Error('Cached protection coverage differs');
        if (module.userPacket(body, body.text, protocol) !== cached.request.user) throw new Error('Cached native packet differs');
      } else {
        if (cachedManifest) throw new Error(`Cached gateway routing differs: ${source.id}`);
        protocol = generatedProtocol;
      }
      request = { body, user: module.userPacket(body, body.text, protocol), protocol: { ...protocol, removableFrames: [...protocol.removableFrames] } };
    }
    if (cachedManifest && Boolean(cachedCases.find(item => item.source.id === source.id)?.request) !== Boolean(request)) throw new Error(`Cached gateway routing differs: ${source.id}`);
    cases.push({ source, request, capture: { route_editor: Boolean(request), result_without_model: capture.result, scorer_calls: capture.scorer_calls, local_diagnostics: capture.local_diagnostics } });
  }
  if (!cases.length || new Set(cases.map(row => row.source.id)).size !== cases.length) throw new Error('Empty or duplicate input');
  await save(join(out, 'prepared-cases.json'), cases);
  await writeFile(join(out, 'system-prompt.txt'), module.SYSTEM_PROMPT);
  const batchSize = Number(args['batch-size'] ?? 4);
  if (!Number.isInteger(batchSize) || batchSize < 1) throw new Error('Invalid batch size');
  const batches = [];
  for (let offset = 0; offset < cases.length; offset += batchSize) {
    const selected = cases.slice(offset, offset + batchSize).filter(row => row.request);
    const file = `batch-${String(offset / batchSize + 1).padStart(3, '0')}.prompt.txt`;
    const prompt = 'Same-host offline policy replay. Apply the exact editorial policy independently to each API-native user packet. Return the exact provider response string for each id in the required outer JSON schema. Do not use tools, inspect files, make external requests, or add editing instructions. Outer JSON is benchmark transport only.\n\nSYSTEM_PROMPT (verbatim):\n' + module.SYSTEM_PROMPT + '\n\nITEMS:\n' + JSON.stringify(selected.map(row => ({ id: row.source.id, user_packet: row.request.user })), null, 2);
    if (selected.length) await writeFile(join(out, file), prompt);
    batches.push({ block: offset / batchSize + 1, ids: selected.map(row => row.source.id), skipped_by_actual_gateway: cases.slice(offset, offset + batchSize).filter(row => !row.request).map(row => row.source.id), file: selected.length ? file : null, prompt_sha256: selected.length ? hash(prompt) : null });
  }
  await save(join(out, 'response-schema.json'), { type: 'object', additionalProperties: false, required: ['responses'], properties: { responses: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'provider_response'], properties: { id: { type: 'string' }, provider_response: { type: 'string' } } } } } });
  await save(join(out, 'manifest.json'), { schema: 1, kind: 'same_host_actual_gateway_policy_replay_not_production', adapter_sha256: hash(await readFile(fileURLToPath(import.meta.url))), protocol_cache_manifest_sha256: args['protocol-cache'] ? hash(await readFile(join(resolve(args['protocol-cache']), 'manifest.json'))) : null, contract: args.contract, core, web, input_sha256: hash(inputBytes), prepared_cases_sha256: hash(await readFile(join(out, 'prepared-cases.json'))), system_prompt_sha256: hash(module.SYSTEM_PROMPT), response_schema_sha256: hash(await readFile(join(out, 'response-schema.json'))), cases: cases.length, requested_cases: cases.filter(row => row.request).length, batch_size: batchSize, batches, limitations: ['Actual pinned routing, Python scorer and selection execute locally. The editor binding supplies recorded same-host outputs; no production call, quota reservation or provider fallback is exercised.', 'A public fixture key signs only local intercepted requests; it is not a production credential.', 'Gateway modelRequests fields reflect the injected replay envelope and are not evidence of actual provider requests. CLI receipts separately establish actual host inference calls.', 'The 75-second runtime budget applies only to local replay; offline inference duration is outside that clock and cannot establish live latency.', 'Legacy CLI approval compatibility is intentional and not a replay blocker.', 'Unknown editorial fidelity remains unproven by local acceptance.'] });
  process.stdout.write(JSON.stringify({ out, cases: cases.length, requested: cases.filter(row => row.request).length, core: core.revision, web: web.commit }) + '\n');
}

async function replay(args) {
  for (const key of ['prepared', 'responses', 'out']) if (!args[key]) throw new Error(`Missing --${key}`);
  const directory = resolve(args.prepared);
  const manifest = await load(join(directory, 'manifest.json'));
  await verify(directory, manifest);
  const module = await moduleFor(join(directory, 'web'));
  if (hash(module.SYSTEM_PROMPT) !== manifest.system_prompt_sha256) throw new Error('Web prompt hash mismatch');
  const cases = await load(join(directory, 'prepared-cases.json'));
  const responseBytes = await readFile(args.responses);
  const responses = JSON.parse(responseBytes).responses;
  if (!Array.isArray(responses) || new Set(responses.map(row => row.id)).size !== responses.length || responses.some(row => !cases.some(item => item.source.id === row.id && item.request))) throw new Error('Unexpected or duplicate response id');
  const results = [];
  for (const item of cases) {
    const response = responses.find(row => row.id === item.source.id);
    if (item.request && !response) { results.push({ id: item.source.id, status: 'missing_provider_response', result: null }); continue; }
    let accepted = null;
    let providerRejection = null;
    if (response) {
      try {
        const protocol = { ...item.request.protocol, removableFrames: new Map(item.request.protocol.removableFrames) };
        accepted = module.checkedProviderEdit(module.providerText({ response: response.provider_response }), protocol, item.request.body.text);
      } catch (error) { providerRejection = ['response_shape', 'empty_output', 'source_preservation', 'implausible_edit'].includes(error.outputStage) ? error.outputStage : error.name; }
    }
    const replayed = await actualPipeline(directory, item.source, () => {
      if (providerRejection) return Response.json({ error: 'editor_invalid_output', editorOutcome: 'invalid_output', providerCalls: 1 }, { status: 503 });
      if (!accepted) throw new Error('Unexpected editor request after capture');
      const payload = typeof accepted === 'string' ? { rewrite: accepted } : accepted;
      return Response.json({ ...payload, provider: 'same-host-replay', model: 'gpt-6.2-astra', stored: false, providerCalls: 1 });
    });
    if (Boolean(item.request) !== Boolean(replayed.editor_requests.length)) throw new Error('Gateway routing changed between capture and replay');
    results.push({ id: item.source.id, status: 'replayed', provider_response: response ? providerRejection ? 'rejected' : 'accepted' : 'not_requested_by_actual_gateway', provider_rejection: providerRejection, ...replayed, semantic_fidelity_proven: false });
  }
  if (args['evaluation-out']) {
    if (!args.method) throw new Error('--evaluation-out requires --method');
    await save(resolve(args['evaluation-out']), { methods: { [args.method]: results.map(row => ({ id: row.id, ...(row.result ? { text: row.result.text, pipelineResult: row.result } : {}), replay_status: row.status })) } });
  }
  await save(resolve(args.out), { kind: manifest.kind, core_revision: manifest.core.revision, web_revision: manifest.web.commit, response_sha256: hash(responseBytes), prepared_manifest_sha256: hash(await readFile(join(directory, 'manifest.json'))), results });
  process.stdout.write(JSON.stringify({ cases: results.length, replayed: results.filter(row => row.status === 'replayed').length, missing: results.filter(row => row.status !== 'replayed').length }) + '\n');
}

const [command, ...rest] = process.argv.slice(2);
if (command === 'prepare') await prepare(options(rest));
else if (command === 'replay') await replay(options(rest));
else throw new Error('Use prepare or replay; neither performs inference');
