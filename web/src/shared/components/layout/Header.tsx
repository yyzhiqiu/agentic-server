import { Badge } from "@/shared/components/ui/badge";
import { APP_BADGE_LABEL, APP_NAME, APP_SUBTITLE } from "@/shared/constants/app";

export function Header() {
  return (
    <header className="rounded-3xl border border-white/70 bg-white/80 px-5 py-4 shadow-[0_12px_40px_rgba(40,53,15,0.06)] backdrop-blur">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">{APP_NAME}</p>
          <h2 className="text-xl font-semibold text-slate-900">{APP_SUBTITLE}</h2>
        </div>
        <Badge>{APP_BADGE_LABEL}</Badge>
      </div>
    </header>
  );
}
