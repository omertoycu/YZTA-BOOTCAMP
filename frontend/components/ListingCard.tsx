"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import type { Listing } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Icon } from "@/components/ui/Icon";

export function ListingCard({ listing, onDelete }: { listing: Listing; onDelete?: () => void }) {
  const [coverFailed, setCoverFailed] = useState(false);
  const cover = !coverFailed ? listing.photos[0] : undefined;

  return (
    <div className="flex flex-col rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] transition-shadow duration-300 hover:shadow-[0px_15px_40px_rgba(0,0,0,0.08)]">
      <div className="mb-4 flex items-start justify-between px-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-mint-accent text-secondary">
            <Icon name="apartment" />
          </div>
          <div>
            <h3 className="text-title-md leading-tight text-primary">{listing.title}</h3>
            <p className="text-[12px] text-text-muted">{listing.district}</p>
          </div>
        </div>
        {onDelete && (
          <button
            type="button"
            onClick={onDelete}
            aria-label="Portföyü sil"
            className="flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-error/10 hover:text-error"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="mb-4 flex flex-wrap gap-2 px-2">
        {listing.square_meters && (
          <span className="rounded bg-surface-container px-2 py-1 font-label text-label-caps text-on-surface">
            {listing.square_meters} m²
          </span>
        )}
        <span className="rounded bg-surface-container px-2 py-1 font-label text-label-caps text-on-surface">
          {listing.room_count}
        </span>
        {listing.status === "active" && (
          <span className="rounded bg-mint-accent px-2 py-1 font-label text-label-caps text-on-secondary-container">
            Aktif
          </span>
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
            <Icon name="home_work" className="text-[40px]" />
          </div>
        )}
        <p className="absolute left-3 top-3 rounded-full bg-primary/80 px-3 py-1 text-[13px] font-semibold text-on-primary">
          {formatCurrency(listing.price)}
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
