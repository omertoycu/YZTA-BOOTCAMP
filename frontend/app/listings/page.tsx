"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Building2, Sparkles } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { Listing, PricingSuggestion } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { ListingCard } from "@/components/ListingCard";

export default function ListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pricingByListing, setPricingByListing] = useState<Record<string, PricingSuggestion>>({});
  const [pricingLoading, setPricingLoading] = useState<string | null>(null);

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
    try {
      const data = await apiFetch<Listing[]>("/listings");
      setListings(data);
    } finally {
      setIsLoading(false);
    }
  }

  async function handlePricingSuggestion(listingId: string) {
    setPricingLoading(listingId);
    try {
      const suggestion = await apiFetch<PricingSuggestion>(`/listings/${listingId}/pricing-suggestion`);
      setPricingByListing((prev) => ({ ...prev, [listingId]: suggestion }));
    } finally {
      setPricingLoading(null);
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

      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-16 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      )}

      {!isLoading && listings.length === 0 && (
        <EmptyState
          icon={Building2}
          title="Henüz portföy eklenmedi"
          description="Yukarıdaki 'Yeni İlan Ekle' butonuyla ilk portföyünüzü ekleyin."
        />
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {listings.map((listing) => {
          const suggestion = pricingByListing[listing.id];
          return (
            <div key={listing.id} className="flex flex-col gap-2">
              <ListingCard listing={listing} />
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
    </div>
  );
}
