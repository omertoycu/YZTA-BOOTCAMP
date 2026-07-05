"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Clock,
  Compass,
  Gauge,
  MapPin,
  Mic,
  MessageCircle,
  NotebookPen,
  Phone,
  Plus,
  Repeat,
  Send,
  Sparkles,
  Square,
  Upload,
  Users,
  Wallet,
} from "lucide-react";
import { apiFetch, apiUpload, getToken } from "@/lib/api";
import { useAudioRecorder } from "@/lib/useAudioRecorder";
import type {
  FollowUpResult,
  Lead,
  LeadNote,
  LeadScore,
  LeadStatus,
  LeadVoiceNoteDraft,
  MatchResult,
  SendMatchesResult,
} from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";

function scoreVariant(score: number): NonNullable<BadgeProps["variant"]> {
  if (score >= 70) return "success";
  if (score >= 40) return "warning";
  return "danger";
}

const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
  new: "Yeni",
  contacted: "İletişim Kuruldu",
  viewing: "Yer Gösterimi",
  negotiation: "Pazarlık",
  won: "Kazanıldı",
  lost: "Kaybedildi",
};

function statusVariant(status: LeadStatus): NonNullable<BadgeProps["variant"]> {
  if (status === "won") return "success";
  if (status === "lost") return "danger";
  if (status === "new") return "neutral";
  return "warning";
}

