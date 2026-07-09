"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { DoorOpen, MapPin, Ruler } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { PublicListing } from "@/lib/types";
import { formatCurrency, formatLocation } from "@/lib/format";
import { Spinner } from "@/components/ui/Spinner";
import { Icon } from "@/components/ui/Icon";

export default function PublicListingPage() {
  const params = useParams<{ id: string }>();
  const [listing, setListing] = useState<PublicListing | null>(null);
  const [activePhoto, setActivePhoto] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await apiFetch<PublicListing>(`/public/listings/${params.id}`);
        setListing(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Portföy bulunamadı");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [params.id]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-2 bg-surface-container text-body-sm text-text-muted">
        <Spinner />
        Yükleniyor...
      </div>
    );
  }

  if (error || !listing) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-surface-container px-6 text-center">
        <Icon name="home_work" className="text-[48px] text-outline" />
        <p className="text-body-sm text-text-muted">{error ?? "Bu portföy artık mevcut değil."}</p>
      </div>
    );
  }

  const currentPhoto = listing.photos[activePhoto];

  return (
    <div className="min-h-screen bg-surface-container">
      <header className="flex items-center gap-2 bg-primary px-6 py-4 text-on-primary">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-mint-accent text-secondary">
          <Icon name="apartment" className="text-[18px]" />
        </div>
        <span className="font-semibold">{listing.office_name}</span>
      </header>

      <main className="mx-auto flex max-w-xl flex-col gap-4 p-4 sm:p-6">
        <div className="relative h-72 w-full overflow-hidden rounded-lg bg-surface-container-lowest sm:h-96">
          {currentPhoto ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={currentPhoto} alt={listing.title} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center text-outline">
              <Icon name="home_work" className="text-[64px]" />
            </div>
          )}
        </div>

        {listing.photos.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {listing.photos.map((photo, i) => (
              <button
                key={photo + i}
                type="button"
                onClick={() => setActivePhoto(i)}
                className={`h-16 w-16 shrink-0 overflow-hidden rounded border-2 transition-colors ${
                  activePhoto === i ? "border-primary" : "border-transparent"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        )}

        <div className="rounded-lg bg-surface-container-lowest p-5 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
          <h1 className="text-headline-lg text-primary">{listing.title}</h1>
          <p className="mt-1 flex items-center gap-1 text-body-sm text-text-muted">
            <MapPin className="h-4 w-4" />
            {formatLocation(listing)}
          </p>
          <p className="mt-3 text-headline-md font-semibold text-primary">
            {formatCurrency(listing.price)}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="flex items-center gap-1 rounded bg-surface-container px-2 py-1 font-label text-label-caps text-on-surface">
              <DoorOpen className="h-3 w-3" />
              {listing.room_count}
            </span>
            {listing.square_meters && (
              <span className="flex items-center gap-1 rounded bg-surface-container px-2 py-1 font-label text-label-caps text-on-surface">
                <Ruler className="h-3 w-3" />
                {listing.square_meters} m²
              </span>
            )}
          </div>
        </div>

        <p className="text-center text-[11px] text-text-muted">
          Bu sayfa {listing.office_name} tarafından PortföyAI ile oluşturuldu.
        </p>
      </main>
    </div>
  );
}
