// Request-local state only. An editor request may have reserved/started work
// before its caller disconnects; never report that uncertain outcome as zero.
export type PipelineControl = { signal?: AbortSignal | undefined; editorRequested: boolean; deadline?: number };

export class PipelineCancelledError extends Error {
  readonly modelRequests: 0 | -1;
  constructor(control?: PipelineControl) {
    super("request_cancelled");
    this.name = "PipelineCancelledError";
    this.modelRequests = control?.editorRequested ? -1 : 0;
  }
}

export function checkCancelled(control?: PipelineControl): void {
  if (control?.signal?.aborted) throw new PipelineCancelledError(control);
  if (control?.deadline !== undefined && Date.now() >= control.deadline) throw new Error("upstream_deadline");
}

// Racing bounds our wait even if an upstream ignores AbortSignal. This cannot
// guarantee provider compute stops, and deliberately never refunds a grant.
export async function boundedOperation<T>(
  operation: (signal: AbortSignal) => Promise<T>,
  timeoutMs: number,
  control?: PipelineControl,
): Promise<T> {
  checkCancelled(control);
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let cancel = () => {};
  const stop = new Promise<never>((_resolve, reject) => {
    cancel = () => {
      const error = new PipelineCancelledError(control);
      reject(error);
      controller.abort(error);
    };
    control?.signal?.addEventListener("abort", cancel, { once: true });
    timer = setTimeout(() => {
      const error = new Error("upstream_deadline");
      reject(error);
      controller.abort(error);
    }, Math.min(timeoutMs, control?.deadline === undefined ? timeoutMs : Math.max(0, control.deadline - Date.now())));
  });
  try {
    // No await between listener registration and starting the operation.
    return await Promise.race([operation(controller.signal), stop]);
  } finally {
    clearTimeout(timer);
    control?.signal?.removeEventListener("abort", cancel);
  }
}
