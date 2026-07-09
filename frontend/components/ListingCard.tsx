"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import type { Listing, PropertyType } from "@/lib/types";
import { formatCurrency, formatLocation } from "@/lib/format";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";

// Emlak tipine göre ayırt edici ikon — arsa/tarla gibi arazi portföyleri
// bina ikonuyla gösterilmez (gerçek kullanıcı geri bildirimi).
const PROPERTY_TYPE_VISUALS: Record<
  PropertyType,
  { icon: string; label: string; chipClass: string }
> = {
  residential: { icon: "apartment", label: "Konut", chipClass: "bg-mint-accent text-secondary" },
  commercial: { icon: "storefront", label: "İş Yeri", chipClass: "bg-tertiary-fixed text-on-tertiary-container" },
  land: { icon: "landscape", label: "Arsa / Arazi", chipClass: "bg-[#E8F0E3] text-[#3E6B2F]" },
};

function InfoChip({ icon, children }: { icon?: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex h-7 items-center gap-1 rounded-full bg-surface-container px-2.5 text-[12px] font-medium leading-none text-on-surface-variant">
      {icon && <Icon name={icon} className="!text-[14px]" />}
      {children}
    </span>
  );
}

export function ListingCard({ listing, onDelete }: { listing: Listing; onDelete?: () => void }) {
  const [coverFailed, setCoverFailed] = useState(false);
  const cover = !coverFailed ? listing.photos[0] : undefined;
  const visuals = PROPERTY_TYPE_VISUALS[listing.property_type] ?? PROPERTY_TYPE_VISUALS.residential;
  const isLand = listing.property_type === "land";

  return (
    <div className="flex flex-col rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] transition-shadow duration-300 hover:shadow-[0px_15px_40px_rgba(0,0,0,0.08)]">
      <div className="mb-3 flex items-start justify-between gap-2 px-1">
        <div className="flex min-w-0 items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
              visuals.chipClass
            )}
            title={visuals.label}
          >
            <Icon name={visuals.icon} />
          </div>
          <div className="min-w-0">
            <h3 className="truncate text-[16px] font-semibold leading-snug text-primary" title={listing.title}>
              {listing.title}
            </h3>
            <p className="truncate text-[12px] leading-tight text-text-muted" title={formatLocation(listing)}>
              {formatLocation(listing)} · {visuals.label}
            </p>
          </div>
        </div>
        {onDelete && (
          <button
            type="button"
            onClick={onDelete}
            aria-label="Portföyü sil"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-error/10 hover:text-error"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-1.5 px-1">
        <span
          className={cn(
            "inline-flex h-7 items-center rounded-full px-2.5 text-[12px] font-semibold leading-none",
            listing.listing_type === "rent"
              ? "bg-secondary-container text-on-secondary-container"
              : "bg-primary text-on-primary"
          )}
        >
          {listing.listing_type === "rent" ? "Kiralık" : "Satılık"}
        </span>
        {listing.square_meters && <InfoChip icon="square_foot">{listing.square_meters} m²</InfoChip>}
        {!isLand && listing.room_count && <InfoChip icon="bed">{listing.room_count}</InfoChip>}
        {listing.status === "active" && (
          <InfoChip>
            <span className="mr-0.5 inline-block h-1.5 w-1.5 rounded-full bg-secondary" />
            Aktif
          </InfoChip>
        )}
      </div>

      <div className="relative mt-auto h-48 w-full overflow-hidden rounded">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover}
            alt={listing.title}
            className="h-full w-full object-cover"
            onError={() => setCoverFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-surface-container text-outline">
            <Icon name={isLand ? "landscape" : "home_work"} className="text-[40px]" />
          </div>
        )}
        <p className="absolute left-3 top-3 rounded-full bg-primary/80 px-3 py-1 text-[13px] font-semibold text-on-primary">
          {formatCurrency(listing.price)}
          {listing.listing_type === "rent" ? " / ay" : ""}
        </p>
        <Link
          href={`/listings/${listing.id}`}
          className="absolute bottom-3 right-3 rounded-full bg-primary px-4 py-2 font-label text-label-caps text-on-primary shadow-lg transition-transform hover:scale-105"
        >
          İncele
        </Link>
      </div>
    </div>
  );
}
