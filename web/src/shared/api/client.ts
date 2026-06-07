import { ApiError } from "@/shared/api/errors";
import { createId } from "@/shared/lib/id";
import type { ApiResponse } from "@/shared/types/api";

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export function buildApiUrl(path: string) {
  return `${DEFAULT_BASE_URL}${path}`;
}

function isApiResponse<T>(value: unknown): value is ApiResponse<T> {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  return (
    "success" in value &&
    "code" in value &&
    "message" in value &&
    "data" in value
  );
}

function buildHeaders(init: RequestInit, requestId: string) {
  const headers = new Headers(init.headers);

  if (!(init.body instanceof FormData) && init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  headers.set("X-Request-Id", requestId);
  return headers;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("Content-Type") ?? "";
  if (!contentType.includes("application/json")) {
    return null;
  }

  return response.json();
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const requestId = createId("req");
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: buildHeaders(init, requestId),
  });

  const responseTraceId = response.headers.get("X-Trace-Id") ?? undefined;
  const responseRequestId =
    response.headers.get("X-Request-Id") ?? requestId;
  const payload = await parseResponseBody(response);

  if (!response.ok) {
    if (isApiResponse(payload)) {
      throw new ApiError(payload.message, response.status, {
        code: payload.code,
        traceId: responseTraceId ?? payload.trace_id,
        requestId: responseRequestId,
        data: payload.data,
      });
    }

    throw new ApiError(`Request failed: ${response.status}`, response.status, {
      traceId: responseTraceId,
      requestId: responseRequestId,
    });
  }

  if (isApiResponse<T>(payload)) {
    if (!payload.success) {
      throw new ApiError(payload.message, response.status, {
        code: payload.code,
        traceId: responseTraceId ?? payload.trace_id,
        requestId: responseRequestId,
        data: payload.data,
      });
    }

    return payload.data;
  }

  return payload as T;
}
