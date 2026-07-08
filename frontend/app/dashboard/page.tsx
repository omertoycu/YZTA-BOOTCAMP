"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch, getToken } from "@/lib/api";
import type { Lead, LeadStatus, Listing, Office, StaleListingAlert } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Icon } from "@/components/ui/Icon";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";

// Hatırlatması/randevusu önümüzdeki 48 saat içinde olan (ya da gecikmiş)
// adayları "bildirim" olarak sayıyoruz — ayrı bir bildirim tablosu yok,
// zaten dashboard'ın çektiği lead verisinden türetiliyor.
const NOTIFICATION_WINDOW_MS = 48 * 60 * 60 * 1000;

const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
  new: "Yeni",
  contacted: "İletişim Kuruldu",
  viewing: "Yer Gösterimi",
  negotiation: "Pazarlık",
  won: "Kazanıldı",
  lost: "Kaybedildi",
};

function statusVariant(status: LeadStatus): NonNullable<BadgeProps["variant"]> {
  if (status === "won") return "success";
  if (status === "lost") return "danger";
  if (status === "new") return "brand";
  return "warning";
}

function leadDisplayName(lead: Lead) {
  return lead.contact_name?.trim() || lead.contact_phone;
}

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

function StatTile({ icon, label, value, href }: { icon: string; label: string; value: number; href: string }) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] transition-shadow hover:shadow-[0px_15px_40px_rgba(0,0,0,0.08)]"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-mint-accent text-secondary">
        <Icon name={icon} />
      </div>
      <div className="min-w-0">
        <p className="text-[22px] font-semibold leading-tight text-primary">{value}</p>
        <p className="truncate text-[12px] text-text-muted">{label}</p>
      </div>
    </Link>
  );
}

