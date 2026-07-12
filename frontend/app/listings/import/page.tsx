"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { Listing, ListingPortfolioExtract, ListingType, PropertyType } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { Icon } from "@/components/ui/Icon";
import { ListingTypeToggle } from "@/components/ui/ListingTypeToggle";
import { PropertyTypeSelect } from "@/components/ui/PropertyTypeSelect";

interface DraftListing {
  selected: boolean;
  title: string;
  city: string;
  district: string;
  neighborhood: string;
  price: string;
  roomCount: string;
  squareMeters: string;
  listingType: ListingType;
  propertyType: PropertyType;
  coverPhotoUrl: string | null;
}

function mapExtractToDrafts(result: ListingPortfolioExtract): DraftListing[] {
  return result.listings.map((item) => ({
    selected: true,
    title: item.title ?? "",
    // Şehir portal kaynağında çoğu zaman yoktur — backend ilçe+mahalle
    // eşleşmesinden çıkarıp doldurur (bkz. app/core/geo.py).
    city: item.city ?? "",
    district: item.district ?? "",
    neighborhood: item.neighborhood ?? "",
    price: item.price != null ? String(item.price) : "",
    roomCount: item.room_count ?? "",
    squareMeters: item.square_meters != null ? String(item.square_meters) : "",
    listingType: item.listing_type ?? "sale",
    propertyType: item.property_type ?? "residential",
    coverPhotoUrl: item.cover_photo_url,
  }));
}

