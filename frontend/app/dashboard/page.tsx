"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch, getToken } from "@/lib/api";
import type { Lead, Listing, StaleListingAlert } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Icon } from "@/components/ui/Icon";
import { ListingCard } from "@/components/ListingCard";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";

// Hatırlatması/randevusu önümüzdeki 48 saat içinde olan (ya da gecikmiş)
// adayları "bildirim" olarak sayıyoruz — ayrı bir bildirim tablosu yok,
// zaten dashboard'ın çektiği lead verisinden türetiliyor.
const NOTIFICATION_WINDOW_MS = 48 * 60 * 60 * 1000;

function getUrgentLeads(leads: Lead[]) {
  const cutoff = Date.now() + NOTIFICATION_WINDOW_MS;
  return leads
    .map((lead) => {
      const dueAt = [lead.reminder_at, lead.appointment_at]
        .filter((d): d is string => Boolean(d))
        .map((d) => ({ date: d, time: new Date(d).getTime() }))
        .filter((d) => d.time <= cutoff)
        .sort((a, b) => a.time - b.time)[0];
      return dueAt ? { lead, dueAt: dueAt.date, isAppointment: dueAt.date === lead.appointment_at } : null;
    })
    .filter((item): item is { lead: Lead; dueAt: string; isAppointment: boolean } => item !== null)
    .sort((a, b) => new Date(a.dueAt).getTime() - new Date(b.dueAt).getTime());
}

export default function DashboardPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [staleAlerts, setStaleAlerts] = useState<StaleListingAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const urgentLeads = useMemo(() => getUrgentLeads(leads), [leads]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      setIsLoading(true);
      try {
        const [listingsData, leadsData, staleAlertsData] = await Promise.all([
          apiFetch<Listing[]>("/listings"),
          apiFetch<Lead[]>("/leads"),
          apiFetch<StaleListingAlert[]>("/listings/stale-alerts"),
        ]);
        setListings(listingsData);
        setLeads(leadsData);
        setStaleAlerts(staleAlertsData);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [router]);

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-gutter">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-headline-lg text-primary">Genel Bakış</h2>
          <p className="mt-1 text-body-sm text-text-muted">
            Toplam: <span className="font-bold text-primary">{listings.length}</span> ilan aktif.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="glass-panel hidden items-center gap-2 rounded-full px-4 py-2 text-text-muted shadow-sm md:flex">
            <Icon name="search" />
            <input
              className="w-48 border-none bg-transparent text-sm outline-none focus:ring-0"
              placeholder="İlan veya müşteri ara..."
              type="text"
              disabled
            />
          </div>
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsNotificationsOpen((prev) => !prev)}
              aria-label="Bildirimler"
              className="relative flex h-10 w-10 items-center justify-center rounded-full bg-surface-container-lowest text-text-muted shadow-sm transition-colors hover:text-primary"
            >
              <Icon name="notifications" />
              {urgentLeads.length > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-error text-[10px] font-semibold text-on-error">
                  {urgentLeads.length}
                </span>
              )}
            </button>
            {isNotificationsOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setIsNotificationsOpen(false)} />
                <div className="absolute right-0 z-50 mt-2 w-80 rounded-lg bg-surface-container-lowest p-2 shadow-[0px_20px_50px_rgba(0,0,0,0.18)]">
                  <p className="px-3 py-2 text-body-sm font-medium text-on-surface">Yaklaşan hatırlatmalar</p>
                  {urgentLeads.length === 0 ? (
                    <p className="px-3 pb-3 text-body-sm text-text-muted">Yaklaşan hatırlatma veya randevu yok.</p>
                  ) : (
                    <ul className="flex max-h-80 flex-col gap-1 overflow-y-auto">
                      {urgentLeads.map(({ lead, dueAt, isAppointment }) => (
                        <li key={lead.id}>
                          <Link
                            href="/leads"
                            onClick={() => setIsNotificationsOpen(false)}
                            className="flex flex-col gap-0.5 rounded px-3 py-2 transition-colors hover:bg-surface-bright"
                          >
                            <span className="flex items-center gap-1.5 text-body-sm font-medium text-on-surface">
                              <Icon name={isAppointment ? "event" : "notifications"} className="text-[16px]" />
                              {lead.contact_phone}
                            </span>
                            <span className="text-[12px] text-text-muted">
                              {isAppointment ? "Randevu" : "Hatırlatma"}: {new Date(dueAt).toLocaleString("tr-TR")}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}
          </div>
          <Link
            href="/settings"
            aria-label="Hesap ayarları"
            className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-mint-accent text-secondary shadow-sm transition-transform hover:scale-105"
          >
            <Icon name="person" filled />
          </Link>
        </div>
      </header>

      {!isLoading && staleAlerts.length > 0 && (
        <Link
          href="/listings"
          className="flex items-center gap-3 rounded-lg bg-yellow-100 px-5 py-3.5 text-body-sm text-yellow-800 transition-colors hover:bg-yellow-200"
        >
          <Icon name="warning" />
          <span>
            <span className="font-semibold">{staleAlerts.length} portföy</span>{" "}
            uzun süredir aktif ve emsallere göre pahalı — en durgunu: &ldquo;{staleAlerts[0].title}&rdquo;{" "}
            (%{staleAlerts[0].overprice_pct} pahalı, {staleAlerts[0].age_days} gündür aktif)
          </span>
        </Link>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center gap-2 py-24 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-gutter xl:grid-cols-12">
          <div className="flex flex-col gap-6 xl:col-span-8">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {listings.slice(0, 4).map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
              {listings.length === 0 && (
                <p className="text-body-sm text-text-muted md:col-span-2">
                  Henüz portföy eklenmedi.
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-6 xl:col-span-4">
            <Link
              href="/listings/new"
              className="group relative flex h-64 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-lg border-2 border-dashed border-outline-variant bg-surface-container-lowest transition-colors hover:bg-surface-bright"
            >
              <div className="z-10 mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-white shadow-md transition-transform group-hover:scale-110">
                <Icon name="add" />
              </div>
              <p className="z-10 text-title-md font-medium text-primary">Yeni İlan Ekle</p>
            </Link>

            <div className="flex flex-1 flex-col rounded-lg bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
              <div className="mb-6 flex items-center justify-between">
                <h3 className="text-[18px] text-title-md text-primary">Aday Mesajları</h3>
                <Badge variant="brand">YZ Destekli</Badge>
              </div>
              <div className="flex max-h-[400px] flex-col gap-2 overflow-y-auto pr-2">
                {leads.slice(0, 6).map((lead) => (
                  <Link
                    key={lead.id}
                    href="/leads"
                    className="flex gap-4 rounded border border-transparent p-3 transition-colors hover:border-surface-variant hover:bg-surface-bright"
                  >
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-surface-container text-outline">
                      <Icon name="person" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <h4 className="font-semibold text-primary">{lead.contact_phone}</h4>
                      </div>
                      <p className="mt-1 text-[12px] text-text-muted">
                        {lead.district ?? "Bölge belirtilmedi"}
                        {lead.budget_max ? ` · ${formatCurrency(lead.budget_max)}'ye kadar` : ""}
                      </p>
                    </div>
                    <div className="flex items-center text-outline">
                      <Icon name="chevron_right" />
                    </div>
                  </Link>
                ))}
                {leads.length === 0 && (
                  <p className="text-body-sm text-text-muted">Henüz lead eklenmedi.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
