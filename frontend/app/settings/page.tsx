"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BellRing } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { Office } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";

export default function SettingsPage() {
  const router = useRouter();
  const [office, setOffice] = useState<Office | null>(null);
  const [notificationPhone, setNotificationPhone] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      setIsLoading(true);
      try {
        const data = await apiFetch<Office>("/offices/me");
        setOffice(data);
        setNotificationPhone(data.notification_phone ?? "");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ofis bilgileri yüklenemedi");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [router]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await apiFetch<Office>("/offices/me", {
        method: "PATCH",
        body: JSON.stringify({ notification_phone: notificationPhone.trim() || null }),
      });
      setOffice(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kaydedilemedi");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6">
      <div>
        <h1 className="text-headline-lg text-primary">Ayarlar</h1>
        <p className="mt-1 text-body-sm text-text-muted">
          Ofisinizin bildirim ve entegrasyon tercihlerini yönetin.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center gap-2 py-16 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BellRing className="h-4 w-4 text-secondary" />
              <CardTitle>Yeni Aday Bildirimi</CardTitle>
            </div>
            <CardDescription>
              WhatsApp&apos;tan yeni bir aday mesajı geldiğinde, panelden uzaktayken de haberdar olun —
              aşağıdaki numaraya kendi WhatsApp&apos;ınızdan bir bildirim mesajı gönderilir.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSave} className="flex flex-col gap-4">
              <Input
                id="notificationPhone"
                label="Bildirim numarası"
                placeholder="905XX XXX XX XX"
                value={notificationPhone}
                onChange={(e) => setNotificationPhone(e.target.value)}
              />
              {!office?.notification_phone && !notificationPhone && (
                <p className="text-body-sm text-text-muted">
                  Henüz bir bildirim numarası ayarlanmadı — yeni adaylar sadece panelde görünecek.
                </p>
              )}
              {error && <Alert>{error}</Alert>}
              {saved && (
                <div className="rounded bg-mint-accent p-3 text-body-sm text-on-secondary-container">
                  Kaydedildi.
                </div>
              )}
              <Button type="submit" isLoading={isSaving} className="w-fit">
                Kaydet
              </Button>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
