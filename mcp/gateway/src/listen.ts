import { SERVER_INFO_META_KEY, SUBSCRIPTION_ID_META_KEY } from "@modelcontextprotocol/server";

type ListenRequest = { method: "subscriptions/listen"; id: string | number };

export function isListenRequest(body: unknown): body is ListenRequest {
  if (!body || typeof body !== "object" || Array.isArray(body)) return false;
  const { method, id } = body as { method?: unknown; id?: unknown };
  return method === "subscriptions/listen" && (typeof id === "string" || typeof id === "number");
}

/**
 * Ends an SDK `subscriptions/listen` stream straight after its acknowledgement.
 *
 * The gateway's tool list is fixed, so a subscription would only ever carry
 * keepalives. The SDK sends one every 15 seconds for as long as the client
 * holds the stream, and on the Workers Free plan that open stream ran past the
 * 10 ms CPU limit. The SDK has no option to close it, so this keeps the SDK's
 * acknowledgement (and its validation), cancels the stream, which clears the
 * SDK's keepalive timer, and appends the spec's graceful-close result.
 */
export async function completeListenStream(
  response: Response,
  request: ListenRequest,
  serverInfo: { name: string; version: string },
): Promise<Response> {
  if (!response.body || !response.headers.get("content-type")?.includes("text/event-stream")) return response;

  const reader = response.body.getReader();
  // The SDK enqueues the acknowledgement as soon as the stream starts.
  const acknowledgement = await reader.read();
  void reader.cancel().catch(() => undefined);

  const complete = new TextEncoder().encode(`event: message\ndata: ${JSON.stringify({
    jsonrpc: "2.0",
    id: request.id,
    result: {
      resultType: "complete",
      _meta: { [SUBSCRIPTION_ID_META_KEY]: request.id, [SERVER_INFO_META_KEY]: serverInfo },
    },
  })}\n\n`);
  const head: Uint8Array = acknowledgement.done ? new Uint8Array() : acknowledgement.value;
  const body = new Uint8Array(head.byteLength + complete.byteLength);
  body.set(head);
  body.set(complete, head.byteLength);
  return new Response(body, { status: response.status, statusText: response.statusText, headers: response.headers });
}
