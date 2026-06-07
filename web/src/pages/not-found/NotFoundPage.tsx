import { Link } from "react-router-dom";

import { ROUTES } from "@/shared/constants/routes";
import { cn } from "@/shared/lib/cn";

export function NotFoundPage() {
  return (
    <section className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <p className="text-sm uppercase tracking-[0.3em] text-brand-700">404</p>
      <h1 className="text-4xl font-semibold text-slate-900">页面不存在</h1>
      <p className="max-w-md text-sm text-slate-600">
        这个地址不存在，或者控制台没有为它注册路由。你可以先回到聊天页继续浏览。
      </p>
      <Link
        className={cn(
          "inline-flex items-center justify-center rounded-full bg-brand-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-900",
        )}
        to={ROUTES.chat}
      >
        返回聊天页
      </Link>
    </section>
  );
}