function QuickAction({ icon, title, subtitle, href }: { icon: string; title: string; subtitle: string; href: string }) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 rounded p-3 transition-colors hover:bg-surface-bright"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-container text-primary transition-colors group-hover:bg-mint-accent group-hover:text-secondary">
        <Icon name={icon} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-body-sm font-semibold text-primary">{title}</p>
        <p className="truncate text-[12px] text-text-muted">{subtitle}</p>
      </div>
      <Icon name="chevron_right" className="text-outline" />
    </Link>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [staleAlerts, setStaleAlerts] = useState<StaleListingAlert[]>([]);
  const [office, setOffice] = useState<Office | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);

  const urgentLeads = useMemo(() => getUrgentLeads(leads), [leads]);
  const newLeads = useMemo(() => leads.filter((l) => l.status === "new"), [leads]);
  const recentLeads = useMemo(
    () =>
      [...leads].sort((a, b) => {
        const aTime = new Date(a.last_contacted_at ?? a.created_at).getTime();
        const bTime = new Date(b.last_contacted_at ?? b.created_at).getTime();
        return bTime - aTime;
      }),
    [leads]
  );
  const recentListings = useMemo(
    () => [...listings].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [listings]
  );

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      setIsLoading(true);
      try {
        const [listingsData, leadsData, staleAlertsData, officeData] = await Promise.all([
          apiFetch<Listing[]>("/listings"),
          apiFetch<Lead[]>("/leads"),
          apiFetch<StaleListingAlert[]>("/listings/stale-alerts"),
          apiFetch<Office>("/offices/me").catch(() => null),
        ]);
        setListings(listingsData);
        setLeads(leadsData);
        setStaleAlerts(staleAlertsData);
        setOffice(officeData);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [router]);

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-gutter">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-headline-lg text-primary">Bugün</h2>
          <p className="mt-1 text-body-sm text-text-muted">
            Gününüzün özeti: yaklaşan randevular, yanıt bekleyen adaylar ve portföy sinyalleri.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/listings/new"
            className="hidden items-center gap-1.5 rounded-full bg-primary px-4 py-2.5 text-body-sm font-semibold text-on-primary shadow-sm transition-transform hover:scale-[1.03] md:flex"
          >
            <Icon name="add" className="!text-[18px]" />
            Yeni İlan
          </Link>
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
                              {leadDisplayName(lead)}
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
            href="/profile"
            aria-label="Profil"
            className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border-2 border-white bg-mint-accent text-secondary shadow-sm transition-transform hover:scale-105"
          >
            {office?.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={office.logo_url} alt={office.name} className="h-full w-full object-contain" />
            ) : (
              <Icon name="person" filled />
            )}
          </Link>
        </div>
      </header>

      {isLoading ? (
        <div className="flex items-center justify-center gap-2 py-24 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatTile icon="home_work" label="Aktif Portföy" value={listings.filter((l) => l.status === "active").length} href="/listings" />
            <StatTile icon="group" label="Toplam Aday" value={leads.length} href="/leads" />
            <StatTile icon="fiber_new" label="Yanıt Bekleyen Yeni Aday" value={newLeads.length} href="/leads" />
            <StatTile icon="event_upcoming" label="48 Saat İçinde Randevu / Hatırlatma" value={urgentLeads.length} href="/leads" />
          </div>

          {staleAlerts.length > 0 && (
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

          <div className="grid grid-cols-1 gap-gutter xl:grid-cols-12">
            <div className="flex flex-col gap-6 xl:col-span-7">
              <div className="rounded-lg bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-[18px] text-title-md text-primary">Bugünün Ajandası</h3>
                  <Badge variant="neutral">{urgentLeads.length} kayıt</Badge>
                </div>
                {urgentLeads.length === 0 ? (
                  <p className="text-body-sm text-text-muted">
                    Önümüzdeki 48 saatte planlı randevu veya hatırlatma yok. Adaylar sayfasından yeni bir
                    randevu planlayabilir ya da hatırlatma ekleyebilirsiniz.
                  </p>
                ) : (
                  <ul className="flex flex-col gap-1">
                    {urgentLeads.slice(0, 6).map(({ lead, dueAt, isAppointment }) => (
                      <li key={lead.id}>
                        <Link
                          href="/leads"
                          className="flex items-center gap-3 rounded p-3 transition-colors hover:bg-surface-bright"
                        >
                          <div
                            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                              isAppointment ? "bg-mint-accent text-secondary" : "bg-yellow-100 text-yellow-800"
                            }`}
                          >
                            <Icon name={isAppointment ? "event" : "alarm"} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-body-sm font-semibold text-primary">
                              {leadDisplayName(lead)}
                              {lead.contact_name && (
                                <span className="ml-2 font-normal text-text-muted">{lead.contact_phone}</span>
                              )}
                            </p>
                            <p className="truncate text-[12px] text-text-muted">
                              {isAppointment
                                ? `Yer gösterimi${lead.appointment_location ? ` · ${lead.appointment_location}` : ""}`
                                : `Hatırlatma${lead.reminder_note ? ` · ${lead.reminder_note}` : ""}`}
                            </p>
                          </div>
                          <p className="shrink-0 text-[12px] font-medium text-on-surface">
                            {new Date(dueAt).toLocaleString("tr-TR", {
                              day: "2-digit",
                              month: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-lg bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-[18px] text-title-md text-primary">Aday Mesajları</h3>
                  <Badge variant="brand">YZ Destekli</Badge>
                </div>
                <div className="flex max-h-[380px] flex-col gap-1 overflow-y-auto pr-1">
                  {recentLeads.slice(0, 6).map((lead) => (
                    <Link
                      key={lead.id}
                      href="/leads"
                      className="flex items-center gap-3 rounded p-3 transition-colors hover:bg-surface-bright"
                    >
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-surface-container text-outline">
                        <Icon name="person" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="truncate text-body-sm font-semibold text-primary">{leadDisplayName(lead)}</p>
                          <Badge variant={statusVariant(lead.status)}>
                            {LEAD_STATUS_LABELS[lead.status] ?? lead.status}
                          </Badge>
                        </div>
                        <p className="mt-0.5 truncate text-[12px] text-text-muted">
                          {lead.contact_name ? `${lead.contact_phone} · ` : ""}
                          {lead.district ?? "Bölge belirtilmedi"}
                          {lead.budget_max ? ` · ${formatCurrency(lead.budget_max)}'ye kadar` : ""}
                        </p>
                      </div>
                      <Icon name="chevron_right" className="shrink-0 text-outline" />
                    </Link>
                  ))}
                  {leads.length === 0 && (
                    <p className="text-body-sm text-text-muted">
                      Henüz aday yok — WhatsApp hattınız bağlandığında gelen mesajlar otomatik olarak burada
                      listelenir.
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-6 xl:col-span-5">
              <div className="rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
                <h3 className="mb-2 px-3 pt-2 text-[18px] text-title-md text-primary">Hızlı İşlemler</h3>
                <QuickAction icon="add_home_work" title="Yeni İlan Ekle" subtitle="6 adımlı rehberli sihirbaz" href="/listings/new" />
                <QuickAction icon="mic" title="Sesli Not ile İlan" subtitle="Konuşun, taslak otomatik oluşsun" href="/assistant" />
                <QuickAction icon="content_paste" title="Toplu İçe Aktar" subtitle="Sahibinden sayfa kaynağından" href="/listings/import" />
                <QuickAction icon="person_add" title="Aday Ekle" subtitle="Telefon + kriterlerle manuel kayıt" href="/leads" />
              </div>

              <div className="rounded-lg bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-[18px] text-title-md text-primary">Son Eklenen Portföyler</h3>
                  <Link href="/listings" className="text-[12px] font-semibold text-secondary hover:underline">
                    Tümünü Gör
                  </Link>
                </div>
                {recentListings.length === 0 ? (
                  <p className="text-body-sm text-text-muted">Henüz portföy eklenmedi.</p>
                ) : (
                  <ul className="flex flex-col gap-1">
                    {recentListings.slice(0, 5).map((listing) => (
                      <li key={listing.id}>
                        <Link
                          href={`/listings/${listing.id}`}
                          className="flex items-center gap-3 rounded p-2.5 transition-colors hover:bg-surface-bright"
                        >
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-mint-accent text-secondary">
                            <Icon
                              name={
                                listing.property_type === "land"
                                  ? "landscape"
                                  : listing.property_type === "commercial"
                                    ? "storefront"
                                    : "apartment"
                              }
                              className="!text-[18px]"
                            />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-body-sm font-medium text-on-surface">{listing.title}</p>
                            <p className="truncate text-[12px] text-text-muted">{listing.district}</p>
                          </div>
                          <p className="shrink-0 text-body-sm font-semibold text-primary">
                            {formatCurrency(listing.price)}
                            {listing.listing_type === "rent" ? " / ay" : ""}
                          </p>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
