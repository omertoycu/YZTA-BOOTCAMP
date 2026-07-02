"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export function PageContainer({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login";

  if (isAuthPage) {
    return <main className="min-h-screen">{children}</main>;
  }

  return <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>;
}
