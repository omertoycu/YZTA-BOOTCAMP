"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiUpload, getToken } from "@/lib/api";
import { useAudioRecorder } from "@/lib/useAudioRecorder";
import type { Listing, ListingType, VoiceListingDraft } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { Icon } from "@/components/ui/Icon";
import { ListingTypeToggle } from "@/components/ui/ListingTypeToggle";

type Phase = "processing" | "review" | null;

const MAX_PHOTO_BYTES = 8 * 1024 * 1024; // 8MB, backend ile aynı sınır

export default function AssistantPage() {
  const router = useRouter();
  const recorder = useAudioRecorder();
  const [phase, setPhase] = useState<Phase>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<VoiceListingDraft | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const [title, setTitle] = useState("");
  const [district, setDistrict] = useState("");
  const [price, setPrice] = useState("");
  const [roomCount, setRoomCount] = useState("");
  const [squareMeters, setSquareMeters] = useState("");
  const [listingType, setListingType] = useState<ListingType>("sale");
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

  const displayError = error ?? recorder.error;

  async function handleAnalyze() {
    if (!recorder.audioFile) return;
    setPhase("processing");
    setError(null);
    try {
      const result = await apiUpload<VoiceListingDraft>("/listings/voice-draft", recorder.audioFile);
      setDraft(result);
      setTitle(result.title ?? "");
      setDistrict(result.district ?? "");
      setPrice(result.price != null ? String(result.price) : "");
      setRoomCount(result.room_count ?? "");
      setSquareMeters(result.square_meters != null ? String(result.square_meters) : "");
      setListingType(result.listing_type ?? "sale");
      setPhase("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ses işlenemedi");
      setPhase(null);
    }
  }

  function reset() {
    recorder.reset();
    setPhase(null);
    setDraft(null);
    setError(null);
    setPhotos([]);
  }

  const parsedPrice = Number(price);
  const isPriceValid = price.trim() !== "" && Number.isFinite(parsedPrice) && parsedPrice > 0;
  const canCreate = title.trim() !== "" && district.trim() !== "" && isPriceValid;

  async function handleCreateListing() {
    setIsCreating(true);
    setError(null);
    try {
      const listing = await apiFetch<Listing>("/listings", {
        method: "POST",
        body: JSON.stringify({
          title,
          district,
          price: Number(price),
          room_count: roomCount || "Belirtilmedi",
          listing_type: listingType,
          square_meters: squareMeters ? Number(squareMeters) : null,
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
          )}. Portföy detayından tekrar ekleyebilirsiniz.`
        );
      }

      router.push(`/listings/${listing.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portföy oluşturulamadı");
      setIsCreating(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6 py-8">
      <div className="flex flex-col items-center gap-3 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-mint-accent text-secondary">
          <Icon name="psychology" className="text-[32px]" />
        </div>
        <h1 className="text-headline-lg text-primary">YZ Asistanı — Sesli Not → İlan</h1>
        <p className="max-w-sm text-body-sm text-text-muted">
          Sahada telefonunuza portföyü anlatın; yapay zeka transkript çıkarıp taslak bir ilan
          hazırlasın, siz onaylayın.
        </p>
      </div>

      {displayError && <Alert>{displayError}</Alert>}

      <div className="rounded-lg bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
        {phase === null && recorder.stage === "idle" && (
          <div className="flex flex-col items-center gap-4 py-6">
            <button
              type="button"
              onClick={recorder.start}
              className="flex h-20 w-20 items-center justify-center rounded-full bg-primary text-on-primary shadow-lg transition-transform hover:scale-105"
            >
              <Icon name="mic" className="text-[36px]" />
            </button>
            <p className="text-body-sm text-text-muted">Kayda başlamak için dokunun</p>
            <div className="flex items-center gap-2 text-body-sm text-text-muted">
              <span className="h-px w-10 bg-outline-variant" />
              veya
              <span className="h-px w-10 bg-outline-variant" />
            </div>
            <label className="flex cursor-pointer items-center gap-2 rounded-full border border-outline-variant px-4 py-2 text-body-sm text-on-surface hover:bg-surface-bright">
              <Icon name="upload_file" className="text-[18px]" />
              Ses dosyası yükle
              <input type="file" accept="audio/*" className="hidden" onChange={recorder.handleFileUpload} />
            </label>
          </div>
        )}

        {phase === null && recorder.stage === "recording" && (
          <div className="flex flex-col items-center gap-4 py-6">
            <button
              type="button"
              onClick={recorder.stop}
              className="flex h-20 w-20 animate-pulse items-center justify-center rounded-full bg-error text-on-error shadow-lg"
            >
              <Icon name="stop" className="text-[36px]" />
            </button>
            <p className="font-mono text-title-md text-primary">
              {String(Math.floor(recorder.recordSeconds / 60)).padStart(2, "0")}:
              {String(recorder.recordSeconds % 60).padStart(2, "0")}
            </p>
            <p className="text-body-sm text-text-muted">Kaydediliyor... durdurmak için dokunun</p>
          </div>
        )}

        {phase === null && recorder.stage === "recorded" && recorder.audioUrl && (
          <div className="flex flex-col items-center gap-4 py-4">
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <audio src={recorder.audioUrl} controls className="w-full" />
            <div className="flex gap-2">
              <Button variant="outline" onClick={reset}>
                Yeniden Kaydet
              </Button>
              <Button onClick={handleAnalyze}>
                <Icon name="auto_awesome" className="text-[18px]" />
                Analiz Et
              </Button>
            </div>
          </div>
        )}

        {phase === "processing" && (
          <div className="flex flex-col items-center gap-3 py-10">
            <Spinner className="h-8 w-8" />
            <p className="text-body-sm text-text-muted">Gemini dinliyor ve ilan taslağı hazırlıyor...</p>
          </div>
        )}

        {phase === "review" && draft && (
          <div className="flex flex-col gap-4">
            <div className="rounded bg-surface-container p-3 text-body-sm text-on-surface">
              <p className="mb-1 font-label text-label-caps text-text-muted">Transkript</p>
              <p className="italic">&ldquo;{draft.transcript}&rdquo;</p>
            </div>

            <p className="text-body-sm text-text-muted">
              Aşağıdaki bilgileri gözden geçirin, gerekirse düzeltin ve onaylayın.
            </p>

            <Input id="voiceTitle" label="Başlık" value={title} onChange={(e) => setTitle(e.target.value)} />
            <Input id="voiceDistrict" label="Bölge" value={district} onChange={(e) => setDistrict(e.target.value)} />
            <div className="flex flex-col gap-1.5">
              <p className="font-label text-label-caps text-on-surface-variant">Satılık mı, kiralık mı?</p>
              <ListingTypeToggle value={listingType} onChange={setListingType} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input
                id="voicePrice"
                label={listingType === "rent" ? "Aylık kira (TL)" : "Fiyat (TL)"}
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
              <Input
                id="voiceRoomCount"
                label="Oda sayısı"
                placeholder="Örn. 3+1"
                value={roomCount}
                onChange={(e) => setRoomCount(e.target.value)}
              />
            </div>
            <Input
              id="voiceSquareMeters"
              label="Metrekare (opsiyonel)"
              type="number"
              value={squareMeters}
              onChange={(e) => setSquareMeters(e.target.value)}
            />

            <div className="flex flex-col gap-2">
              <p className="font-label text-label-caps text-text-muted">Fotoğraf ekleyin (opsiyonel)</p>
              <div className="grid grid-cols-4 gap-2">
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

            <div className="mt-2 flex justify-between">
              <Button variant="ghost" onClick={reset}>
                Baştan Başla
              </Button>
              <Button isLoading={isCreating} disabled={!canCreate} onClick={handleCreateListing}>
                İlanı Oluştur
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
