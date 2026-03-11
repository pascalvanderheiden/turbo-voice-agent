"use client";

import { AppSidebar } from "@/components/layout/app-sidebar";
import { SiteHeader } from "@/components/layout/site-header";
import { MobileHeader } from "@/components/layout/mobile-header";
import { BottomTabBar } from "@/components/layout/bottom-tab-bar";
import { useIsMobile } from "@/hooks/use-is-mobile";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <div className="flex flex-col h-full w-full">
        <MobileHeader />
        <main className="flex-1 overflow-auto p-4 pb-20">{children}</main>
        <BottomTabBar />
      </div>
    );
  }

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
