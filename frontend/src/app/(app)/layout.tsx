"use client";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { SiteHeader } from "@/components/layout/site-header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <AppSidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <SiteHeader />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </>
  );
}
