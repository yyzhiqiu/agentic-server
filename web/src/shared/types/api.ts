export type ApiResponse<T> = {
  success: boolean;
  code: string;
  message: string;
  data: T;
  trace_id?: string;
};

export type PageResponse<T> = {
  items: T[];
  total: number;
};

export type ApiResponseMeta = {
  traceId?: string;
  requestId?: string;
};
