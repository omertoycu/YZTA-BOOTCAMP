"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Sidebar } from "@/components/Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isFullBleed = pathname === "/login" || pathname === "/" || pathname.startsWith("/p/");

  if (isFullBleed) {
    return <main className="min-h-screen">{children}</main>;
  }

  return (
    // h-screen yerine h-[100dvh]: mobil tarayıcılarda adres çubuğu
    // gizlenip/gösterilince 100vh sabit kalıp içeriğin altını kesiyordu.
    <div className="flex h-[100dvh] overflow-hidden">
      <Sidebar />
      <main className="h-full flex-1 overflow-y-auto p-4 pt-20 md:ml-72 md:p-8">{children}</main>
    </div>
  );
}
