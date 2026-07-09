"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { apiFetch, apiUpload, getToken } from "@/lib/api";
import type { Listing, ListingType, PropertyType } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Icon } from "@/components/ui/Icon";
import { ListingTypeToggle } from "@/components/ui/ListingTypeToggle";
import { PropertyTypeSelect } from "@/components/ui/PropertyTypeSelect";
import { LocationAutocomplete } from "@/components/ui/LocationAutocomplete";
import { cn } from "@/lib/utils";

const TOTAL_STEPS = 5;
const MAX_PHOTO_BYTES = 8 * 1024 * 1024; // 8MB, backend ile aynı sınır

export default function NewListingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [title, setTitle] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [neighborhood, setNeighborhood] = useState("");
  const [price, setPrice] = useState("");
  const [roomCount, setRoomCount] = useState("2+1");
  const [squareMeters, setSquareMeters] = useState("");
  const [listingType, setListingType] = useState<ListingType>("sale");
  const [propertyType, setPropertyType] = useState<PropertyType>("residential");
  const [photos, setPhotos] = useState<File[]>([]);
  const [photoPreviewUrls, setPhotoPreviewUrls] = useState<string[]>([]);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    const urls = photos.map((file) => URL.createObjectURL(file));
    setPhotoPreviewUrls(urls);
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, [photos]);

  function goNext() {
    setError(null);
    setStep((s) => Math.min(s + 1, TOTAL_STEPS));
  }

  function goBack() {
    setError(null);
    setStep((s) => Math.max(s - 1, 1));
  }

  const parsedPrice = Number(price);
  const isPriceValid = price.trim() !== "" && Number.isFinite(parsedPrice) && parsedPrice > 0;

  function handlePhotoSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
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
    setPhotos((prev) => [...prev, ...accepted]);
    setError(rejected.length > 0 ? `Eklenemeyen fotoğraflar: ${rejected.join(", ")}` : null);
    e.target.value = "";
  }

  function removePhoto(index: number) {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSave() {
    setError(null);
    setIsSaving(true);
    try {
      const listing = await apiFetch<Listing>("/listings", {
        method: "POST",
        body: JSON.stringify({
          title,
          city: city.trim() || null,
          district,
          neighborhood: neighborhood.trim() || null,
          price: Number(price),
          room_count: roomCount,
          square_meters: squareMeters ? Number(squareMeters) : null,
          listing_type: listingType,
          property_type: propertyType,
        }),
      });

      const failedPhotos: string[] = [];
      for (const file of photos) {
        try {
          await apiUpload(`/listings/${listing.id}/photos`, file);
        } catch {
          failedPhotos.push(file.name);
        }
      }

      if (failedPhotos.length > 0) {
        window.alert(
          `İlan kaydedildi ancak şu fotoğraflar yüklenemedi: ${failedPhotos.join(
            ", "
          )}. Panelden tekrar ekleyebilirsiniz.`
        );
      }

      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföy eklenemedi");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-6 py-4 sm:gap-8 sm:py-8">
      <Link href="/listings" className="inline-flex w-fit items-center gap-1 text-body-sm text-text-muted hover:text-primary">
        <ArrowLeft className="h-4 w-4" />
        Portföylere dön
      </Link>

      <div>
        <h1 className="text-headline-lg text-primary">Yeni İlan Ekle</h1>
        <p className="mt-1 text-body-sm text-text-muted">Birkaç adımda portföyünüze ekleyin.</p>
      </div>

      <div className="flex gap-1.5">
        {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
          <div
            key={i}
            className={cn("h-1.5 flex-1 rounded-full", i < step ? "bg-primary" : "bg-surface-variant")}
          />
        ))}
      </div>

      <div className="rounded-lg bg-surface-container-lowest p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] sm:p-6">
        {step === 1 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-title-md text-primary">Bu ilan nerede?</h2>
            <p className="text-body-sm text-text-muted">
              Yazmaya başlayın, eşleşen sonuçlardan seçin — önce şehir, sonra ilçe ve mahalle.
            </p>
            <LocationAutocomplete
              id="city"
              label="Şehir"
              value={city}
              onChange={(value) => {
                setCity(value);
                setDistrict("");
                setNeighborhood("");
              }}
              endpoint="/geo/cities"
              placeholder="Örn. İstanbul"
              autoFocus
            />
            <LocationAutocomplete
              id="district"
              label="İlçe"
              value={district}
              onChange={(value) => {
                setDistrict(value);
                setNeighborhood("");
              }}
              endpoint="/geo/districts"
              params={city.trim() ? { city: city.trim() } : {}}
              placeholder={city.trim() ? "Örn. Kadıköy" : "Önce şehir seçin"}
              disabled={!city.trim()}
            />
            <LocationAutocomplete
              id="neighborhood"
              label="Mahalle (opsiyonel)"
              value={neighborhood}
              onChange={setNeighborhood}
              endpoint="/geo/neighborhoods"
              params={{
                ...(city.trim() ? { city: city.trim() } : {}),
                ...(district.trim() ? { district: district.trim() } : {}),
              }}
              placeholder={district.trim() ? "Örn. Caferağa" : "Önce ilçe seçin"}
              disabled={!district.trim()}
            />
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-title-md text-primary">Kaç oda?</h2>
            <Input
              id="roomCount"
              placeholder="Örn. 2+1"
              value={roomCount}
              onChange={(e) => setRoomCount(e.target.value)}
              autoFocus
            />
          </div>
        )}

        {step === 3 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-title-md text-primary">Satılık mı, kiralık mı?</h2>
            <ListingTypeToggle value={listingType} onChange={setListingType} />
            <div className="flex flex-col gap-1.5">
              <label htmlFor="propertyType" className="text-body-sm text-text-muted">
                Emlak tipi
              </label>
              <PropertyTypeSelect value={propertyType} onChange={setPropertyType} className="w-fit" />
            </div>
            <Input
              id="price"
              label={listingType === "rent" ? "Aylık kira (TL)" : "Satış fiyatı (TL)"}
              type="number"
              placeholder="2500000"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              autoFocus
            />
          </div>
        )}

        {step === 4 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-title-md text-primary">Son birkaç detay</h2>
            <Input
              id="title"
              label="Başlık"
              placeholder="Örn. Deniz manzaralı 3+1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Input
              id="squareMeters"
              label="Metrekare (opsiyonel)"
              type="number"
              placeholder="140"
              value={squareMeters}
              onChange={(e) => setSquareMeters(e.target.value)}
            />
          </div>
        )}

        {step === 5 && (
          <div className="flex flex-col gap-4">
            <h2 className="text-title-md text-primary">Fotoğraf ekleyin (opsiyonel)</h2>
            <div className="grid grid-cols-3 gap-2">
              {photos.map((file, i) => (
                <div key={i} className="group relative aspect-square overflow-hidden rounded">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={photoPreviewUrls[i]} alt={file.name} className="h-full w-full object-cover" />
                  {i === 0 && (
                    <span className="absolute left-1 top-1 rounded-full bg-primary/80 px-2 py-0.5 text-[10px] font-semibold text-on-primary">
                      Kapak
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => removePhoto(i)}
                    className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-primary/80 text-on-primary opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <Icon name="close" className="text-[16px]" />
                  </button>
                </div>
              ))}
              <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded border-2 border-dashed border-outline-variant text-text-muted hover:bg-surface-bright">
                <Icon name="add_photo_alternate" />
                <span className="text-center text-[11px] leading-tight">Fotoğraf seç</span>
                <input type="file" accept="image/*" multiple className="hidden" onChange={handlePhotoSelect} />
              </label>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4">
            <Alert>{error}</Alert>
          </div>
        )}

        <div className="mt-6 flex items-center justify-between">
          <Button variant="ghost" onClick={goBack} disabled={step === 1}>
            Geri
          </Button>

          {step < TOTAL_STEPS && (
            <Button
              onClick={goNext}
              disabled={
                (step === 1 && (!city.trim() || !district.trim())) ||
                (step === 2 && !roomCount.trim()) ||
                (step === 3 && !isPriceValid)
              }
            >
              İleri
            </Button>
          )}

          {step === TOTAL_STEPS && (
            <Button
              isLoading={isSaving}
              onClick={handleSave}
              disabled={!title.trim() || !district.trim() || !isPriceValid}
            >
              Kaydet
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