export default function LeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoresByLead, setScoresByLead] = useState<Record<string, LeadScore>>({});
  const [matchesByLead, setMatchesByLead] = useState<Record<string, MatchResult[]>>({});
  const [followUpResultByLead, setFollowUpResultByLead] = useState<Record<string, string>>({});
  const [notesByLead, setNotesByLead] = useState<Record<string, LeadNote[]>>({});
  const [openNotesLead, setOpenNotesLead] = useState<string | null>(null);
  const [noteDraft, setNoteDraft] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);

  // Sesli Not → CRM güncellemesi: tek seferde tek aday için açık, panel tek bir
  // paylaşılan recorder örneğini kullanır (bkz. lib/useAudioRecorder.ts).
  const voiceNoteRecorder = useAudioRecorder();
  const [openVoiceNoteLead, setOpenVoiceNoteLead] = useState<string | null>(null);
  const [voiceNotePhase, setVoiceNotePhase] = useState<"processing" | "review" | null>(null);
  const [voiceDraft, setVoiceDraft] = useState<LeadVoiceNoteDraft | null>(null);
  const [noteSummaryDraft, setNoteSummaryDraft] = useState("");
  const [suggestedStatusDraft, setSuggestedStatusDraft] = useState<LeadStatus | "">("");
  const [reminderDateDraft, setReminderDateDraft] = useState("");
  const [reminderNoteDraft, setReminderNoteDraft] = useState("");

  const [contactPhone, setContactPhone] = useState("");
  const [district, setDistrict] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [roomCount, setRoomCount] = useState("2+1");
  const [radiusKm, setRadiusKm] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    loadLeads();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadLeads() {
    setIsLoading(true);
    try {
      const data = await apiFetch<Lead[]>("/leads");
      setLeads(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lead'ler yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch("/leads", {
        method: "POST",
        body: JSON.stringify({
          contact_phone: contactPhone,
          district: district || null,
          budget_max: budgetMax ? Number(budgetMax) : null,
          room_count: roomCount || null,
          radius_km: radiusKm ? Number(radiusKm) : null,
        }),
      });
      setContactPhone("");
      setDistrict("");
      setBudgetMax("");
      setRadiusKm("");
      await loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lead eklenemedi");
    }
  }

  async function handleScore(leadId: string) {
    setPendingAction(`score-${leadId}`);
    try {
      const score = await apiFetch<LeadScore>(`/leads/${leadId}/score`, { method: "POST" });
      setScoresByLead((prev) => ({ ...prev, [leadId]: score }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Skor hesaplanamadı");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleMatch(leadId: string) {
    setPendingAction(`match-${leadId}`);
    try {
      const matches = await apiFetch<MatchResult[]>(`/leads/${leadId}/match`, { method: "POST" });
      setMatchesByLead((prev) => ({ ...prev, [leadId]: matches }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eşleştirme yapılamadı");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleStatusChange(leadId: string, status: LeadStatus) {
    setError(null);
    try {
      const updated = await apiFetch<Lead>(`/leads/${leadId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Durum güncellenemedi");
    }
  }

  async function handleSendMatches(leadId: string) {
    setPendingAction(`send-matches-${leadId}`);
    setError(null);
    try {
      const result = await apiFetch<SendMatchesResult>(`/leads/${leadId}/send-matches`, { method: "POST" });
      setFollowUpResultByLead((prev) => ({ ...prev, [leadId]: result.message }));
      await loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eşleşmeler gönderilemedi");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleToggleNotes(leadId: string) {
    if (openNotesLead === leadId) {
      setOpenNotesLead(null);
      return;
    }
    setOpenNotesLead(leadId);
    setNoteDraft("");
    try {
      const notes = await apiFetch<LeadNote[]>(`/leads/${leadId}/notes`);
      setNotesByLead((prev) => ({ ...prev, [leadId]: notes }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Notlar yüklenemedi");
    }
  }

  async function handleAddNote(leadId: string) {
    if (!noteDraft.trim()) return;
    setPendingAction(`note-${leadId}`);
    try {
      const note = await apiFetch<LeadNote>(`/leads/${leadId}/notes`, {
        method: "POST",
        body: JSON.stringify({ body: noteDraft }),
      });
      setNotesByLead((prev) => ({ ...prev, [leadId]: [note, ...(prev[leadId] ?? [])] }));
      setNoteDraft("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Not eklenemedi");
    } finally {
      setPendingAction(null);
    }
  }

  function handleToggleVoiceNote(leadId: string) {
    voiceNoteRecorder.reset();
    setVoiceNotePhase(null);
    setVoiceDraft(null);
    setOpenVoiceNoteLead((prev) => (prev === leadId ? null : leadId));
  }

  async function handleAnalyzeVoiceNote(leadId: string) {
    if (!voiceNoteRecorder.audioFile) return;
    setVoiceNotePhase("processing");
    setError(null);
    try {
      const result = await apiUpload<LeadVoiceNoteDraft>(`/leads/${leadId}/voice-note`, voiceNoteRecorder.audioFile);
      setVoiceDraft(result);
      setNoteSummaryDraft(result.note_summary ?? "");
      setSuggestedStatusDraft(result.suggested_status ?? "");
      setReminderDateDraft(result.reminder_at ? result.reminder_at.slice(0, 10) : "");
      setReminderNoteDraft(result.reminder_note ?? "");
      setVoiceNotePhase("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ses işlenemedi");
      setVoiceNotePhase(null);
    }
  }

  async function handleConfirmVoiceNote(lead: Lead) {
    setPendingAction(`voice-note-confirm-${lead.id}`);
    setError(null);
    try {
      if (noteSummaryDraft.trim()) {
        const note = await apiFetch<LeadNote>(`/leads/${lead.id}/notes`, {
          method: "POST",
          body: JSON.stringify({ body: noteSummaryDraft.trim() }),
        });
        setNotesByLead((prev) => ({ ...prev, [lead.id]: [note, ...(prev[lead.id] ?? [])] }));
      }
      if (suggestedStatusDraft && suggestedStatusDraft !== lead.status) {
        const updated = await apiFetch<Lead>(`/leads/${lead.id}/status`, {
          method: "PATCH",
          body: JSON.stringify({ status: suggestedStatusDraft }),
        });
        setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      }
      if (reminderDateDraft) {
        const updated = await apiFetch<Lead>(`/leads/${lead.id}/reminder`, {
          method: "PATCH",
          body: JSON.stringify({
            reminder_at: new Date(`${reminderDateDraft}T09:00:00`).toISOString(),
            reminder_note: reminderNoteDraft.trim() || null,
          }),
        });
        setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      }
      setOpenVoiceNoteLead(null);
      voiceNoteRecorder.reset();
      setVoiceNotePhase(null);
      setVoiceDraft(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Onaylanamadı");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleToggleAutoFollowUp(lead: Lead) {
    setPendingAction(`auto-follow-up-${lead.id}`);
    setError(null);
    try {
      const updated = await apiFetch<Lead>(`/leads/${lead.id}/auto-follow-up`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !lead.auto_follow_up_enabled }),
      });
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Otomatik takip güncellenemedi");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleFollowUp(leadId: string) {
    setPendingAction(`follow-up-${leadId}`);
    setError(null);
    try {
      const result = await apiFetch<FollowUpResult>(`/leads/${leadId}/follow-up`, { method: "POST" });
      setFollowUpResultByLead((prev) => ({ ...prev, [leadId]: result.message }));
      await loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Takip mesajı gönderilemedi");
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-headline-lg text-primary">Adaylar</h1>
        <p className="mt-1 text-body-sm text-text-muted">
          Gelen talepleri skorlayın, en uygun portföyle eşleştirin.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Yeni aday ekle</CardTitle>
          <CardDescription>İletişim bilgisi ve tercihleri girerek listenize ekleyin.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
            <Input
              id="contactPhone"
              label="Telefon"
              required
              placeholder="05XX XXX XX XX"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
              className="lg:col-span-2"
            />
            <Input
              id="leadDistrict"
              label="Bölge"
              placeholder="Örn. Beşiktaş"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
            />
            <Input
              id="budgetMax"
              label="Maks. bütçe (TL)"
              type="number"
              placeholder="3000000"
              value={budgetMax}
              onChange={(e) => setBudgetMax(e.target.value)}
            />
            <Input
              id="leadRoomCount"
              label="Oda sayısı"
              placeholder="2+1"
              value={roomCount}
              onChange={(e) => setRoomCount(e.target.value)}
            />
            <Input
              id="radiusKm"
              label="Arama yarıçapı (km, opsiyonel)"
              type="number"
              placeholder="Örn. 5"
              value={radiusKm}
              onChange={(e) => setRadiusKm(e.target.value)}
            />
            <Button type="submit" className="lg:col-span-5 lg:w-fit">
              <Plus className="h-4 w-4" />
              Aday ekle
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && <Alert>{error}</Alert>}

      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-16 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      )}

      {!isLoading && leads.length === 0 && (
        <EmptyState
          icon={Users}
          title="Henüz aday eklenmedi"
          description="Yukarıdaki formu kullanarak ilk adayınızı ekleyin."
        />
      )}

      <div className="flex flex-col gap-4">
        {leads.map((lead) => {
          const score = scoresByLead[lead.id];
          const matches = matchesByLead[lead.id];
          return (
            <Card key={lead.id}>
              <CardContent className="flex flex-col gap-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2 font-semibold text-primary">
                      <Phone className="h-4 w-4 text-outline" />
                      {lead.contact_phone}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant={statusVariant(lead.status)}>
                        {LEAD_STATUS_LABELS[lead.status] ?? lead.status}
                      </Badge>
                      <Badge variant="neutral">
                        <MapPin className="h-3 w-3" />
                        {lead.district ?? "Bölge belirtilmedi"}
                      </Badge>
                      <Badge variant="neutral">{lead.room_count ?? "Oda belirtilmedi"}</Badge>
                      <Badge variant="brand">
                        <Wallet className="h-3 w-3" />
                        {lead.budget_max ? `${formatCurrency(lead.budget_max)}'ye kadar` : "Bütçe belirtilmedi"}
                      </Badge>
                      {lead.radius_km && (
                        <Badge variant="neutral">
                          <Compass className="h-3 w-3" />
                          {lead.radius_km} km yarıçap
                        </Badge>
                      )}
                      {score && (
                        <Badge variant={scoreVariant(score.score)}>
                          <Gauge className="h-3 w-3" />
                          Skor: {score.score}/100
                        </Badge>
                      )}
                      {lead.reminder_at && (
                        <Badge variant="warning">
                          <Clock className="h-3 w-3" />
                          Hatırlatma {new Date(lead.reminder_at).toLocaleDateString("tr-TR")}
                          {lead.reminder_note ? `: ${lead.reminder_note}` : ""}
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <select
                      value={lead.status}
                      onChange={(e) => handleStatusChange(lead.id, e.target.value as LeadStatus)}
                      aria-label="Aday durumu"
                      className="rounded border border-outline-variant bg-surface-container-lowest px-2 py-1 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
                    >
                      {Object.entries(LEAD_STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={pendingAction === `score-${lead.id}`}
                      onClick={() => handleScore(lead.id)}
                    >
                      <Gauge className="h-3.5 w-3.5" />
                      Skorla
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={pendingAction === `match-${lead.id}`}
                      onClick={() => handleMatch(lead.id)}
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      Eşleştir
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={pendingAction === `follow-up-${lead.id}`}
                      onClick={() => handleFollowUp(lead.id)}
                    >
                      <MessageCircle className="h-3.5 w-3.5" />
                      Takip Mesajı Gönder
                    </Button>
                    <Button
                      variant={lead.auto_follow_up_enabled ? "primary" : "outline"}
                      size="sm"
                      isLoading={pendingAction === `auto-follow-up-${lead.id}`}
                      onClick={() => handleToggleAutoFollowUp(lead)}
                    >
                      <Repeat className="h-3.5 w-3.5" />
                      {lead.auto_follow_up_enabled ? "Otomatik Takip: Açık" : "Otomatik Takip"}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={pendingAction === `send-matches-${lead.id}`}
                      onClick={() => handleSendMatches(lead.id)}
                    >
                      <Send className="h-3.5 w-3.5" />
                      Eşleşenleri Gönder
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleToggleNotes(lead.id)}>
                      <NotebookPen className="h-3.5 w-3.5" />
                      Notlar
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleToggleVoiceNote(lead.id)}>
                      <Mic className="h-3.5 w-3.5" />
                      Sesli Not
                    </Button>
                  </div>
                </div>

                {openVoiceNoteLead === lead.id && (
                  <div className="flex flex-col gap-3 rounded bg-surface-bright p-3">
                    {voiceNoteRecorder.stage === "idle" && voiceNotePhase === null && (
                      <div className="flex flex-col items-center gap-3 py-4">
                        <button
                          type="button"
                          onClick={voiceNoteRecorder.start}
                          className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-on-primary shadow-lg transition-transform hover:scale-105"
                        >
                          <Mic className="h-6 w-6" />
                        </button>
                        <p className="text-body-sm text-text-muted">
                          Görüşme sonrası aday hakkında sesli not bırakın — sistem görüşme notu,
                          durum ve hatırlatma önerisi çıkarsın.
                        </p>
                        <label className="flex cursor-pointer items-center gap-2 rounded-full border border-outline-variant px-3 py-1.5 text-body-sm text-on-surface hover:bg-surface-container-lowest">
                          <Upload className="h-3.5 w-3.5" />
                          Ses dosyası yükle
                          <input
                            type="file"
                            accept="audio/*"
                            className="hidden"
                            onChange={voiceNoteRecorder.handleFileUpload}
                          />
                        </label>
                      </div>
                    )}

                    {voiceNoteRecorder.stage === "recording" && voiceNotePhase === null && (
                      <div className="flex flex-col items-center gap-3 py-4">
                        <button
                          type="button"
                          onClick={voiceNoteRecorder.stop}
                          className="flex h-14 w-14 animate-pulse items-center justify-center rounded-full bg-error text-on-error shadow-lg"
                        >
                          <Square className="h-6 w-6" />
                        </button>
                        <p className="font-mono text-title-md text-primary">
                          {String(Math.floor(voiceNoteRecorder.recordSeconds / 60)).padStart(2, "0")}:
                          {String(voiceNoteRecorder.recordSeconds % 60).padStart(2, "0")}
                        </p>
                        <p className="text-body-sm text-text-muted">Kaydediliyor... durdurmak için dokunun</p>
                      </div>
                    )}

                    {voiceNoteRecorder.stage === "recorded" && voiceNotePhase === null && voiceNoteRecorder.audioUrl && (
                      <div className="flex flex-col items-center gap-3 py-2">
                        {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                        <audio src={voiceNoteRecorder.audioUrl} controls className="w-full" />
                        <div className="flex gap-2">
                          <Button variant="outline" size="sm" onClick={voiceNoteRecorder.reset}>
                            Yeniden Kaydet
                          </Button>
                          <Button size="sm" onClick={() => handleAnalyzeVoiceNote(lead.id)}>
                            <Sparkles className="h-3.5 w-3.5" />
                            Analiz Et
                          </Button>
                        </div>
                      </div>
                    )}

                    {voiceNotePhase === "processing" && (
                      <div className="flex flex-col items-center gap-2 py-6">
                        <Spinner />
                        <p className="text-body-sm text-text-muted">Gemini dinliyor ve notu çıkarıyor...</p>
                      </div>
                    )}

                    {voiceNotePhase === "review" && voiceDraft && (
                      <div className="flex flex-col gap-3">
                        <div className="rounded bg-surface-container-lowest p-2.5 text-body-sm">
                          <p className="mb-1 font-label text-label-caps text-text-muted">Transkript</p>
                          <p className="italic text-on-surface">&ldquo;{voiceDraft.transcript}&rdquo;</p>
                        </div>
                        <Input
                          id={`voice-note-summary-${lead.id}`}
                          label="Görüşme notu"
                          value={noteSummaryDraft}
                          onChange={(e) => setNoteSummaryDraft(e.target.value)}
                        />
                        <div className="grid grid-cols-2 gap-3">
                          <div className="flex flex-col gap-1.5">
                            <label
                              htmlFor={`voice-note-status-${lead.id}`}
                              className="font-label text-label-caps text-on-surface-variant"
                            >
                              Önerilen durum
                            </label>
                            <select
                              id={`voice-note-status-${lead.id}`}
                              value={suggestedStatusDraft}
                              onChange={(e) => setSuggestedStatusDraft(e.target.value as LeadStatus | "")}
                              className="h-10 rounded border border-outline-variant bg-surface-container-lowest px-2 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
                            >
                              <option value="">Değiştirme</option>
                              {Object.entries(LEAD_STATUS_LABELS).map(([value, label]) => (
                                <option key={value} value={value}>
                                  {label}
                                </option>
                              ))}
                            </select>
                          </div>
                          <Input
                            id={`voice-note-reminder-date-${lead.id}`}
                            label="Hatırlatma tarihi"
                            type="date"
                            value={reminderDateDraft}
                            onChange={(e) => setReminderDateDraft(e.target.value)}
                          />
                        </div>
                        {reminderDateDraft && (
                          <Input
                            id={`voice-note-reminder-note-${lead.id}`}
                            label="Hatırlatma notu"
                            value={reminderNoteDraft}
                            onChange={(e) => setReminderNoteDraft(e.target.value)}
                          />
                        )}
                        <div className="mt-1 flex justify-between">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              voiceNoteRecorder.reset();
                              setVoiceNotePhase(null);
                              setVoiceDraft(null);
                            }}
                          >
                            Baştan Başla
                          </Button>
                          <Button
                            size="sm"
                            isLoading={pendingAction === `voice-note-confirm-${lead.id}`}
                            onClick={() => handleConfirmVoiceNote(lead)}
                          >
                            Onayla ve Kaydet
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {openNotesLead === lead.id && (
                  <div className="flex flex-col gap-3 rounded bg-surface-bright p-3">
                    <div className="flex gap-2">
                      <Input
                        id={`note-${lead.id}`}
                        placeholder="Görüşme notu ekleyin..."
                        value={noteDraft}
                        onChange={(e) => setNoteDraft(e.target.value)}
                        className="flex-1"
                      />
                      <Button
                        size="sm"
                        isLoading={pendingAction === `note-${lead.id}`}
                        onClick={() => handleAddNote(lead.id)}
                      >
                        Ekle
                      </Button>
                    </div>
                    {(notesByLead[lead.id] ?? []).length === 0 ? (
                      <p className="text-body-sm text-text-muted">Henüz not yok.</p>
                    ) : (
                      <ul className="flex flex-col gap-2">
                        {(notesByLead[lead.id] ?? []).map((note) => (
                          <li key={note.id} className="rounded bg-surface-container-lowest p-2.5 text-body-sm">
                            <p className="text-on-surface">{note.body}</p>
                            <p className="mt-1 text-[11px] text-text-muted">
                              {note.author_email ?? "danışman"} ·{" "}
                              {new Date(note.created_at).toLocaleString("tr-TR")}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {followUpResultByLead[lead.id] && (
                  <div className="rounded bg-mint-accent p-3 text-body-sm text-on-secondary-container">
                    Gönderildi: &ldquo;{followUpResultByLead[lead.id]}&rdquo;
                  </div>
                )}

                {matches && (
                  <div className="rounded bg-surface-bright p-3">
                    {matches.length === 0 ? (
                      <p className="text-body-sm text-text-muted">Uygun portföy bulunamadı.</p>
                    ) : (
                      <ul className="flex flex-col gap-1.5">
                        {matches.map((match) => (
                          <li
                            key={match.listing_id}
                            className="flex items-center justify-between text-body-sm text-on-surface"
                          >
                            <span>{match.title}</span>
                            <span className="font-medium text-primary">{formatCurrency(match.price)}</span>
                          </li>
                        ))}
                      </ul>
                    )}
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
