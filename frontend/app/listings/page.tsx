"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AlertTriangle, Building2, Sparkles } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { Listing, ListingType, PricingSuggestion, PropertyType, StaleListingAlert } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { Alert } from "@/components/ui/Alert";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ListingCard } from "@/components/ListingCard";

type StatusFilter = "all" | ListingType;
type TypeFilter = "all" | PropertyType;

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Tümü" },
  { value: "sale", label: "Satılık" },
  { value: "rent", label: "Kiralık" },
];

const TYPE_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: "all", label: "Tümü" },
  { value: "residential", label: "Konut" },
  { value: "commercial", label: "İş Yeri" },
  { value: "land", label: "Arsa" },
];

// Türkçe büyük/küçük harf kurallarına göre karşılaştırma — düz toLowerCase()
// "İstanbul" gibi noktalı büyük İ'yi yanlış küçültür ("i̇stanbul").
function normalizeTr(value: string): string {
  return value.toLocaleLowerCase("tr-TR");
}

function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (value: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="flex w-fit flex-wrap gap-1 rounded-full bg-surface-container p-1">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`rounded-full px-3.5 py-1.5 text-body-sm font-medium transition-colors ${
            value === option.value
              ? "bg-primary text-on-primary shadow-sm"
              : "text-text-muted hover:text-primary"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export default function ListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pricingByListing, setPricingByListing] = useState<Record<string, PricingSuggestion>>({});
  const [pricingLoading, setPricingLoading] = useState<string | null>(null);
  const [pricingError, setPricingError] = useState<string | null>(null);
  const [staleAlertsByListing, setStaleAlertsByListing] = useState<Record<string, StaleListingAlert>>({});
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Filtreleme tamamen istemci tarafında — GET /listings zaten ofisin tüm
  // portföyünü tek seferde döndürüyor (sayfalama yok, hedef ölçek 1-5
  // danışmanlı ofis), ekstra istek atmaya gerek yok.
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [minSqm, setMinSqm] = useState("");
  const [maxSqm, setMaxSqm] = useState("");

  const hasActiveFilters =
    search.trim() !== "" || statusFilter !== "all" || typeFilter !== "all" || minSqm !== "" || maxSqm !== "";

  function clearFilters() {
    setSearch("");
    setStatusFilter("all");
    setTypeFilter("all");
    setMinSqm("");
    setMaxSqm("");
  }

  const filteredListings = useMemo(() => {
    const query = normalizeTr(search.trim());
    const min = minSqm !== "" ? Number(minSqm) : null;
    const max = maxSqm !== "" ? Number(maxSqm) : null;

    return listings.filter((listing) => {
      // Şehir/ilçe/mahalle: tek bir yapılandırılmış alan yok — district
      // (il/ilçe) ve title (mahalle çoğunlukla burada geçiyor, bkz.
      // Matching Agent'ın aynı yaklaşımı) birlikte aranıyor.
      if (query && !normalizeTr(`${listing.title} ${listing.district}`).includes(query)) {
        return false;
      }
      if (statusFilter !== "all" && listing.listing_type !== statusFilter) return false;
      if (typeFilter !== "all" && listing.property_type !== typeFilter) return false;
      if (min !== null || max !== null) {
        if (listing.square_meters == null) return false;
        if (min !== null && listing.square_meters < min) return false;
        if (max !== null && listing.square_meters > max) return false;
      }
      return true;
    });
  }, [listings, search, statusFilter, typeFilter, minSqm, maxSqm]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    loadListings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadListings() {
    setIsLoading(true);
    setError(null);
    try {
      const [data, staleAlerts] = await Promise.all([
        apiFetch<Listing[]>("/listings"),
        apiFetch<StaleListingAlert[]>("/listings/stale-alerts"),
      ]);
      setListings(data);
      setStaleAlertsByListing(Object.fromEntries(staleAlerts.map((a) => [a.listing_id, a])));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföyler yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }

  async function handlePricingSuggestion(listingId: string) {
    setPricingLoading(listingId);
    setPricingError(null);
    try {
      const suggestion = await apiFetch<PricingSuggestion>(`/listings/${listingId}/pricing-suggestion`);
      setPricingByListing((prev) => ({ ...prev, [listingId]: suggestion }));
    } catch (err) {
      setPricingError(err instanceof Error ? err.message : "Fiyat önerisi alınamadı");
    } finally {
      setPricingLoading(null);
    }
  }

  async function handleDeleteListing(listingId: string) {
    setError(null);
    setDeleteLoading(true);
    try {
      await apiFetch(`/listings/${listingId}`, { method: "DELETE" });
      setListings((prev) => prev.filter((l) => l.id !== listingId));
      setPendingDeleteId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföy silinemedi");
    } finally {
      setDeleteLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-headline-lg text-primary">Portföyler</h1>
          <p className="mt-1 text-body-sm text-text-muted">
            Ofisinizin tüm gayrimenkul portföyünü tek yerden yönetin.
          </p>
        </div>
        <Link href="/listings/new">
          <Button>
            <Icon name="add" />
            Yeni İlan Ekle
          </Button>
        </Link>
      </div>

      {error && <Alert>{error}</Alert>}
      {pricingError && <Alert>{pricingError}</Alert>}

      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-16 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      )}

      {!isLoading && !error && listings.length === 0 && (
        <EmptyState
          icon={Building2}
          title="Henüz portföy eklenmedi"
          description="Yukarıdaki 'Yeni İlan Ekle' butonuyla ilk portföyünüzü ekleyin."
        />
      )}

      {!isLoading && !error && listings.length > 0 && (
        <div className="flex flex-col gap-4 rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <div className="relative flex-1">
              <Icon
                name="search"
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 !text-[20px] text-outline"
              />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Şehir, ilçe veya mahalle ara..."
                aria-label="Şehir, ilçe veya mahalle ara"
                className="h-10 w-full rounded-full border border-outline-variant bg-surface-container-lowest pl-10 pr-3 text-body-sm text-on-surface placeholder:text-text-muted transition-shadow focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary-container"
              />
            </div>
            <div className="flex items-center gap-2 text-body-sm text-text-muted">
              <span>m²</span>
              <input
                type="number"
                min={0}
                inputMode="numeric"
                value={minSqm}
                onChange={(e) => setMinSqm(e.target.value)}
                placeholder="Min"
                aria-label="Minimum metrekare"
                className="h-10 w-20 rounded border border-outline-variant bg-surface-container-lowest px-2 text-body-sm text-on-surface placeholder:text-text-muted focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary-container"
              />
              <span>–</span>
              <input
                type="number"
                min={0}
                inputMode="numeric"
                value={maxSqm}
                onChange={(e) => setMaxSqm(e.target.value)}
                placeholder="Max"
                aria-label="Maksimum metrekare"
                className="h-10 w-20 rounded border border-outline-variant bg-surface-container-lowest px-2 text-body-sm text-on-surface placeholder:text-text-muted focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary-container"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <SegmentedControl value={statusFilter} onChange={setStatusFilter} options={STATUS_OPTIONS} />
              <SegmentedControl value={typeFilter} onChange={setTypeFilter} options={TYPE_OPTIONS} />
            </div>
            <div className="flex items-center gap-3">
              <span className="text-body-sm text-text-muted">
                {filteredListings.length} / {listings.length} portföy
              </span>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="text-body-sm font-medium text-secondary hover:underline"
                >
                  Filtreleri temizle
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {!isLoading && !error && listings.length > 0 && filteredListings.length === 0 && (
        <EmptyState
          icon={Building2}
          title="Filtrelere uygun portföy bulunamadı"
          description="Arama kriterlerinizi veya filtreleri değiştirmeyi deneyin."
        />
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredListings.map((listing) => {
          const suggestion = pricingByListing[listing.id];
          const staleAlert = staleAlertsByListing[listing.id];
          return (
            <div key={listing.id} className="flex flex-col gap-2">
              <ListingCard listing={listing} onDelete={() => setPendingDeleteId(listing.id)} />
              {staleAlert && (
                <div className="flex items-start gap-2 rounded bg-yellow-100 px-3 py-2.5 text-body-sm text-yellow-800">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{staleAlert.message}</span>
                </div>
              )}
              <Button
                variant="outline"
                size="sm"
                isLoading={pricingLoading === listing.id}
                onClick={() => handlePricingSuggestion(listing.id)}
                className="w-fit"
              >
                <Sparkles className="h-3.5 w-3.5" />
                Fiyat önerisi
              </Button>
              {suggestion && (
                <div className="rounded bg-mint-accent px-3 py-2.5 text-body-sm text-on-secondary-container">
                  {suggestion.has_enough_data
                    ? `Benzer ilan aralığı: ${formatCurrency(suggestion.suggested_min ?? 0)} - ${formatCurrency(
                        suggestion.suggested_max ?? 0
                      )} (${suggestion.comparable_count} emsal)`
                    : suggestion.message}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Portföyü sil"
        description="Bu portföyü kalıcı olarak silmek istediğinize emin misiniz? Bu işlem geri alınamaz."
        isLoading={deleteLoading}
        onConfirm={() => pendingDeleteId && handleDeleteListing(pendingDeleteId)}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}
