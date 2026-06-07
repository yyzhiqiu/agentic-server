import { ApiError } from "@/shared/api/errors";
import { apiRequest, buildApiUrl } from "@/shared/api/client";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { createId } from "@/shared/lib/id";
import type { ApiResponse } from "@/shared/types/api";

import type {
  FileDeleteResponse,
  FileDownloadResponse,
  FileInfo,
  FileListResponse,
  FileMetadata,
  FileUploadResponse,
} from "@/features/files/types";

type BackendFileRecord = {
  id: string;
  filename: string;
  content_type: string | null;
  storage_key: string | null;
  size: number | null;
  user_id: string | null;
  status: string;
  metadata: FileMetadata;
  created_at: string | null;
};

type BackendFileListResponse = {
  items: BackendFileRecord[];
  total: number;
};

type BackendFileDeleteResponse = {
  id: string;
  status: string;
};

function readDocumentStatus(metadata: FileMetadata, fallbackStatus: string) {
  const documentStatus = metadata.document_status;
  return typeof documentStatus === "string" && documentStatus.length > 0
    ? documentStatus
    : fallbackStatus;
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

function buildDownloadHeaders(requestId: string) {
  const headers = new Headers();
  headers.set("X-Request-Id", requestId);
  return headers;
}

function readResponseFilename(response: Response, fallbackFilename: string) {
  const disposition = response.headers.get("Content-Disposition");
  if (!disposition) {
    return fallbackFilename;
  }

  const encodedMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    try {
      return decodeURIComponent(encodedMatch[1]);
    } catch {
      return encodedMatch[1];
    }
  }

  const filenameMatch = disposition.match(/filename="?([^"]+)"?/i);
  return filenameMatch?.[1] ?? fallbackFilename;
}

async function throwFileRequestError(
  response: Response,
  requestId: string,
): Promise<never> {
  const responseTraceId = response.headers.get("X-Trace-Id") ?? undefined;
  const responseRequestId =
    response.headers.get("X-Request-Id") ?? requestId;
  const contentType = response.headers.get("Content-Type") ?? "";

  if (contentType.includes("application/json")) {
    const payload = (await response.json()) as unknown;

    if (isApiResponse(payload)) {
      throw new ApiError(payload.message, response.status, {
        code: payload.code,
        traceId: responseTraceId ?? payload.trace_id,
        requestId: responseRequestId,
        data: payload.data,
      });
    }
  }

  throw new ApiError(`Request failed: ${response.status}`, response.status, {
    traceId: responseTraceId,
    requestId: responseRequestId,
  });
}

function mapFileInfo(record: BackendFileRecord): FileInfo {
  return {
    id: record.id,
    filename: record.filename,
    status: record.status,
    documentStatus: readDocumentStatus(record.metadata, "registered"),
    contentType: record.content_type,
    storageKey: record.storage_key,
    size: record.size,
    userId: record.user_id,
    metadata: record.metadata,
    createdAt: record.created_at,
  };
}

export async function getFiles(): Promise<FileListResponse> {
  const data = await apiRequest<BackendFileListResponse>(API_ENDPOINTS.files);

  return {
    items: data.items.map(mapFileInfo),
    total: data.total,
  };
}

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const data = await apiRequest<BackendFileRecord>(API_ENDPOINTS.fileUpload, {
    method: "POST",
    body: formData,
  });

  return mapFileInfo(data);
}

export async function deleteFile(fileId: string): Promise<FileDeleteResponse> {
  const data = await apiRequest<BackendFileDeleteResponse>(
    API_ENDPOINTS.fileDetail(fileId),
    {
      method: "DELETE",
    },
  );

  return {
    id: data.id,
    status: data.status,
  };
}

export async function downloadFile(
  fileId: string,
): Promise<FileDownloadResponse> {
  const requestId = createId("req");
  const response = await fetch(buildApiUrl(API_ENDPOINTS.fileDownload(fileId)), {
    headers: buildDownloadHeaders(requestId),
  });

  if (!response.ok) {
    await throwFileRequestError(response, requestId);
  }

  return {
    blob: await response.blob(),
    filename: readResponseFilename(response, `file-${fileId}`),
    contentType: response.headers.get("Content-Type"),
  };
}
