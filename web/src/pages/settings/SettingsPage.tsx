import { Card } from "@/shared/components/ui/card";

export function SettingsPage() {
  return (
    <section className="space-y-4">
      <h1 className="text-3xl font-semibold text-slate-900">设置</h1>
      <Card>
        这里用于配置 API 地址、界面偏好与本地开发选项，作为控制台的统一设置入口。
      </Card>
    </section>
  );
}
