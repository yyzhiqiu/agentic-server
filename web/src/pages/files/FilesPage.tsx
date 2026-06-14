import { useRef, useState } from "react";

import { Download, RefreshCcw, Trash2, Upload, FileText, FileJson, FileCode, File } from "lucide-react";

import {
  useDeleteFile,
  useDownloadFile,
  useFiles,
  useUploadFile,
} from "@/features/files/hooks";
import { EmptyState } from "@/shared/components/feedback/EmptyState";
import { ErrorState } from "@/shared/components/feedback/ErrorState";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { Card } from "@/shared/components/ui/card";
import { GUEST_USER_LABEL } from "@/shared/constants/app";
import { formatDate } from "@/shared/lib/date";

function getBadgeVariant(status: string): "default" | "success" | "warning" | "info" | "destructive" | "secondary" {
  if (status === "indexed") return "success";
  if (status === "stored" || status === "registered") return "warning";
  return "default";
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

  function getFileIcon(filename: string) {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (ext === "json") return <FileJson size={18} className="text-amber-500" />;
    if (["txt", "md", "csv"].includes(ext || "")) return <FileText size={18} className="text-blue-500" />;
    if (["js", "ts", "py", "sh", "tsx", "html", "css"].includes(ext || "")) return <FileCode size={18} className="text-purple-500" />;
    return <File size={18} className="text-slate-400" />;
  }

  return (
    <section className="h-full overflow-y-auto pr-2 space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between select-none">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            管理智能体检索增强生成 (RAG) 所需的参考文件。支持直接拖拽上传，系统会自动完成分块和索引流程。
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            void filesQuery.refetch();
          }}
          disabled={filesQuery.isFetching}
          className="gap-2 self-start lg:self-auto text-xs"
        >
          <RefreshCcw size={14} className={filesQuery.isFetching ? "animate-spin" : ""} />
          <span>刷新列表</span>
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* 上传面板 */}
        <Card className="space-y-4 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6 flex flex-col justify-between">
          <div className="select-none">
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">添加数据源</h2>
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
              添加的文档在完成分块索引后，可直接被 RAG 知识库及智能体流程检索并引用。
            </p>
          </div>

          <div className="relative border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-3xl p-8 text-center bg-slate-50/50 dark:bg-slate-950/20 hover:bg-white dark:hover:bg-slate-900/35 transition-all duration-300 group">
            <input
              ref={fileInputRef}
              type="file"
              onChange={(event) => {
                setSelectedFile(event.target.files?.[0] ?? null);
              }}
              disabled={uploadMutation.isPending}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="p-3 bg-brand-50 dark:bg-brand-950/45 rounded-2xl text-brand-700 dark:text-brand-400 group-hover:scale-110 transition-transform duration-300">
                <Upload size={24} />
              </div>
              <div className="select-none">
                <p className="text-sm font-bold text-slate-850 dark:text-slate-200">
                  {selectedFile ? `已选择：${selectedFile.name}` : "选择文件或拖拽上传到这里"}
                </p>
                <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                  支持 TXT, PDF, MD, JSON 等文档格式，单文件最大 10MB
                </p>
              </div>
              
              {selectedFile ? (
                <div className="pt-2">
                  <p className="text-[11px] text-slate-450 dark:text-slate-500 mb-2">
                    文件大小：{formatBytes(selectedFile.size)}
                  </p>
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleUpload();
                    }}
                    disabled={uploadMutation.isPending}
                    className="text-xs px-5 py-1.5 shadow-md"
                  >
                    {uploadMutation.isPending ? "正在上传..." : "确认开始上传"}
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </Card>

        {/* 状态统计面板 */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 select-none">
          <Card className="border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6 flex flex-col justify-center">
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">文件托管总量</p>
            <p className="mt-2 text-3xl font-extrabold text-slate-900 dark:text-slate-100 font-display">{total}</p>
          </Card>
          <Card className="border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6 flex flex-col justify-center">
            <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">完成向量化索引</p>
            <p className="mt-2 text-3xl font-extrabold text-brand-700 dark:text-brand-400 font-display">{indexedCount}</p>
          </Card>
        </div>
      </div>

      {actionMessage ? (
        <div className="rounded-2xl border border-emerald-250 bg-emerald-50/50 dark:border-emerald-900/30 dark:bg-emerald-950/20 px-4 py-3 text-xs text-emerald-800 dark:text-emerald-400">
          {actionMessage}
        </div>
      ) : null}

      {actionError ? <ErrorState message={actionError} /> : null}

      {filesQuery.isLoading ? (
        <Card className="flex items-center justify-center p-8">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
            </span>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">正在加载文件列表...</p>
          </div>
        </Card>
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
          title="暂无文件归档"
          description="系统目前未托管任何参考资料文件。请通过上方上传区域添加参考文档。"
        />
      ) : null}

      {!filesQuery.isLoading && !filesQuery.isError && total > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
          {files.map((file) => (
            <Card
              key={file.id}
              className="space-y-4 border border-slate-200 bg-white/70 dark:border-slate-800/80 dark:bg-slate-900/60 shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between border-b border-slate-100 dark:border-slate-800/50 pb-3">
                <div className="flex items-start gap-2.5 min-w-0">
                  <div className="p-2.5 bg-slate-100/60 dark:bg-slate-950/40 rounded-xl shrink-0">
                    {getFileIcon(file.filename)}
                  </div>
                  <div className="min-w-0">
                    <h2 className="truncate text-sm font-bold text-slate-900 dark:text-slate-100 font-display" title={file.filename}>
                      {file.filename}
                    </h2>
                    <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500 truncate">
                      类型: {file.contentType || "未知"} · 大小: {formatBytes(file.size)}
                    </p>
                  </div>
                </div>
                
                <div className="flex flex-wrap gap-1.5 self-start lg:self-auto shrink-0 select-none">
                  <Badge variant={getBadgeVariant(file.status)} className="text-[9px] px-2">
                    文件: {file.status}
                  </Badge>
                  <Badge variant={getBadgeVariant(file.documentStatus)} className="text-[9px] px-2">
                    索引: {file.documentStatus}
                  </Badge>
                </div>
              </div>

              <div className="grid gap-3 text-xs md:grid-cols-3 pt-1">
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    上传时间
                  </p>
                  <p className="mt-1 text-slate-700 dark:text-slate-350">
                    {file.createdAt ? formatDate(file.createdAt) : "无记录"}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    上传用户
                  </p>
                  <p className="mt-1 break-all text-slate-700 dark:text-slate-350">
                    {file.userId ?? GUEST_USER_LABEL}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-slate-400 dark:text-slate-500 tracking-wider">
                    存储密钥 Storage Key
                  </p>
                  <p className="mt-1 break-all text-slate-700 dark:text-slate-350 font-mono text-[10px]" title={file.storageKey ?? "未归档"}>
                    {file.storageKey ?? "未归档"}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap justify-end gap-2 pt-2 border-t border-slate-100/50 dark:border-slate-800/40">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    void handleDownload(file.id);
                  }}
                  disabled={downloadMutation.isPending || deleteMutation.isPending}
                  className="gap-2 text-xs font-semibold px-4 py-1.5"
                >
                  <Download size={13} />
                  <span>
                    {downloadMutation.isPending &&
                    downloadMutation.variables === file.id
                      ? "下载中..."
                      : "下载文件"}
                  </span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    void handleDelete(file.id, file.filename);
                  }}
                  disabled={deleteMutation.isPending || downloadMutation.isPending}
                  className="gap-2 text-red-650 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 text-xs font-semibold px-4 py-1.5"
                >
                  <Trash2 size={13} />
                  <span>
                    {deleteMutation.isPending && deleteMutation.variables === file.id
                      ? "删除中..."
                      : "永久删除"}
                  </span>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : null}
    </section>
  );
}
