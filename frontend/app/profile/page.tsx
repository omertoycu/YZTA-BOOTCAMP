"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, Building2, ShieldCheck, CalendarDays, Settings as SettingsIcon } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { CurrentUser, Office, UserRole } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";

const ROLE_LABELS: Record<UserRole, string> = {
  owner: "Ofis Sahibi",
  agent: "Danışman",
  viewer: "Görüntüleyici",
};

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [office, setOffice] = useState<Office | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [userData, officeData] = await Promise.all([
          apiFetch<CurrentUser>("/users/me"),
          apiFetch<Office>("/offices/me"),
        ]);
        setUser(userData);
        setOffice(officeData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Profil bilgileri yüklenemedi");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-body-sm text-text-muted">
        <Spinner />
        Yükleniyor...
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6">
      <div>
        <h1 className="text-headline-lg text-primary">Profil</h1>
        <p className="mt-1 text-body-sm text-text-muted">
          Hangi hesapla ve hangi ofis adına giriş yaptığınızı buradan görebilirsiniz.
        </p>
      </div>

      {error && <Alert>{error}</Alert>}

      {user && office && (
        <>
          <div className="flex flex-col gap-4 rounded-lg bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-mint-accent text-title-md font-semibold text-secondary">
                {office.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <h2 className="text-title-md text-primary">{office.name}</h2>
                <Badge variant="brand">{ROLE_LABELS[user.role] ?? user.role}</Badge>
              </div>
            </div>

            <div className="flex flex-col gap-3 border-t border-outline-variant pt-4">
              <div className="flex items-center gap-3 text-body-sm text-on-surface">
                <Mail className="h-4 w-4 text-text-muted" />
                {user.email}
              </div>
              <div className="flex items-center gap-3 text-body-sm text-on-surface">
                <Building2 className="h-4 w-4 text-text-muted" />
                {office.name} — {office.subscription_plan === "starter" ? "Starter" : office.subscription_plan === "pro" ? "Pro" : office.subscription_plan === "office" ? "Office" : office.subscription_plan} planı
              </div>
              <div className="flex items-center gap-3 text-body-sm text-on-surface">
                <ShieldCheck className="h-4 w-4 text-text-muted" />
                {ROLE_LABELS[user.role] ?? user.role}
              </div>
              <div className="flex items-center gap-3 text-body-sm text-on-surface">
                <CalendarDays className="h-4 w-4 text-text-muted" />
                Üyelik: {new Date(user.created_at).toLocaleDateString("tr-TR")}
              </div>
            </div>
          </div>

          <Link
            href="/settings"
            className="flex items-center gap-3 rounded-lg bg-surface-container-lowest p-4 text-body-sm text-on-surface shadow-[0px_10px_30px_rgba(0,0,0,0.04)] transition-colors hover:bg-surface-bright"
          >
            <SettingsIcon className="h-4 w-4 text-text-muted" />
            WhatsApp ve bildirim ayarları
          </Link>
        </>
      )}
    </div>
  );
}
