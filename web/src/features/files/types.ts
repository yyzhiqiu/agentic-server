export type FileMetadata = Record<string, unknown>;

export type FileInfo = {
  id: string;
  filename: string;
  status: string;
  documentStatus: string;
  contentType: string | null;
  storageKey: string | null;
  size: number | null;
  userId: string | null;
  metadata: FileMetadata;
  createdAt: string | null;
};

export type FileListResponse = {
  items: FileInfo[];
  total: number;
};

export type FileUploadResponse = FileInfo;

export type FileDeleteResponse = {
  id: string;
  status: string;
};

export type FileDownloadResponse = {
  blob: Blob;
  filename: string;
  contentType: string | null;
};
