"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Ruler, DoorOpen, MapPin, Sparkles, CalendarDays, Eye, Link2, Check, Trash2, Pencil, X, Plus } from "lucide-react";
import { apiFetch, apiUpload, getToken } from "@/lib/api";
import type { Listing, ListingViewStats, MarketPriceCheck, PropertyType } from "@/lib/types";
import { formatCurrency, formatLocation } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ListingTypeToggle } from "@/components/ui/ListingTypeToggle";
import { PropertyTypeSelect } from "@/components/ui/PropertyTypeSelect";
import { LocationAutocomplete } from "@/components/ui/LocationAutocomplete";

const MAX_PHOTO_BYTES = 8 * 1024 * 1024; // 8MB, backend ile aynı sınır

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

  const [marketCheck, setMarketCheck] = useState<MarketPriceCheck | null>(null);
  const [marketCheckLoading, setMarketCheckLoading] = useState(false);
  const [marketCheckError, setMarketCheckError] = useState<string | null>(null);

  const [viewStats, setViewStats] = useState<ListingViewStats | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const [isEditing, setIsEditing] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editDistrict, setEditDistrict] = useState("");
  const [editNeighborhood, setEditNeighborhood] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [editRoomCount, setEditRoomCount] = useState("");
  const [editSquareMeters, setEditSquareMeters] = useState("");

  const [photoUploading, setPhotoUploading] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [deletingPhotoIndex, setDeletingPhotoIndex] = useState<number | null>(null);

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

  async function handleMarketCheck() {
    if (!listing) return;
    setMarketCheckLoading(true);
    setMarketCheckError(null);
    try {
      const result = await apiFetch<MarketPriceCheck>(`/listings/${listing.id}/market-price-check`);
      setMarketCheck(result);
    } catch (err) {
      setMarketCheckError(err instanceof Error ? err.message : "Piyasa verisi alınamadı");
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

  function startEditing() {
    if (!listing) return;
    setEditTitle(listing.title);
    setEditCity(listing.city ?? "");
    setEditDistrict(listing.district);
    setEditNeighborhood(listing.neighborhood ?? "");
    setEditPrice(String(listing.price));
    setEditRoomCount(listing.room_count);
    setEditSquareMeters(listing.square_meters ? String(listing.square_meters) : "");
    setEditError(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    setIsEditing(false);
    setEditError(null);
  }

  async function handleSaveEdit() {
    if (!listing) return;
    const parsedPrice = Number(editPrice);
    if (
      !editTitle.trim() ||
      !editDistrict.trim() ||
      !editRoomCount.trim() ||
      !Number.isFinite(parsedPrice) ||
      parsedPrice <= 0
    ) {
      setEditError("Lütfen başlık, ilçe, oda sayısı ve geçerli bir fiyat girin.");
      return;
    }
    setEditSaving(true);
    setEditError(null);
    try {
      const updated = await apiFetch<Listing>(`/listings/${listing.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: editTitle.trim(),
          city: editCity.trim() || null,
          district: editDistrict.trim(),
          neighborhood: editNeighborhood.trim() || null,
          price: parsedPrice,
          room_count: editRoomCount.trim(),
          square_meters: editSquareMeters.trim() ? Number(editSquareMeters) : null,
        }),
      });
      setListing(updated);
      setIsEditing(false);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Portföy güncellenemedi");
    } finally {
      setEditSaving(false);
    }
  }

  async function handleAddPhotos(e: React.ChangeEvent<HTMLInputElement>) {
    if (!listing) return;
    const files = Array.from(e.target.files ?? []);
    e.target.value = "";
    if (files.length === 0) return;

    const accepted: File[] = [];
    const rejected: string[] = [];
    for (const file of files) {
      if (!file.type.startsWith("image/")) {
        rejected.push(`${file.name} (desteklenmeyen dosya türü)`);
      } else if (file.size > MAX_PHOTO_BYTES) {
        rejected.push(`${file.name} (8MB sınırını aşıyor)`);
      } else {
        accepted.push(file);
      }
    }

    setPhotoUploading(true);
    setPhotoError(rejected.length > 0 ? `Eklenemeyen fotoğraflar: ${rejected.join(", ")}` : null);
    const failed: string[] = [];
    let current = listing;
    for (const file of accepted) {
      try {
        current = await apiUpload<Listing>(`/listings/${current.id}/photos`, file);
      } catch {
        failed.push(file.name);
      }
    }
    setListing(current);
    if (failed.length > 0) {
      setPhotoError((prev) => {
        const message = `Yüklenemeyen fotoğraflar: ${failed.join(", ")}`;
        return prev ? `${prev} ${message}` : message;
      });
    }
    setPhotoUploading(false);
  }

  async function handleDeletePhoto(index: number) {
    if (!listing) return;
    setDeletingPhotoIndex(index);
    setPhotoError(null);
    try {
      const updated = await apiFetch<Listing>(`/listings/${listing.id}/photos/${index}`, { method: "DELETE" });
      setListing(updated);
      setPhotoFailed({});
      setActivePhoto((prev) => Math.min(prev, Math.max(updated.photos.length - 1, 0)));
    } catch (err) {
      setPhotoError(err instanceof Error ? err.message : "Fotoğraf silinemedi");
    } finally {
      setDeletingPhotoIndex(null);
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
            {showCurrent && (
              <button
                type="button"
                onClick={() => handleDeletePhoto(activePhoto)}
                disabled={deletingPhotoIndex !== null}
                aria-label="Fotoğrafı sil"
                className="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80 disabled:opacity-50"
              >
                {deletingPhotoIndex === activePhoto ? <Spinner /> : <Trash2 className="h-4 w-4" />}
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {listing.photos.map((photo, i) =>
              photoFailed[i] ? null : (
                <div key={photo + i} className="group relative shrink-0">
                  <button
                    type="button"
                    onClick={() => setActivePhoto(i)}
                    className={`h-16 w-16 overflow-hidden rounded border-2 transition-colors ${
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
                  <button
                    type="button"
                    onClick={() => handleDeletePhoto(i)}
                    disabled={deletingPhotoIndex !== null}
                    aria-label="Fotoğrafı sil"
                    className="absolute right-0.5 top-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity group-hover:opacity-100 disabled:opacity-50"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )
            )}
            <label className="flex h-16 w-16 shrink-0 cursor-pointer flex-col items-center justify-center gap-0.5 rounded border-2 border-dashed border-outline-variant text-text-muted hover:bg-surface-bright">
              {photoUploading ? (
                <Spinner />
              ) : (
                <>
                  <Plus className="h-4 w-4" />
                  <span className="text-[10px]">Ekle</span>
                </>
              )}
              <input
                type="file"
                accept="image/*"
                multiple
                disabled={photoUploading}
                className="hidden"
                onChange={handleAddPhotos}
              />
            </label>
          </div>
          {photoError && <Alert>{photoError}</Alert>}
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
              {!isEditing && (
                <Button variant="outline" size="sm" onClick={startEditing}>
                  <Pencil className="h-3.5 w-3.5" />
                  Düzenle
                </Button>
              )}
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
            {!isEditing && (
              <>
                <h1 className="text-headline-lg text-primary">{listing.title}</h1>
                <p className="mt-1 flex items-center gap-1 text-body-sm text-text-muted">
                  <MapPin className="h-4 w-4" />
                  {formatLocation(listing)}
                </p>
              </>
            )}
          </div>

          {isEditing ? (
            <div className="flex flex-col gap-3 rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
              <h2 className="text-title-md text-primary">Portföyü düzenle</h2>
              <Input id="editTitle" label="Başlık" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
              <LocationAutocomplete
                id="editCity"
                label="Şehir"
                value={editCity}
                onChange={(value) => {
                  setEditCity(value);
                  setEditDistrict("");
                  setEditNeighborhood("");
                }}
                endpoint="/geo/cities"
                placeholder="Örn. İstanbul"
              />
              <LocationAutocomplete
                id="editDistrict"
                label="İlçe"
                value={editDistrict}
                onChange={(value) => {
                  setEditDistrict(value);
                  setEditNeighborhood("");
                }}
                endpoint="/geo/districts"
                params={editCity.trim() ? { city: editCity.trim() } : {}}
                placeholder={editCity.trim() ? "Örn. Kadıköy" : "Önce şehir seçin"}
              />
              <LocationAutocomplete
                id="editNeighborhood"
                label="Mahalle (opsiyonel)"
                value={editNeighborhood}
                onChange={setEditNeighborhood}
                endpoint="/geo/neighborhoods"
                params={{
                  ...(editCity.trim() ? { city: editCity.trim() } : {}),
                  ...(editDistrict.trim() ? { district: editDistrict.trim() } : {}),
                }}
                placeholder={editDistrict.trim() ? "Örn. Caferağa" : "Önce ilçe seçin"}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  id="editPrice"
                  label={listing.listing_type === "rent" ? "Aylık kira (TL)" : "Satış fiyatı (TL)"}
                  type="number"
                  value={editPrice}
                  onChange={(e) => setEditPrice(e.target.value)}
                />
                <Input
                  id="editRoomCount"
                  label="Oda sayısı"
                  value={editRoomCount}
                  onChange={(e) => setEditRoomCount(e.target.value)}
                />
              </div>
              <Input
                id="editSquareMeters"
                label="Metrekare (opsiyonel)"
                type="number"
                value={editSquareMeters}
                onChange={(e) => setEditSquareMeters(e.target.value)}
              />
              {editError && <Alert>{editError}</Alert>}
              <div className="flex items-center gap-2">
                <Button size="sm" isLoading={editSaving} onClick={handleSaveEdit}>
                  <Check className="h-3.5 w-3.5" />
                  Kaydet
                </Button>
                <Button variant="ghost" size="sm" onClick={cancelEditing} disabled={editSaving}>
                  <X className="h-3.5 w-3.5" />
                  Vazgeç
                </Button>
              </div>
            </div>
          ) : (
            <>
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
            </>
          )}

          <div className="flex flex-col gap-3 rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-title-md text-primary">Fiyat Önerisi</h2>
                <p className="text-[12px] text-text-muted">
                  Bölgedeki güncel emsal ilanlar taranır, tahmini bir piyasa aralığı sunulur.
                </p>
              </div>
              <Button variant="outline" size="sm" isLoading={marketCheckLoading} onClick={handleMarketCheck}>
                <Sparkles className="h-3.5 w-3.5" />
                Öneri Al
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
                    : marketCheck.summary ?? "Güvenilir bir emsal bulunamadı."}
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
                  Güncel piyasa verilerine dayalı tahmindir, kesin değerleme değildir.
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
