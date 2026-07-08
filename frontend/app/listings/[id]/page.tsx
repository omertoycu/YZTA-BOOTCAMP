"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Ruler, DoorOpen, MapPin, Sparkles, CalendarDays, Eye, Link2, Check, Trash2, Globe } from "lucide-react";
import { apiFetch, apiFetchBlob, getToken } from "@/lib/api";
import type { Listing, ListingViewStats, MarketPriceCheck, PricingSuggestion, PropertyType } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ListingTypeToggle } from "@/components/ui/ListingTypeToggle";
import { PropertyTypeSelect } from "@/components/ui/PropertyTypeSelect";

export default function ListingDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [listing, setListing] = useState<Listing | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePhoto, setActivePhoto] = useState(0);
  const [photoFailed, setPhotoFailed] = useState<Record<number, boolean>>({});

  const LISTING_STATUS_LABELS: Record<string, string> = {
    active: "Aktif",
    optioned: "Opsiyonlu",
    sold: "Satıldı",
  };

  const [pricing, setPricing] = useState<PricingSuggestion | null>(null);
  const [pricingLoading, setPricingLoading] = useState(false);
  const [pricingError, setPricingError] = useState<string | null>(null);

  const [marketCheck, setMarketCheck] = useState<MarketPriceCheck | null>(null);
  const [marketCheckLoading, setMarketCheckLoading] = useState(false);
  const [marketCheckError, setMarketCheckError] = useState<string | null>(null);

  const [targetAddress, setTargetAddress] = useState("");
  const [targetLabel, setTargetLabel] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  const [viewStats, setViewStats] = useState<ListingViewStats | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    loadListing();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  async function loadListing() {
    setIsLoading(true);
    setError(null);
    try {
      const [data, stats] = await Promise.all([
        apiFetch<Listing>(`/listings/${params.id}`),
        apiFetch<ListingViewStats>(`/listings/${params.id}/view-stats`),
      ]);
      setListing(data);
      setViewStats(stats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföy yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCopyShareLink() {
    if (!listing) return;
    const url = `${window.location.origin}/p/${listing.id}`;
    await navigator.clipboard.writeText(url);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  }

  async function handleStatusChange(status: string) {
    if (!listing) return;
    setError(null);
    try {
      const updated = await apiFetch<Listing>(`/listings/${listing.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setListing(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Durum güncellenemedi");
    }
  }

  async function handleTypeChange(listingType: "sale" | "rent") {
    if (!listing || listing.listing_type === listingType) return;
    setError(null);
    try {
      const updated = await apiFetch<Listing>(`/listings/${listing.id}/type`, {
        method: "PATCH",
        body: JSON.stringify({ listing_type: listingType }),
      });
      setListing(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "İlan tipi güncellenemedi");
    }
  }

  async function handlePropertyTypeChange(propertyType: PropertyType) {
    if (!listing || listing.property_type === propertyType) return;
    setError(null);
    try {
      const updated = await apiFetch<Listing>(`/listings/${listing.id}/property-type`, {
        method: "PATCH",
        body: JSON.stringify({ property_type: propertyType }),
      });
      setListing(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Emlak tipi güncellenemedi");
    }
  }

  async function handlePricingSuggestion() {
    if (!listing) return;
    setPricingLoading(true);
    setPricingError(null);
    try {
      const suggestion = await apiFetch<PricingSuggestion>(`/listings/${listing.id}/pricing-suggestion`);
      setPricing(suggestion);
    } catch (err) {
      setPricingError(err instanceof Error ? err.message : "Fiyat önerisi alınamadı");
    } finally {
      setPricingLoading(false);
    }
  }

  async function handleMarketCheck() {
    if (!listing) return;
    setMarketCheckLoading(true);
    setMarketCheckError(null);
    try {
      const result = await apiFetch<MarketPriceCheck>(`/listings/${listing.id}/market-price-check`);
      setMarketCheck(result);
    } catch (err) {
      setMarketCheckError(err instanceof Error ? err.message : "Web'den piyasa verisi alınamadı");
    } finally {
      setMarketCheckLoading(false);
    }
  }

  async function handleDeleteListing() {
    if (!listing) return;
    setError(null);
    setDeleteLoading(true);
    try {
      await apiFetch(`/listings/${listing.id}`, { method: "DELETE" });
      router.push("/listings");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföy silinemedi");
      setDeleteLoading(false);
      setConfirmDeleteOpen(false);
    }
  }

  async function handleGenerateReport() {
    if (!listing || !targetAddress.trim()) return;
    setReportLoading(true);
    setReportError(null);
    try {
      const blob = await apiFetchBlob(`/listings/${listing.id}/location-report`, {
        method: "POST",
        body: JSON.stringify({ target_address: targetAddress, target_label: targetLabel || null }),
      });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch (err) {
      setReportError(err instanceof Error ? err.message : "Rapor oluşturulamadı");
    } finally {
      setReportLoading(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-24 text-body-sm text-text-muted">
        <Spinner />
        Yükleniyor...
      </div>
    );
  }

  if (error || !listing) {
    return (
      <div className="flex flex-col gap-4">
        <Link href="/listings" className="inline-flex w-fit items-center gap-1 text-body-sm text-text-muted hover:text-primary">
          <ArrowLeft className="h-4 w-4" />
          Portföylere dön
        </Link>
        <Alert>{error ?? "Portföy bulunamadı"}</Alert>
      </div>
    );
  }

  const validPhotos = listing.photos.filter((_, i) => !photoFailed[i]);
  const currentSrc = listing.photos[activePhoto];
  const showCurrent = currentSrc && !photoFailed[activePhoto];

  return (
    <div className="flex flex-col gap-6">
      <Link href="/listings" className="inline-flex w-fit items-center gap-1 text-body-sm text-text-muted hover:text-primary">
        <ArrowLeft className="h-4 w-4" />
        Portföylere dön
      </Link>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="flex flex-col gap-3 lg:col-span-3">
          <div className="relative h-80 w-full overflow-hidden rounded-lg bg-surface-container sm:h-96">
            {showCurrent ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={currentSrc}
                alt={listing.title}
                className="h-full w-full object-cover"
                onError={() => setPhotoFailed((prev) => ({ ...prev, [activePhoto]: true }))}
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-outline">
                <Icon name="home_work" className="text-[64px]" />
              </div>
            )}
          </div>

          {listing.photos.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {listing.photos.map((photo, i) =>
                photoFailed[i] ? null : (
                  <button
                    key={photo + i}
                    type="button"
                    onClick={() => setActivePhoto(i)}
                    className={`h-16 w-16 shrink-0 overflow-hidden rounded border-2 transition-colors ${
                      activePhoto === i ? "border-primary" : "border-transparent"
                    }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photo}
                      alt=""
                      className="h-full w-full object-cover"
                      onError={() => setPhotoFailed((prev) => ({ ...prev, [i]: true }))}
                    />
                  </button>
                )
              )}
            </div>
          )}
          {listing.photos.length > 0 && validPhotos.length === 0 && (
            <p className="text-body-sm text-text-muted">
              Bu portföyün fotoğrafları şu an yüklenemiyor. Depolama servisinin erişim ayarları kontrol edilmeli.
            </p>
          )}
        </div>

        <div className="flex flex-col gap-4 lg:col-span-2">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant={listing.status === "active" ? "brand" : listing.status === "sold" ? "success" : "warning"}>
                {LISTING_STATUS_LABELS[listing.status] ?? listing.status}
              </Badge>
              <ListingTypeToggle value={listing.listing_type} onChange={handleTypeChange} />
              <PropertyTypeSelect value={listing.property_type} onChange={handlePropertyTypeChange} />
              <Badge variant="neutral">
                <CalendarDays className="h-3 w-3" />
                {new Date(listing.created_at).toLocaleDateString("tr-TR")}
              </Badge>
              <select
                value={listing.status}
                onChange={(e) => handleStatusChange(e.target.value)}
                aria-label="Portföy durumu"
                className="rounded border border-outline-variant bg-surface-container-lowest px-2 py-1 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
              >
                {Object.entries(LISTING_STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <Button variant="destructive" size="sm" onClick={() => setConfirmDeleteOpen(true)}>
                <Trash2 className="h-3.5 w-3.5" />
                Sil
              </Button>
            </div>
            {listing.status !== "active" && (
              <p className="mb-2 text-body-sm text-text-muted">
                Bu portföy eşleştirmelere dahil edilmiyor; emsal verisi ve raporlar için tarihçede kalır.
              </p>
            )}
            <h1 className="text-headline-lg text-primary">{listing.title}</h1>
            <p className="mt-1 flex items-center gap-1 text-body-sm text-text-muted">
              <MapPin className="h-4 w-4" />
              {listing.district}
            </p>
          </div>

          <p className="text-headline-md font-semibold text-primary">
            {formatCurrency(listing.price)}
            {listing.listing_type === "rent" && <span className="text-body-lg text-text-muted"> / ay</span>}
          </p>

          <div className="flex flex-wrap gap-2">
            <Badge variant="neutral">
              <DoorOpen className="h-3 w-3" />
              {listing.room_count}
            </Badge>
            {listing.square_meters && (
              <Badge variant="neutral">
                <Ruler className="h-3 w-3" />
                {listing.square_meters} m²
              </Badge>
            )}
          </div>

          <div className="flex flex-col gap-3 rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
            <div className="flex items-center justify-between">
              <h2 className="text-title-md text-primary">Fiyat önerisi</h2>
              <Button variant="outline" size="sm" isLoading={pricingLoading} onClick={handlePricingSuggestion}>
                <Sparkles className="h-3.5 w-3.5" />
                Hesapla
              </Button>
            </div>
            {pricingError && <Alert>{pricingError}</Alert>}
            {pricing && (
              <p className="text-body-sm text-text-muted">
                {pricing.has_enough_data
                  ? `Benzer ilan aralığı: ${formatCurrency(pricing.suggested_min ?? 0)} - ${formatCurrency(
                      pricing.suggested_max ?? 0
                    )} (${pricing.comparable_count} emsal)`
                  : pricing.message}
              </p>
            )}

            <div className="flex items-center justify-between border-t border-outline-variant pt-3">
              <div>
                <h3 className="text-body-md font-medium text-on-surface">Web'den karşılaştır</h3>
                <p className="text-[12px] text-text-muted">
                  Gemini, aynı konum/tipteki güncel ilanları web'de araştırıp bir aralık önerir.
                </p>
              </div>
              <Button variant="outline" size="sm" isLoading={marketCheckLoading} onClick={handleMarketCheck}>
                <Globe className="h-3.5 w-3.5" />
                Web'den Karşılaştır
              </Button>
            </div>
            {marketCheckError && <Alert>{marketCheckError}</Alert>}
            {marketCheck && (
              <div className="flex flex-col gap-1.5">
                <p className="text-body-sm text-text-muted">
                  {marketCheck.has_market_data
                    ? `Tahmini piyasa aralığı: ${formatCurrency(marketCheck.estimated_min ?? 0)} - ${formatCurrency(
                        marketCheck.estimated_max ?? 0
                      )}`
                    : marketCheck.summary ?? "Web'de güvenilir bir emsal bulunamadı."}
                </p>
                {marketCheck.has_market_data && marketCheck.summary && (
                  <p className="text-[12px] text-text-muted">{marketCheck.summary}</p>
                )}
                {marketCheck.sources.length > 0 && (
                  <div className="flex flex-wrap gap-x-3 gap-y-1">
                    {marketCheck.sources.map((source) => (
                      <a
                        key={source.url}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[12px] text-secondary underline hover:text-primary"
                      >
                        {source.title}
                      </a>
                    ))}
                  </div>
                )}
                <p className="text-[11px] text-text-muted">
                  AI tahmini — harici web kaynaklarından, kesin değildir.
                </p>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-3 rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
            <div className="flex items-center justify-between">
              <h2 className="text-title-md text-primary">İlan Vitrini</h2>
              <Button variant="outline" size="sm" onClick={handleCopyShareLink}>
                {linkCopied ? <Check className="h-3.5 w-3.5" /> : <Link2 className="h-3.5 w-3.5" />}
                {linkCopied ? "Kopyalandı" : "Linki Kopyala"}
              </Button>
            </div>
            <p className="text-body-sm text-text-muted">
              Login gerektirmeyen markalı bir sayfa oluşturur; adaya WhatsApp&apos;tan bu linki
              atabilirsiniz.
            </p>
            {viewStats && (
              <Badge variant="brand" className="w-fit">
                <Eye className="h-3 w-3" />
                {viewStats.view_count} görüntülenme
                {viewStats.last_viewed_at
                  ? ` · son: ${new Date(viewStats.last_viewed_at).toLocaleDateString("tr-TR")}`
                  : ""}
              </Badge>
            )}
          </div>

          <div className="flex flex-col gap-3 rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
            <span className="flex items-center gap-2 font-medium text-on-surface">
              <Icon name="directions" />
              Markalı Ulaşım/Konum Raporu
            </span>
            <p className="text-body-sm text-text-muted">
              Adayın önem verdiği bir adresi (iş yeri, metro istasyonu vb.) girin; bu ilana araçla,
              yürüyerek ve toplu taşımayla ulaşım sürelerini gösteren bir PDF oluşturulsun.
            </p>
            <Input
              id="targetAddress"
              label="Hedef adres"
              placeholder="Örn. Levent, İstanbul"
              value={targetAddress}
              onChange={(e) => setTargetAddress(e.target.value)}
            />
            <Input
              id="targetLabel"
              label="Etiket (opsiyonel)"
              placeholder="Örn. İş yeri"
              value={targetLabel}
              onChange={(e) => setTargetLabel(e.target.value)}
            />
            {reportError && <Alert>{reportError}</Alert>}
            <Button
              variant="outline"
              size="sm"
              className="w-fit"
              isLoading={reportLoading}
              disabled={!targetAddress.trim()}
              onClick={handleGenerateReport}
            >
              <Icon name="picture_as_pdf" className="text-[16px]" />
              Rapor Oluştur
            </Button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDeleteOpen}
        title="Portföyü sil"
        description="Bu portföyü kalıcı olarak silmek istediğinize emin misiniz? Bu işlem geri alınamaz."
        isLoading={deleteLoading}
        onConfirm={handleDeleteListing}
        onCancel={() => setConfirmDeleteOpen(false)}
      />
    </div>
  );
}
