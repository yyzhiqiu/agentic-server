import { Outlet } from "react-router-dom";

import { Header } from "@/shared/components/layout/Header";
import { Sidebar } from "@/shared/components/layout/Sidebar";

export function AppLayout() {
  return (
    <div className="h-screen w-screen overflow-hidden text-slate-800 dark:text-slate-100 antialiased transition-colors duration-300 bg-[#f0f4f9] dark:bg-[#131314]">
      <div className="flex h-full w-full gap-5 p-5 animate-fade-in overflow-hidden">
        <Sidebar />
        <div className="flex h-full flex-1 flex-col gap-4 overflow-hidden">
          <Header />
          <main className="flex-1 min-h-0">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
