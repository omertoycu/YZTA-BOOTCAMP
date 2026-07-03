"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BarChart3 } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { ReportsOverview } from "@/lib/types";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-surface-container-lowest p-5 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
      <p className="font-label text-label-caps text-text-muted">{label}</p>
      <p className="text-headline-lg text-primary">{value}</p>
    </div>
  );
}

function DistrictBarList({ items }: { items: { district: string; count: number }[] }) {
  if (items.length === 0) {
    return <p className="text-body-sm text-text-muted">Henüz veri yok.</p>;
  }
  const max = Math.max(...items.map((i) => i.count));
  return (
    <div className="flex flex-col gap-2.5">
      {items.map((item) => (
        <div key={item.district} className="flex items-center gap-3">
          <span className="w-24 shrink-0 truncate text-body-sm text-on-surface" title={item.district}>
            {item.district}
          </span>
          <div className="h-3 flex-1 overflow-hidden rounded-full bg-surface-container">
            <div
              className="h-full rounded-full bg-secondary"
              style={{ width: `${Math.max((item.count / max) * 100, 4)}%` }}
            />
          </div>
          <span className="w-6 shrink-0 text-right text-body-sm font-medium text-on-surface">{item.count}</span>
        </div>
      ))}
    </div>
  );
}

const SCORE_BUCKET_COLOR: Record<string, string> = {
  "Yüksek (70-100)": "bg-emerald-500",
  "Orta (40-69)": "bg-yellow-500",
  "Düşük (0-39)": "bg-rose-500",
};

function ScoreDistribution({ buckets }: { buckets: { label: string; count: number }[] }) {
  const total = buckets.reduce((sum, b) => sum + b.count, 0);
  if (total === 0) {
    return <p className="text-body-sm text-text-muted">Henüz skorlanmış aday yok.</p>;
  }
  return (
    <div className="flex flex-col gap-2.5">
      {buckets.map((bucket) => (
        <div key={bucket.label} className="flex items-center gap-3">
          <span className="w-32 shrink-0 text-body-sm text-on-surface">{bucket.label}</span>
          <div className="h-3 flex-1 overflow-hidden rounded-full bg-surface-container">
            <div
              className={`h-full rounded-full ${SCORE_BUCKET_COLOR[bucket.label] ?? "bg-secondary"}`}
              style={{ width: `${Math.max((bucket.count / total) * 100, bucket.count > 0 ? 4 : 0)}%` }}
            />
          </div>
          <span className="w-6 shrink-0 text-right text-body-sm font-medium text-on-surface">{bucket.count}</span>
        </div>
      ))}
    </div>
  );
}

export default function ReportsPage() {
  const router = useRouter();
  const [data, setData] = useState<ReportsOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function load() {
    setIsLoading(true);
    setError(null);
    try {
      const overview = await apiFetch<ReportsOverview>("/reports/overview");
      setData(overview);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Raporlar yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-headline-lg text-primary">Reports</h1>
        <p className="mt-1 text-body-sm text-text-muted">Ofis performansına genel bakış.</p>
      </div>

      {error && <Alert>{error}</Alert>}

      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-16 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      )}

      {!isLoading && data && data.listing_count === 0 && data.lead_count === 0 && (
        <EmptyState
          icon={BarChart3}
          title="Henüz raporlanacak veri yok"
          description="Portföy ve aday eklemeye başladıkça burada ofis performansınızı göreceksiniz."
        />
      )}

      {!isLoading && data && (data.listing_count > 0 || data.lead_count > 0) && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatTile label="Toplam Portföy" value={data.listing_count} />
            <StatTile label="Aktif Portföy" value={data.active_listing_count} />
            <StatTile label="Toplam Aday" value={data.lead_count} />
            <StatTile label="Ortalama Skor" value={data.average_score ?? "—"} />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-lg bg-surface-container-lowest p-5 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
              <h2 className="mb-4 text-title-md text-primary">Bölgeye Göre Portföy</h2>
              <DistrictBarList items={data.listings_by_district} />
            </div>

            <div className="rounded-lg bg-surface-container-lowest p-5 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
              <h2 className="mb-4 text-title-md text-primary">Bölgeye Göre Aday</h2>
              <DistrictBarList items={data.leads_by_district} />
            </div>

            <div className="rounded-lg bg-surface-container-lowest p-5 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
              <h2 className="mb-4 text-title-md text-primary">Aday Skor Dağılımı</h2>
              <ScoreDistribution buckets={data.score_distribution} />
              <p className="mt-3 text-body-sm text-text-muted">
                {data.scored_lead_count} / {data.lead_count} aday skorlandı
              </p>
            </div>

            <div className="rounded-lg bg-surface-container-lowest p-5 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
              <h2 className="mb-4 text-title-md text-primary">Kaynağa Göre Aday</h2>
              <div className="flex flex-col gap-2.5">
                {Object.entries(data.leads_by_source).length === 0 && (
                  <p className="text-body-sm text-text-muted">Henüz veri yok.</p>
                )}
                {Object.entries(data.leads_by_source).map(([source, count]) => (
                  <div key={source} className="flex items-center justify-between rounded bg-surface-container px-3 py-2">
                    <span className="text-body-sm capitalize text-on-surface">
                      {source === "whatsapp" ? "WhatsApp" : "Manuel"}
                    </span>
                    <span className="text-body-sm font-semibold text-primary">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
