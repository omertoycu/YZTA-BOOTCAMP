"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiUpload, getToken } from "@/lib/api";
import { useAudioRecorder } from "@/lib/useAudioRecorder";
import type { Listing, VoiceListingDraft } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { Icon } from "@/components/ui/Icon";

type Phase = "processing" | "review" | null;

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

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

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
          square_meters: squareMeters ? Number(squareMeters) : null,
        }),
      });
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
            <div className="grid grid-cols-2 gap-3">
              <Input
                id="voicePrice"
                label="Fiyat (TL)"
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
