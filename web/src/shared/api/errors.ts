type ApiErrorOptions = {
  code?: string;
  traceId?: string;
  requestId?: string;
  data?: unknown;
};

export class ApiError extends Error {
  status: number;
  code?: string;
  traceId?: string;
  requestId?: string;
  data?: unknown;

  constructor(message: string, status: number, options: ApiErrorOptions = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = options.code;
    this.traceId = options.traceId;
    this.requestId = options.requestId;
    this.data = options.data;
  }
}
