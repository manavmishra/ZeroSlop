// Only the private editor binding may reserve inference. No draft, IP address,
// or model output enters this coordinator; reservations are never refunded.
export const EDITOR_BUDGET_NAME = "editor-budget-v1";
const DAY_MS = 86_400_000;
const encoder = new TextEncoder();

export class HostedBudgetError extends Error {
  constructor(
    readonly code: "usage_limit" | "budget_unavailable",
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(code === "usage_limit"
      ? "Hosted editing is temporarily busy or at its free usage limit. " + (retryAfterSeconds === null
        ? "Please try again later."
        : `Please wait ${humanRetryDelay(retryAfterSeconds)} before trying again.`)
      : "Hosted capacity could not be checked. No model request was started. Please try again later.");
  }
  get status(): 429 | 503 { return this.code === "usage_limit" ? 429 : 503; }
}

function humanRetryDelay(seconds: number): string {
  if (seconds >= 3600) {
    const hours = Math.ceil(seconds / 3600);
    return `about ${hours} ${hours === 1 ? "hour" : "hours"}`;
  }
  if (seconds > 90) {
    const minutes = Math.ceil(seconds / 60);
    return `about ${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
  }
  return `at least ${seconds} ${seconds === 1 ? "second" : "seconds"}`;
}

export async function dailyBudgetClient(secret: string, address = "", now = Date.now()) {
  if (typeof secret !== "string" || secret.length < 32) throw new HostedBudgetError("budget_unavailable");
  const day = new Date(now).toISOString().slice(0, 10);
  const normalized = /^[a-f0-9:.]{1,64}$/i.test(address) ? address.toLowerCase() : "unknown";
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const digest = await crypto.subtle.sign("HMAC", key, encoder.encode(`zero-slop-editor-client-v1\n${day}\n${normalized}`));
  return { day, key: [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("") };
}

function configuredLimit(value: string | undefined, fallback: number, maximum: number): number {
  if (value === undefined) return fallback;
  if (!/^\d{1,5}$/.test(value)) throw new Error("invalid_budget_configuration");
  const limit = Number(value);
  if (limit > maximum) throw new Error("invalid_budget_configuration");
  return limit;
}

export class EditorBudgetStore {
  constructor(private readonly storage: DurableObjectStorage, private readonly env: Env) {
    storage.sql.exec("CREATE TABLE IF NOT EXISTS editor_budget_days (day TEXT PRIMARY KEY, reserved INTEGER NOT NULL CHECK(reserved >= 0))");
    storage.sql.exec("CREATE TABLE IF NOT EXISTS editor_budget_clients (day TEXT NOT NULL, client_key TEXT NOT NULL, calls INTEGER NOT NULL, minute INTEGER NOT NULL, minute_calls INTEGER NOT NULL, PRIMARY KEY(day, client_key))");
    storage.sql.exec("CREATE TABLE IF NOT EXISTS editor_openrouter_days (day TEXT PRIMARY KEY, calls INTEGER NOT NULL CHECK(calls >= 0))");
  }

  cleanup(now = Date.now()): void {
    const day = new Date(now).toISOString().slice(0, 10);
    this.storage.transactionSync(() => {
      this.storage.sql.exec("DELETE FROM editor_budget_clients WHERE day < ?", day);
      this.storage.sql.exec("DELETE FROM editor_budget_days WHERE day < ?", day);
      this.storage.sql.exec("DELETE FROM editor_openrouter_days WHERE day < ?", day);
    });
  }

  async reserve(input: unknown, clock = Date.now, provider: "workers-ai" | "openrouter" = "workers-ai"): Promise<Response> {
    const now = clock();
    if (!input || typeof input !== "object" || Array.isArray(input)) return new Response(null, { status: 400 });
    const body = input as Record<string, unknown>;
    const day = new Date(now).toISOString().slice(0, 10);
    const expectedKeys = provider === "openrouter" ? "clientKey,day" : "clientKey,day,neurons";
    if (Object.keys(body).sort().join(",") !== expectedKeys || body.day !== day
      || typeof body.clientKey !== "string" || !/^[a-f0-9]{64}$/.test(body.clientKey)
      || (provider === "workers-ai" && (typeof body.neurons !== "number" || !Number.isSafeInteger(body.neurons) || body.neurons < 1 || body.neurons > 8000))) {
      return new Response(null, { status: 400 });
    }
    const neurons = provider === "workers-ai" ? body.neurons as number : 0;
    const clientKey = body.clientKey;
    const daily = configuredLimit(this.env.EDITOR_DAILY_NEURONS, 8000, 8000);
    const clientDaily = configuredLimit(this.env.EDITOR_CLIENT_DAILY_CALLS, 5, 20);
    const clientMinute = configuredLimit(this.env.EDITOR_CLIENT_MINUTE_CALLS, 2, 5);
    // OpenRouter's free allowance is account-wide. Leave headroom for other
    // account activity; adding models or keys does not multiply this pool.
    const openRouterDaily = configuredLimit(this.env.EDITOR_OPENROUTER_DAILY_CALLS, 800, 1000);
    const nextDay = (Math.floor(now / DAY_MS) + 1) * DAY_MS;
    if (nextDay - now <= 60000) return Response.json({ allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((nextDay - now) / 1000)), reason: "day_reset" });
    // Persist expiration before granting anything. Even an idle object purges
    // daily pseudonyms; alarm failure denies the request instead of leaking it.
    const alarm = await this.storage.getAlarm();
    if (alarm === null || alarm > nextDay || alarm <= now) await this.storage.setAlarm(nextDay);
    const grantedAt = clock();
    if (new Date(grantedAt).toISOString().slice(0, 10) !== day) throw new Error("budget_day_changed");
    if (nextDay - grantedAt <= 60000) return Response.json({ allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((nextDay - grantedAt) / 1000)), reason: "day_reset" });
    this.cleanup(grantedAt);
    const result = this.storage.transactionSync(() => {
      const total = this.storage.sql.exec<{ reserved: number }>("SELECT reserved FROM editor_budget_days WHERE day = ?", day).toArray()[0]?.reserved ?? 0;
      const openRouterCalls = provider === "openrouter"
        ? this.storage.sql.exec<{ calls: number }>("SELECT calls FROM editor_openrouter_days WHERE day = ?", day).toArray()[0]?.calls ?? 0
        : 0;
      const client = this.storage.sql.exec<{ calls: number; minute: number; minute_calls: number }>("SELECT calls, minute, minute_calls FROM editor_budget_clients WHERE day = ? AND client_key = ?", day, clientKey).toArray()[0];
      const minute = Math.floor(grantedAt / 60_000);
      const minuteCalls = client?.minute === minute ? client.minute_calls : 0;
      if (provider === "workers-ai" && neurons > daily - total) {
        return { allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((nextDay - grantedAt) / 1000)), reason: "workers_daily" };
      }
      if (provider === "openrouter" && openRouterCalls >= openRouterDaily) {
        return { allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((nextDay - grantedAt) / 1000)), reason: "openrouter_daily" };
      }
      if ((client?.calls ?? 0) >= clientDaily) {
        return { allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((nextDay - grantedAt) / 1000)), reason: "client_daily" };
      }
      if (minuteCalls >= clientMinute) {
        return { allowed: false, retryAfterSeconds: Math.max(1, Math.ceil(((minute + 1) * 60_000 - grantedAt) / 1000)), reason: "client_minute" };
      }
      if (provider === "workers-ai") this.storage.sql.exec("INSERT INTO editor_budget_days(day, reserved) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET reserved = editor_budget_days.reserved + excluded.reserved", day, neurons);
      else this.storage.sql.exec("INSERT INTO editor_openrouter_days(day, calls) VALUES (?, 1) ON CONFLICT(day) DO UPDATE SET calls = editor_openrouter_days.calls + 1", day);
      this.storage.sql.exec("INSERT INTO editor_budget_clients(day, client_key, calls, minute, minute_calls) VALUES (?, ?, 1, ?, 1) ON CONFLICT(day, client_key) DO UPDATE SET calls = editor_budget_clients.calls + 1, minute = excluded.minute, minute_calls = ?", day, clientKey, minute, minuteCalls + 1);
      return { allowed: true, retryAfterSeconds: null };
    });
    return Response.json(result, { headers: { "cache-control": "no-store" } });
  }
}
