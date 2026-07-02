"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getToken } from "@/lib/api";
import type { Listing, PricingSuggestion } from "@/lib/types";

export default function ListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pricingByListing, setPricingByListing] = useState<Record<string, PricingSuggestion>>({});

  const [title, setTitle] = useState("");
  const [district, setDistrict] = useState("");
  const [price, setPrice] = useState("");
  const [roomCount, setRoomCount] = useState("2+1");

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

  async function handlePricingSuggestion(listingId: string) {
    try {
      const suggestion = await apiFetch<PricingSuggestion>(`/listings/${listingId}/pricing-suggestion`);
      setPricingByListing((prev) => ({ ...prev, [listingId]: suggestion }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fiyat önerisi alınamadı");
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Portföyler</h1>

      <form onSubmit={handleCreate} className="mb-8 flex flex-wrap items-end gap-3 rounded border border-gray-200 p-4">
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Başlık</label>
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Bölge</label>
          <input
            required
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Fiyat (TL)</label>
          <input
            required
            type="number"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-32 rounded border border-gray-300 px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Oda sayısı</label>
          <input
            required
            value={roomCount}
            onChange={(e) => setRoomCount(e.target.value)}
            className="w-24 rounded border border-gray-300 px-2 py-1"
          />
        </div>
        <button type="submit" className="rounded bg-gray-900 px-3 py-1.5 text-white">
          Ekle
        </button>
      </form>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {isLoading && <p className="text-sm text-gray-500">Yükleniyor...</p>}

      <div className="flex flex-col gap-3">
        {listings.map((listing) => {
          const suggestion = pricingByListing[listing.id];
          return (
            <div key={listing.id} className="rounded border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{listing.title}</p>
                  <p className="text-sm text-gray-500">
                    {listing.district} · {listing.room_count} · {listing.price.toLocaleString("tr-TR")} TL
                  </p>
                </div>
                <button
                  onClick={() => handlePricingSuggestion(listing.id)}
                  className="text-sm text-gray-500 underline hover:text-gray-900"
                >
                  Fiyat önerisi
                </button>
              </div>
              {suggestion && (
                <p className="mt-2 text-sm text-gray-600">
                  {suggestion.has_enough_data
                    ? `Benzer ilan aralığı: ${suggestion.suggested_min?.toLocaleString("tr-TR")} - ${suggestion.suggested_max?.toLocaleString("tr-TR")} TL (${suggestion.comparable_count} emsal)`
                    : suggestion.message}
                </p>
              )}
            </div>
          );
        })}
        {!isLoading && listings.length === 0 && (
          <p className="text-sm text-gray-500">Henüz portföy eklenmedi.</p>
        )}
      </div>
    </div>
  );
}
