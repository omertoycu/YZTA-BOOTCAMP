"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BellRing, MessageCircle } from "lucide-react";
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
  const [whatsappPhoneNumberId, setWhatsappPhoneNumberId] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const [savingNotification, setSavingNotification] = useState(false);
  const [notificationError, setNotificationError] = useState<string | null>(null);
  const [notificationSaved, setNotificationSaved] = useState(false);

  const [savingWhatsapp, setSavingWhatsapp] = useState(false);
  const [whatsappError, setWhatsappError] = useState<string | null>(null);
  const [whatsappSaved, setWhatsappSaved] = useState(false);

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
        setWhatsappPhoneNumberId(data.whatsapp_phone_number_id ?? "");
      } catch (err) {
        setNotificationError(err instanceof Error ? err.message : "Ofis bilgileri yüklenemedi");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [router]);

  async function handleSaveNotification(e: React.FormEvent) {
    e.preventDefault();
    setSavingNotification(true);
    setNotificationError(null);
    setNotificationSaved(false);
    try {
      const updated = await apiFetch<Office>("/offices/me", {
        method: "PATCH",
        body: JSON.stringify({ notification_phone: notificationPhone.trim() || null }),
      });
      setOffice(updated);
      setNotificationSaved(true);
      setTimeout(() => setNotificationSaved(false), 3000);
    } catch (err) {
      setNotificationError(err instanceof Error ? err.message : "Kaydedilemedi");
    } finally {
      setSavingNotification(false);
    }
  }

  async function handleSaveWhatsapp(e: React.FormEvent) {
    e.preventDefault();
    setSavingWhatsapp(true);
    setWhatsappError(null);
    setWhatsappSaved(false);
    try {
      const updated = await apiFetch<Office>("/offices/me", {
        method: "PATCH",
        body: JSON.stringify({ whatsapp_phone_number_id: whatsappPhoneNumberId.trim() || null }),
      });
      setOffice(updated);
      setWhatsappSaved(true);
      setTimeout(() => setWhatsappSaved(false), 3000);
    } catch (err) {
      setWhatsappError(err instanceof Error ? err.message : "Kaydedilemedi");
    } finally {
      setSavingWhatsapp(false);
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
        <>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-secondary" />
                <CardTitle>WhatsApp Bağlantısı</CardTitle>
              </div>
              <CardDescription>
                Meta for Developers&apos;ta oluşturduğunuz WhatsApp Business numarasının{" "}
                <b>Phone Number ID</b>&apos;sini girin — takip mesajları, randevu onayları ve gelen aday
                mesajları bu numara üzerinden işler.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSaveWhatsapp} className="flex flex-col gap-4">
                <Input
                  id="whatsappPhoneNumberId"
                  label="Phone Number ID"
                  placeholder="Örn. 1279529618577191"
                  value={whatsappPhoneNumberId}
                  onChange={(e) => setWhatsappPhoneNumberId(e.target.value)}
                />
                {!office?.whatsapp_phone_number_id && !whatsappPhoneNumberId && (
                  <p className="text-body-sm text-text-muted">
                    Henüz bağlı değil — WhatsApp aksiyonları (takip mesajı, randevu onayı, otomatik takip)
                    bağlanana kadar aktif olmaz.
                  </p>
                )}
                {whatsappError && <Alert>{whatsappError}</Alert>}
                {whatsappSaved && (
                  <div className="rounded bg-mint-accent p-3 text-body-sm text-on-secondary-container">
                    Kaydedildi.
                  </div>
                )}
                <Button type="submit" isLoading={savingWhatsapp} className="w-fit">
                  Kaydet
                </Button>
              </form>
            </CardContent>
          </Card>

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
              <form onSubmit={handleSaveNotification} className="flex flex-col gap-4">
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
                {notificationError && <Alert>{notificationError}</Alert>}
                {notificationSaved && (
                  <div className="rounded bg-mint-accent p-3 text-body-sm text-on-secondary-container">
                    Kaydedildi.
                  </div>
                )}
                <Button type="submit" isLoading={savingNotification} className="w-fit">
                  Kaydet
                </Button>
              </form>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