export default function ImportPortfolioPage() {
  const router = useRouter();
  const [pastedHtml, setPastedHtml] = useState("");
  const [storeUrl, setStoreUrl] = useState("");
  const [isExtracting, setIsExtracting] = useState(false);
  const [isFetchingStore, setIsFetchingStore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<DraftListing[] | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importSummary, setImportSummary] = useState<{
    succeeded: number;
    failed: string[];
    photoFailed: string[];
  } | null>(null);

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  async function handleExtract() {
    setError(null);
    setImportSummary(null);
    setIsExtracting(true);
    try {
      const result = await apiFetch<ListingPortfolioExtract>("/listings/extract-portfolio-from-html", {
        method: "POST",
        body: JSON.stringify({ html: pastedHtml }),
      });
      if (result.listings.length === 0) {
        setError("Sayfadan hiç ilan ayrıştırılamadı. Kaynağın doğru sayfadan (portföyünüzün listelendiği sayfa) kopyalandığından emin olun.");
        setDrafts(null);
        return;
      }
      setDrafts(mapExtractToDrafts(result));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sayfadan bilgi çıkarılamadı");
      setDrafts(null);
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleStoreImport() {
    setError(null);
    setImportSummary(null);
    setIsFetchingStore(true);
    try {
      // Apify üzerinden mağaza sayfası çekimi 30-90 sn sürebilir — buton bu
      // süre boyunca yükleniyor durumunda kalır, sonuç aynı inceleme akışına düşer.
      const result = await apiFetch<ListingPortfolioExtract>("/listings/import-store", {
        method: "POST",
        body: JSON.stringify({ url: storeUrl.trim() }),
      });
      setDrafts(mapExtractToDrafts(result));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Mağaza sayfası okunamadı. Alternatif olarak sayfa kaynağını yapıştırabilir ya da Voice-to-Listing (Sesle İlan Ekleme) özelliğini kullanabilirsiniz."
      );
      setDrafts(null);
    } finally {
      setIsFetchingStore(false);
    }
  }

  function updateDraft(index: number, patch: Partial<DraftListing>) {
    setDrafts((prev) => (prev ? prev.map((d, i) => (i === index ? { ...d, ...patch } : d)) : prev));
  }

  function isDraftValid(draft: DraftListing) {
    const price = Number(draft.price);
    return draft.title.trim() !== "" && draft.district.trim() !== "" && draft.price.trim() !== "" && Number.isFinite(price) && price > 0;
  }

  const selectedCount = drafts?.filter((d) => d.selected).length ?? 0;

  async function handleImportSelected() {
    if (!drafts) return;
    setIsImporting(true);
    setError(null);
    const failed: string[] = [];
    const photoFailed: string[] = [];
    let succeeded = 0;

    for (const draft of drafts) {
      if (!draft.selected) continue;
      if (!isDraftValid(draft)) {
        failed.push(draft.title || "(başlıksız ilan)");
        continue;
      }
      try {
        const listing = await apiFetch<Listing>("/listings", {
          method: "POST",
          body: JSON.stringify({
            title: draft.title,
            city: draft.city.trim() || null,
            district: draft.district,
            neighborhood: draft.neighborhood.trim() || null,
            price: Number(draft.price),
            room_count: draft.roomCount.trim() || "Belirtilmedi",
            square_meters: draft.squareMeters ? Number(draft.squareMeters) : null,
            listing_type: draft.listingType,
            property_type: draft.propertyType,
          }),
        });
        succeeded += 1;

        // Kapak fotoğrafını best-effort olarak indirmeye çalış — en azından
        // emlakçı hangi evin hangisi olduğunu hatırlayabilsin. Başarısız
        // olursa ilan zaten oluşturuldu, sadece fotoğraf eksik kalır.
        if (draft.coverPhotoUrl) {
          try {
            await apiFetch(`/listings/${listing.id}/photos/from-url`, {
              method: "POST",
              body: JSON.stringify({ url: draft.coverPhotoUrl }),
            });
          } catch {
            photoFailed.push(draft.title || "(başlıksız ilan)");
          }
        }
      } catch {
        failed.push(draft.title || "(başlıksız ilan)");
      }
    }

    setImportSummary({ succeeded, failed, photoFailed });
    setIsImporting(false);
    if (failed.length === 0 && photoFailed.length === 0) {
      router.push("/listings");
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 py-8">
      <Link href="/listings" className="inline-flex w-fit items-center gap-1 text-body-sm text-text-muted hover:text-primary">
        <ArrowLeft className="h-4 w-4" />
        Portföylere dön
      </Link>

      <div>
        <h1 className="text-headline-lg text-primary">Sahibinden&apos;den Toplu Aktarım</h1>
        <p className="mt-1 text-body-sm text-text-muted">
          İki yol var: mağaza adresinizi yazın, ilanlar sizin yerinize çekilsin — ya da
          Sahibinden&apos;de portföyünüzün listelendiği sayfayı açıp Ctrl+U (sayfa kaynağını görüntüle)
          ile açılan sekmedeki tüm metni kopyalayıp aşağıya yapıştırın. Her iki yolda da hiçbir ilan
          otomatik eklenmez; ayrıştırılan taslakları gözden geçirip onaylarsınız.
        </p>
      </div>

      {error && <Alert>{error}</Alert>}

      {!drafts && (
        <div className="flex flex-col gap-3 rounded-lg bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
          <label className="text-body-sm font-medium text-on-surface" htmlFor="storeUrl">
            Mağaza adresi ile aktar
          </label>
          <p className="text-body-sm text-text-muted">
            Sahibinden mağazanızın adresini yazın (örn. magazaadi.sahibinden.com) — ilanlar sizin
            yerinize çekilip aşağıdaki inceleme akışına düşer. Çekim 1-2 dakika sürebilir.
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[240px] flex-1">
              <Input
                id="storeUrl"
                label=""
                placeholder="magazaadi.sahibinden.com"
                value={storeUrl}
                onChange={(e) => setStoreUrl(e.target.value)}
              />
            </div>
            <Button
              isLoading={isFetchingStore}
              disabled={!storeUrl.trim() || isExtracting}
              onClick={handleStoreImport}
              className="w-fit"
            >
              <Icon name="storefront" className="text-[18px]" />
              Mağazadan Aktar
            </Button>
          </div>

          <div className="my-2 flex items-center gap-3 text-body-sm text-text-muted">
            <span className="h-px flex-1 bg-outline-variant" />
            veya sayfa kaynağını yapıştırın
            <span className="h-px flex-1 bg-outline-variant" />
          </div>

          <label className="text-body-sm font-medium text-on-surface" htmlFor="portfolioHtml">
            Sayfa kaynağı
          </label>
          <textarea
            id="portfolioHtml"
            value={pastedHtml}
            onChange={(e) => setPastedHtml(e.target.value)}
            rows={10}
            placeholder="Sayfa kaynağını buraya yapıştırın..."
            className="w-full rounded border border-outline-variant bg-surface-container-lowest p-3 font-mono text-xs text-on-surface focus:border-secondary focus:outline-none"
          />
          <Button isLoading={isExtracting} disabled={!pastedHtml.trim() || isFetchingStore} onClick={handleExtract} className="w-fit">
            <Icon name="auto_awesome" className="text-[18px]" />
            İlanları Ayrıştır
          </Button>
        </div>
      )}

      {drafts && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="text-body-sm text-text-muted">
              {drafts.length} ilan bulundu, {selectedCount} tanesi seçili. Bilgileri gözden geçirip
              gerekirse düzeltin.
            </p>
            <Button variant="ghost" size="sm" onClick={() => setDrafts(null)}>
              Baştan Başla
            </Button>
          </div>

          {importSummary && (
            <Alert>
              {importSummary.succeeded} ilan eklendi.
              {importSummary.failed.length > 0 &&
                ` Eklenemeyenler: ${importSummary.failed.join(", ")} — bilgileri kontrol edip tekrar deneyin.`}
              {importSummary.photoFailed.length > 0 &&
                ` Kapak fotoğrafı çekilemeyenler: ${importSummary.photoFailed.join(
                  ", "
                )} — ilan eklendi, fotoğrafı portföy detayından elle ekleyebilirsiniz.`}
            </Alert>
          )}

          <div className="flex flex-col gap-3">
            {drafts.map((draft, index) => (
              <div
                key={index}
                className={`flex flex-col gap-3 rounded-lg border p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] ${
                  draft.selected ? "border-secondary bg-surface-container-lowest" : "border-outline-variant bg-surface-container-lowest opacity-60"
                }`}
              >
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={draft.selected}
                    onChange={(e) => updateDraft(index, { selected: e.target.checked })}
                    className="mt-1 h-4 w-4 accent-secondary"
                    aria-label={`${draft.title || "İlan"} seçili`}
                  />
                  {draft.coverPhotoUrl && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={draft.coverPhotoUrl}
                      alt=""
                      className="h-14 w-14 shrink-0 rounded object-cover"
                    />
                  )}
                  <div className="flex-1">
                    <Input
                      id={`title-${index}`}
                      label="Başlık"
                      value={draft.title}
                      onChange={(e) => updateDraft(index, { title: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3 pl-7">
                  <ListingTypeToggle
                    value={draft.listingType}
                    onChange={(listingType) => updateDraft(index, { listingType })}
                  />
                  <PropertyTypeSelect
                    value={draft.propertyType}
                    onChange={(propertyType) => updateDraft(index, { propertyType })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3 pl-7 sm:grid-cols-3">
                  <Input
                    id={`city-${index}`}
                    label="Şehir"
                    placeholder="İlçeden otomatik bulunur"
                    value={draft.city}
                    onChange={(e) => updateDraft(index, { city: e.target.value })}
                  />
                  <Input
                    id={`district-${index}`}
                    label="İlçe"
                    value={draft.district}
                    onChange={(e) => updateDraft(index, { district: e.target.value })}
                  />
                  <Input
                    id={`neighborhood-${index}`}
                    label="Mahalle"
                    value={draft.neighborhood}
                    onChange={(e) => updateDraft(index, { neighborhood: e.target.value })}
                  />
                  <Input
                    id={`price-${index}`}
                    label={draft.listingType === "rent" ? "Aylık kira (TL)" : "Fiyat (TL)"}
                    type="number"
                    value={draft.price}
                    onChange={(e) => updateDraft(index, { price: e.target.value })}
                  />
                  <Input
                    id={`rooms-${index}`}
                    label="Oda sayısı"
                    value={draft.roomCount}
                    onChange={(e) => updateDraft(index, { roomCount: e.target.value })}
                  />
                  <Input
                    id={`sqm-${index}`}
                    label="m² (opsiyonel)"
                    type="number"
                    value={draft.squareMeters}
                    onChange={(e) => updateDraft(index, { squareMeters: e.target.value })}
                  />
                </div>
                {draft.selected && !isDraftValid(draft) && (
                  <p className="pl-7 text-body-sm text-error">Başlık, ilçe ve geçerli bir fiyat gerekli.</p>
                )}
              </div>
            ))}
          </div>

          <div className="flex justify-end">
            <Button isLoading={isImporting} disabled={selectedCount === 0} onClick={handleImportSelected}>
              Seçilen {selectedCount} İlanı İçe Aktar
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
