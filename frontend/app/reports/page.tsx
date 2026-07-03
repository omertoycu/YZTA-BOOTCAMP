"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";

export default function ReportsPage() {
  const router = useRouter();

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-mint-accent text-secondary">
        <Icon name="assessment" className="text-[32px]" />
      </div>
      <h1 className="text-headline-lg text-primary">Reports</h1>
      <p className="max-w-sm text-body-sm text-text-muted">
        Ofis performans raporları ve analizler yakında burada olacak.
      </p>
    </div>
  );
}
