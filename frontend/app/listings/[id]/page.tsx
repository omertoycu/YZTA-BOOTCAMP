"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Ruler, DoorOpen, MapPin, Sparkles, CalendarDays } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { Listing, PricingSuggestion } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { Icon } from "@/components/ui/Icon";

export default function ListingDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [listing, setListing] = useState<Listing | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePhoto, setActivePhoto] = useState(0);
  const [photoFailed, setPhotoFailed] = useState<Record<number, boolean>>({});

  const [pricing, setPricing] = useState<PricingSuggestion | null>(null);
  const [pricingLoading, setPricingLoading] = useState(false);
  const [pricingError, setPricingError] = useState<string | null>(null);

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
      const data = await apiFetch<Listing>(`/listings/${params.id}`);
      setListing(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföy yüklenemedi");
    } finally {
      setIsLoading(false);
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
              {listing.status === "active" && <Badge variant="brand">Aktif</Badge>}
              <Badge variant="neutral">
                <CalendarDays className="h-3 w-3" />
                {new Date(listing.created_at).toLocaleDateString("tr-TR")}
              </Badge>
            </div>
            <h1 className="text-headline-lg text-primary">{listing.title}</h1>
            <p className="mt-1 flex items-center gap-1 text-body-sm text-text-muted">
              <MapPin className="h-4 w-4" />
              {listing.district}
            </p>
          </div>

          <p className="text-headline-md font-semibold text-primary">{formatCurrency(listing.price)}</p>

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
          </div>

          <div className="flex flex-col gap-2 rounded-lg border border-dashed border-outline-variant p-4 text-body-sm text-text-muted">
            <span className="flex items-center gap-2 font-medium text-on-surface">
              <Icon name="directions" />
              Markalı Ulaşım/Konum Raporu
            </span>
            Yakında: adaya bu ilana ulaşım sürelerini gösteren PDF rapor gönderebileceksiniz.
          </div>
        </div>
      </div>
    </div>
  );
}
