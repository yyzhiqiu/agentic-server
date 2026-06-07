import { useRef, useState } from "react";

import { Download, RefreshCcw, Trash2, Upload } from "lucide-react";

import {
  useDeleteFile,
  useDownloadFile,
  useFiles,
  useUploadFile,
} from "@/features/files/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { LoadingState } from "@/shared/components/feedback/LoadingState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { Input } from "@/shared/components/ui/input";
import { GUEST_USER_LABEL } from "@/shared/constants/app";
import { formatDate } from "@/shared/lib/date";

function getStatusTone(status: string) {
  if (status === "indexed") {
    return "bg-emerald-100 text-emerald-800";
  }

  if (status === "stored" || status === "registered") {
    return "bg-amber-100 text-amber-800";
  }

  return "bg-slate-200 text-slate-700";
}

function formatBytes(size: number | null) {
  if (size === null) {
    return "未知大小";
  }

  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function triggerFileDownload(blob: Blob, filename: string) {
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

export function FilesPage() {
  const filesQuery = useFiles();
  const uploadMutation = useUploadFile();
  const downloadMutation = useDownloadFile();
  const deleteMutation = useDeleteFile();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const files = filesQuery.data?.items ?? [];
  const total = filesQuery.data?.total ?? 0;
  const indexedCount = files.filter(
    (file) => file.documentStatus === "indexed",
  ).length;

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }

    setActionError(null);
    setActionMessage(null);

    try {
      const uploadedFile = await uploadMutation.mutateAsync(selectedFile);
      setActionMessage(`已上传文件：${uploadedFile.filename}`);
      setSelectedFile(null);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "文件上传失败");
    }
  }

  async function handleDownload(fileId: string) {
    setActionError(null);
    setActionMessage(null);

    try {
      const result = await downloadMutation.mutateAsync(fileId);
      triggerFileDownload(result.blob, result.filename);
      setActionMessage(`已开始下载：${result.filename}`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "文件下载失败");
    }
  }

  async function handleDelete(fileId: string, filename: string) {
    const shouldDelete = window.confirm(`确认删除文件“${filename}”吗？`);
    if (!shouldDelete) {
      return;
    }

    setActionError(null);
    setActionMessage(null);

    try {
      await deleteMutation.mutateAsync(fileId);
      setActionMessage(`已删除文件：${filename}`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "文件删除失败");
    }
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-brand-700">
            Files
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">文件管理</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            这里展示上传状态、文档索引状态和创建时间，并提供单文件上传、下载与删除入口。
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void filesQuery.refetch();
          }}
          disabled={filesQuery.isFetching}
          className="gap-2"
        >
          <RefreshCcw size={16} className={filesQuery.isFetching ? "animate-spin" : ""} />
          刷新列表
        </Button>
      </div>

      <Card className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">上传文件</h2>
          <p className="mt-1 text-sm text-slate-500">
            支持单文件上传，完成后会自动刷新列表。
          </p>
        </div>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
          <Input
            ref={fileInputRef}
            type="file"
            onChange={(event) => {
              setSelectedFile(event.target.files?.[0] ?? null);
            }}
            disabled={uploadMutation.isPending}
          />
          <Button
            onClick={() => {
              void handleUpload();
            }}
            disabled={!selectedFile || uploadMutation.isPending}
            className="gap-2"
          >
            <Upload size={16} />
            {uploadMutation.isPending ? "上传中..." : "上传文件"}
          </Button>
        </div>

        {selectedFile ? (
          <p className="text-sm text-slate-600">
            已选择：{selectedFile.name} · {formatBytes(selectedFile.size)}
          </p>
        ) : null}
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <p className="text-sm text-slate-500">文件总数</p>
          <p className="mt-3 text-3xl font-semibold text-slate-900">{total}</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-500">已完成文档索引</p>
          <p className="mt-3 text-3xl font-semibold text-slate-900">{indexedCount}</p>
        </Card>
      </div>

      {actionMessage ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {actionMessage}
        </div>
      ) : null}

      {actionError ? <ErrorState message={actionError} /> : null}

      {filesQuery.isLoading ? (
        <LoadingState title="正在加载文件列表..." />
      ) : null}

      {filesQuery.isError ? (
        <div className="space-y-3">
          <ErrorState message={filesQuery.error.message} />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              void filesQuery.refetch();
            }}
          >
            重新加载
          </Button>
        </div>
      ) : null}

      {!filesQuery.isLoading && !filesQuery.isError && total === 0 ? (
        <EmptyState
          title="还没有文件记录"
          description="上传文件后，这里会展示文件和索引状态。"
        />
      ) : null}

      {!filesQuery.isLoading && !filesQuery.isError && total > 0 ? (
        <div className="grid gap-4">
          {files.map((file) => (
            <Card key={file.id} className="space-y-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <h2 className="truncate text-lg font-semibold text-slate-900">
                    {file.filename}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {file.contentType ?? "未知类型"}
                    {` · ${formatBytes(file.size)}`}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge className={getStatusTone(file.status)}>
                    文件状态: {file.status}
                  </Badge>
                  <Badge className={getStatusTone(file.documentStatus)}>
                    文档状态: {file.documentStatus}
                  </Badge>
                </div>
              </div>

              <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    创建时间
                  </p>
                  <p className="mt-1 text-slate-700">
                    {file.createdAt ? formatDate(file.createdAt) : "暂无"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    用户
                  </p>
                  <p className="mt-1 break-all text-slate-700">
                    {file.userId ?? GUEST_USER_LABEL}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-400">
                    Storage Key
                  </p>
                  <p className="mt-1 break-all text-slate-700">
                    {file.storageKey ?? "未登记"}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    void handleDownload(file.id);
                  }}
                  disabled={downloadMutation.isPending || deleteMutation.isPending}
                  className="gap-2"
                >
                  <Download size={16} />
                  {downloadMutation.isPending &&
                  downloadMutation.variables === file.id
                    ? "下载中..."
                    : "下载"}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    void handleDelete(file.id, file.filename);
                  }}
                  disabled={deleteMutation.isPending || downloadMutation.isPending}
                  className="gap-2 text-red-700 hover:bg-red-50"
                >
                  <Trash2 size={16} />
                  {deleteMutation.isPending && deleteMutation.variables === file.id
                    ? "删除中..."
                    : "删除"}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
