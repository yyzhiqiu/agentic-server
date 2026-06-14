import { useState } from "react";
import { ShieldAlert, CheckCircle, RefreshCw, Sun, Moon } from "lucide-react";

import { Card } from "@/shared/components/ui/card";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { useTheme } from "@/shared/lib/ThemeContext";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { buildApiUrl } from "@/shared/api/client";

export function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  
  // API 地址配置状态
  const [apiUrl, setApiUrl] = useState(() => {
    return localStorage.getItem("api_base_url") ?? import.meta.env.VITE_API_BASE_URL ?? "";
  });
  
  const [savedUrl, setSavedUrl] = useState(() => {
    return localStorage.getItem("api_base_url") ?? import.meta.env.VITE_API_BASE_URL ?? "";
  });

  // 后端连接诊断状态
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "failed">("idle");
  const [testError, setTestError] = useState<string | null>(null);

  // 保存 API 配置
  function handleSaveApi() {
    const trimmed = apiUrl.trim();
    if (trimmed.length > 0) {
      localStorage.setItem("api_base_url", trimmed);
      setSavedUrl(trimmed);
    } else {
      localStorage.removeItem("api_base_url");
      setSavedUrl(import.meta.env.VITE_API_BASE_URL ?? "");
    }
    setTestStatus("idle");
    setTestError(null);
  }

  // 恢复 API 默认配置
  function handleResetApi() {
    localStorage.removeItem("api_base_url");
    const defaultUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    setApiUrl(defaultUrl);
    setSavedUrl(defaultUrl);
    setTestStatus("idle");
    setTestError(null);
  }

  // 后端连通性测试
  async function handleTestConnection() {
    setTestStatus("testing");
    setTestError(null);
    try {
      const targetUrl = buildApiUrl(API_ENDPOINTS.agents);
      const res = await fetch(targetUrl, {
        method: "GET",
        headers: {
          "Accept": "application/json",
        }
      });
      if (res.ok) {
        setTestStatus("success");
      } else {
        throw new Error(`HTTP 异常状态码: ${res.status}`);
      }
    } catch (err) {
      setTestStatus("failed");
      setTestError(err instanceof Error ? err.message : "网络连接异常，请检查网路。");
    }
  }

  return (
    <section className="h-full overflow-y-auto pr-2 space-y-6 animate-fade-in">
      <div className="select-none">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          在此统一配置与校验您的本地或远端多智能体运行环境、界面视觉偏好及 API 通信网络诊断。
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
        {/* API 核心配置 */}
        <Card className="space-y-5 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">后端 API 服务地址</h2>
              <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                前端面板与 FastAPI + LangGraph 后端服务交互的根路径。
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 select-none">
                API Base URL
              </label>
              <Input
                type="text"
                placeholder="例如 http://localhost:8000"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="font-mono text-xs"
              />
              <p className="text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed select-none">
                当前生效地址：<span className="font-mono bg-slate-100 dark:bg-slate-950 px-1.5 py-0.5 rounded text-slate-700 dark:text-slate-350">{savedUrl || "环境变量默认值"}</span>
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-4 border-t border-slate-100 dark:border-slate-800/40">
            <Button
              variant="primary"
              size="sm"
              onClick={handleSaveApi}
              className="text-xs font-semibold px-4 py-1.5"
            >
              应用并保存
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleResetApi}
              className="text-xs font-semibold px-4 py-1.5"
            >
              恢复默认
            </Button>
          </div>
        </Card>

        {/* 界面偏好与主题 */}
        <Card className="space-y-5 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">界面主题偏好</h2>
              <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
                切换高对比度护眼的暗黑模式或明亮的传统模式。
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => { if (theme !== "light") toggleTheme(); }}
                className={`flex-1 flex items-center justify-center gap-2 rounded-2xl border p-4 transition-all duration-300 font-medium text-sm ${
                  theme === "light"
                    ? "border-brand-650 bg-brand-50/50 text-brand-900 dark:border-brand-500 dark:bg-brand-950/20"
                    : "border-slate-200/80 bg-slate-50/50 text-slate-700 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950/20 dark:text-slate-400"
                }`}
              >
                <Sun size={16} className={theme === "light" ? "text-amber-500" : ""} />
                <span>明亮模式 (Light)</span>
              </button>

              <button
                type="button"
                onClick={() => { if (theme !== "dark") toggleTheme(); }}
                className={`flex-1 flex items-center justify-center gap-2 rounded-2xl border p-4 transition-all duration-300 font-medium text-sm ${
                  theme === "dark"
                    ? "border-brand-650 bg-brand-600 text-white dark:border-brand-500 dark:bg-brand-950/30"
                    : "border-slate-200/80 bg-slate-50/50 text-slate-700 hover:border-slate-300 dark:border-slate-800 dark:bg-slate-950/20 dark:text-slate-400"
                }`}
              >
                <Moon size={16} className={theme === "dark" ? "text-white" : ""} />
                <span>暗黑模式 (Dark)</span>
              </button>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 dark:border-slate-800/40 text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed select-none">
            提示：主题配置在切换后会自动写入本地存储，确保再次开启时无缝衔接。
          </div>
        </Card>
      </div>

      {/* 连接诊断与状态报告 */}
      <Card className="space-y-4 border-slate-200/80 bg-white/70 shadow-sm dark:border-slate-800/80 dark:bg-slate-900/60 p-6">
        <div className="border-b border-slate-100 dark:border-slate-800/50 pb-3 select-none flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-display">系统网络连通性诊断</h2>
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
              通过真实抓取后端服务健康节点，校验网络并反馈当前连通性诊断报告。
            </p>
          </div>
          
          <Button
            variant="secondary"
            size="sm"
            onClick={handleTestConnection}
            disabled={testStatus === "testing"}
            className="text-xs px-4 py-1.5 gap-2"
          >
            <RefreshCw size={13} className={testStatus === "testing" ? "animate-spin" : ""} />
            <span>开始网络诊断</span>
          </Button>
        </div>

        {/* 诊断结果看板 */}
        <div className="rounded-2xl border border-slate-200 bg-slate-50/30 dark:border-slate-800/80 dark:bg-slate-950/30 p-4">
          {testStatus === "idle" && (
            <p className="text-xs text-slate-450 dark:text-slate-500 text-center py-2 select-none">
              网络环境未诊断。点击右上方按钮开始与服务端进行通信校验。
            </p>
          )}

          {testStatus === "testing" && (
            <div className="flex items-center justify-center gap-3 py-2 select-none">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
              </span>
              <p className="text-xs text-slate-500 dark:text-slate-400">正在与后端服务进行握手，读取智能体配置表...</p>
            </div>
          )}

          {testStatus === "success" && (
            <div className="flex items-start gap-2.5 text-emerald-800 dark:text-emerald-450 py-1">
              <CheckCircle size={18} className="shrink-0 text-emerald-500 mt-0.5" />
              <div>
                <p className="text-xs font-bold">后端通信成功</p>
                <p className="mt-1 text-[11px] text-emerald-700 dark:text-emerald-500 leading-relaxed">
                  成功获取到了智能体（Coordinator Agents）配置元列表。前端已和后端服务建立正常通信。
                </p>
              </div>
            </div>
          )}

          {testStatus === "failed" && (
            <div className="flex items-start gap-2.5 text-red-800 dark:text-red-400 py-1 select-text">
              <ShieldAlert size={18} className="shrink-0 text-red-500 mt-0.5" />
              <div>
                <p className="text-xs font-bold">通信诊断失败</p>
                <p className="mt-1 text-[11px] leading-relaxed">
                  网络请求异常，当前配置地址与后端服务不匹配，或后端服务未启动。
                </p>
                {testError && (
                  <pre className="mt-2 text-[10px] font-mono bg-red-50/50 dark:bg-red-950/20 p-2 rounded-xl border border-red-200/40 dark:border-red-900/30 text-red-650 dark:text-red-450 whitespace-pre-wrap break-all leading-5">
                    错误快照: {testError}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      </Card>
    </section>
  );
}
