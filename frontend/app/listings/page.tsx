"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Building2, Link2, MapPin, Plus, Sparkles } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { Listing, ListingExtract, PricingSuggestion } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

export default function ListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pricingByListing, setPricingByListing] = useState<Record<string, PricingSuggestion>>({});
  const [pricingLoading, setPricingLoading] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [district, setDistrict] = useState("");
  const [price, setPrice] = useState("");
  const [roomCount, setRoomCount] = useState("2+1");

  const [sourceUrl, setSourceUrl] = useState("");
  const [isExtracting, setIsExtracting] = useState(false);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföyler yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch("/listings", {
        method: "POST",
        body: JSON.stringify({ title, district, price: Number(price), room_count: roomCount }),
      });
      setTitle("");
      setDistrict("");
      setPrice("");
      await loadListings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföy eklenemedi");
    }
  }

  async function handleExtract() {
    setError(null);
    setIsExtracting(true);
    try {
      const fields = await apiFetch<ListingExtract>("/listings/extract-from-url", {
        method: "POST",
        body: JSON.stringify({ url: sourceUrl }),
      });
      if (fields.title) setTitle(fields.title);
      if (fields.district) setDistrict(fields.district);
      if (fields.price) setPrice(String(fields.price));
      if (fields.room_count) setRoomCount(fields.room_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Linkten bilgi alınamadı, elle doldurabilirsiniz");
    } finally {
      setIsExtracting(false);
    }
  }

  async function handlePricingSuggestion(listingId: string) {
    setPricingLoading(listingId);
    try {
      const suggestion = await apiFetch<PricingSuggestion>(`/listings/${listingId}/pricing-suggestion`);
      setPricingByListing((prev) => ({ ...prev, [listingId]: suggestion }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fiyat önerisi alınamadı");
    } finally {
      setPricingLoading(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Portföyler</h1>
        <p className="mt-1 text-sm text-slate-500">
          Ofisinizin tüm gayrimenkul portföyünü tek yerden yönetin.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Yeni portföy ekle</CardTitle>
          <CardDescription>İlan bilgilerini girip listenize saniyeler içinde ekleyin.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex flex-col gap-2 rounded-lg border border-dashed border-slate-200 bg-slate-50/60 p-4 sm:flex-row sm:items-end">
            <Input
              id="sourceUrl"
              label="Sahibinden linki (opsiyonel)"
              placeholder="https://www.sahibinden.com/ilan/..."
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              className="flex-1"
            />
            <Button
              type="button"
              variant="outline"
              isLoading={isExtracting}
              disabled={!sourceUrl}
              onClick={handleExtract}
            >
              <Link2 className="h-3.5 w-3.5" />
              Doldur
            </Button>
          </div>

          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
            <Input
              id="title"
              label="Başlık"
              required
              placeholder="Örn. Deniz manzaralı 3+1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="lg:col-span-2"
            />
            <Input
              id="district"
              label="Bölge"
              required
              placeholder="Örn. Kadıköy"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
            />
            <Input
              id="price"
              label="Fiyat (TL)"
              required
              type="number"
              placeholder="2500000"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
            <Input
              id="roomCount"
              label="Oda sayısı"
              required
              placeholder="2+1"
              value={roomCount}
              onChange={(e) => setRoomCount(e.target.value)}
            />
            <Button type="submit" className="lg:col-span-5 lg:w-fit">
              <Plus className="h-4 w-4" />
              Portföy ekle
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && <Alert>{error}</Alert>}

      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500">
          <Spinner />
          Yükleniyor...
        </div>
      )}

      {!isLoading && listings.length === 0 && (
        <EmptyState
          icon={Building2}
          title="Henüz portföy eklenmedi"
          description="Yukarıdaki formu kullanarak ilk portföyünüzü ekleyin."
        />
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {listings.map((listing) => {
          const suggestion = pricingByListing[listing.id];
          return (
            <Card key={listing.id} className="flex flex-col">
              <CardHeader className="flex-row items-start justify-between gap-2 space-y-0">
                <div className="flex flex-col gap-1">
                  <CardTitle>{listing.title}</CardTitle>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge variant="neutral">
                      <MapPin className="h-3 w-3" />
                      {listing.district}
                    </Badge>
                    <Badge variant="brand">{listing.room_count}</Badge>
                    {listing.status && (
                      <Badge variant={listing.status === "active" ? "success" : "neutral"}>
                        {listing.status === "active" ? "Aktif" : listing.status}
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col gap-4">
                <p className="text-2xl font-semibold text-slate-900">{formatCurrency(listing.price)}</p>

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
                  <div className="rounded-lg bg-brand-50 px-3 py-2.5 text-sm text-brand-800">
                    {suggestion.has_enough_data
                      ? `Benzer ilan aralığı: ${formatCurrency(suggestion.suggested_min ?? 0)} - ${formatCurrency(
                          suggestion.suggested_max ?? 0
                        )} (${suggestion.comparable_count} emsal)`
                      : suggestion.message}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
