"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  CalendarPlus,
  Clock,
  Compass,
  DollarSign,
  Download,
  Gauge,
  MapPin,
  Mic,
  MessageCircle,
  Phone,
  Plus,
  Repeat,
  Send,
  Sparkles,
  Square,
  Trash2,
  Upload,
  Users,
  Wallet,
  Wand2,
  X,
} from "lucide-react";
import { apiFetch, apiFetchBlob, apiUpload, getToken } from "@/lib/api";
import { useAudioRecorder } from "@/lib/useAudioRecorder";
import type {
  AppointmentResult,
  FollowUpResult,
  Lead,
  LeadFieldExtractionDraft,
  LeadNote,
  LeadScore,
  LeadStatus,
  LeadUpdatePayload,
  LeadVoiceNoteDraft,
  ListingType,
  MatchResult,
  PropertyType,
  SendMatchesResult,
  SuggestReplyResult,
  WhatsAppMessage,
} from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge, type BadgeProps } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
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

const LISTING_TYPE_PREFERENCE_LABELS: Record<ListingType, string> = {
  sale: "Satılık arıyor",
  rent: "Kiralık arıyor",
};

const PROPERTY_TYPE_PREFERENCE_LABELS: Record<PropertyType, string> = {
  residential: "Konut",
  commercial: "İş Yeri",
  land: "Arsa",
};

function statusVariant(status: LeadStatus): NonNullable<BadgeProps["variant"]> {
  if (status === "won") return "success";
  if (status === "lost") return "danger";
  if (status === "new") return "neutral";
  return "warning";
}

// Kart içi sekmeler — eski tasarımda 13 buton tek satırda sıkışıyordu (gerçek
// kullanıcı şikayeti); işlevler mantıksal gruplara ayrıldı, aynı anda tek
// sekmenin içeriği görünür.
type LeadTab = "eslestirme" | "mesajlar" | "notlar" | "randevu";

const LEAD_TABS: { key: LeadTab; label: string }[] = [
  { key: "eslestirme", label: "Eşleştirme & Yanıt" },
  { key: "mesajlar", label: "Mesajlar & Takip" },
  { key: "notlar", label: "Notlar & Sesli Not" },
  { key: "randevu", label: "Randevu & Anlaşma" },
];

export default function LeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoresByLead, setScoresByLead] = useState<Record<string, LeadScore>>({});
  const [matchesByLead, setMatchesByLead] = useState<Record<string, MatchResult[]>>({});
  const [followUpResultByLead, setFollowUpResultByLead] = useState<Record<string, string>>({});
  const [notesByLead, setNotesByLead] = useState<Record<string, LeadNote[]>>({});
  const [noteDraft, setNoteDraft] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  // Kart içi aktif sekme (aday başına) — null: kart kapalı/özet görünümde.
  const [activeTabByLead, setActiveTabByLead] = useState<Record<string, LeadTab | null>>({});

  // WhatsApp konuşma geçmişi ("Mesajlar" sekmesi)
  const [messagesByLead, setMessagesByLead] = useState<Record<string, WhatsAppMessage[]>>({});

  // Gemini alan çıkarımını manuel tetikleme ("Yeniden Analiz Et") — sadece
  // taslak döner, danışman gözden geçirip PATCH /leads/{id} ile uygular.
  const [openReanalyzeLead, setOpenReanalyzeLead] = useState<string | null>(null);
  const [reanalyzeDraft, setReanalyzeDraft] = useState<LeadFieldExtractionDraft | null>(null);

  // RAG'lı yanıt taslağı ("Yanıt Öner") — mevcut portföylere dayalı, düzenlenip
  // mevcut POST /leads/{id}/follow-up ile gönderilir.
  const [openReplyLead, setOpenReplyLead] = useState<string | null>(null);
  const [replyDraft, setReplyDraft] = useState("");

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

  // Yer gösterme randevusu + takvim daveti
  const [openAppointmentLead, setOpenAppointmentLead] = useState<string | null>(null);
  const [appointmentDateTime, setAppointmentDateTime] = useState("");
  const [appointmentLocation, setAppointmentLocation] = useState("");
  const [appointmentSendWhatsapp, setAppointmentSendWhatsapp] = useState(true);
  const [appointmentResultByLead, setAppointmentResultByLead] = useState<Record<string, string>>({});

  // Komisyon takibi
  const [openDealLead, setOpenDealLead] = useState<string | null>(null);
  const [dealAmount, setDealAmount] = useState("");
  const [commissionAmount, setCommissionAmount] = useState("");
  const [dealClosedAt, setDealClosedAt] = useState("");

  const [contactPhone, setContactPhone] = useState("");
  const [contactName, setContactName] = useState("");
  const [district, setDistrict] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [roomCount, setRoomCount] = useState("2+1");
  const [radiusKm, setRadiusKm] = useState("");
  const [listingTypePreference, setListingTypePreference] = useState<ListingType | "">("");
  const [propertyTypePreference, setPropertyTypePreference] = useState<PropertyType | "">("");

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
          contact_name: contactName.trim() || null,
          district: district || null,
          budget_max: budgetMax ? Number(budgetMax) : null,
          room_count: roomCount || null,
          radius_km: radiusKm ? Number(radiusKm) : null,
          listing_type_preference: listingTypePreference || null,
          property_type_preference: propertyTypePreference || null,
        }),
      });
      setContactPhone("");
      setContactName("");
      setDistrict("");
      setBudgetMax("");
      setRadiusKm("");
      setListingTypePreference("");
      setPropertyTypePreference("");
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

  function handleSelectTab(leadId: string, tab: LeadTab) {
    const isClosing = activeTabByLead[leadId] === tab;
    setActiveTabByLead((prev) => ({ ...prev, [leadId]: isClosing ? null : tab }));
    if (isClosing) return;
    // Sekme ilk açıldığında ilgili veri tembelce yüklenir.
    if (tab === "notlar" && !notesByLead[leadId]) {
      setNoteDraft("");
      loadNotes(leadId);
    }
    if (tab === "mesajlar" && !messagesByLead[leadId]) {
      loadMessages(leadId);
    }
  }

  async function loadNotes(leadId: string) {
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

  async function handleDeleteLead(leadId: string) {
    setPendingAction(`delete-${leadId}`);
    setError(null);
    try {
      await apiFetch(`/leads/${leadId}`, { method: "DELETE" });
      setLeads((prev) => prev.filter((l) => l.id !== leadId));
      setPendingDeleteId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Aday silinemedi");
    } finally {
      setPendingAction(null);
    }
  }

  async function loadMessages(leadId: string) {
    try {
      const messages = await apiFetch<WhatsAppMessage[]>(`/leads/${leadId}/messages`);
      setMessagesByLead((prev) => ({ ...prev, [leadId]: messages }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Mesajlar yüklenemedi");
    }
  }

  async function handleReanalyze(leadId: string) {
    setPendingAction(`reanalyze-${leadId}`);
    setError(null);
    try {
      const draft = await apiFetch<LeadFieldExtractionDraft>(`/leads/${leadId}/reanalyze-messages`, {
        method: "POST",
      });
      setReanalyzeDraft(draft);
      setOpenReanalyzeLead(leadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yeniden analiz edilemedi");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleApplyReanalyzeDraft(leadId: string) {
    if (!reanalyzeDraft) return;
    setPendingAction(`apply-reanalyze-${leadId}`);
    setError(null);
    try {
      const payload: LeadUpdatePayload = {
        district: reanalyzeDraft.district,
        budget_min: reanalyzeDraft.budget_min,
        budget_max: reanalyzeDraft.budget_max,
        room_count: reanalyzeDraft.room_count,
        radius_km: reanalyzeDraft.radius_km,
        listing_type_preference: reanalyzeDraft.listing_type_preference,
        property_type_preference: reanalyzeDraft.property_type_preference,
      };
      const updated = await apiFetch<Lead>(`/leads/${leadId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      setOpenReanalyzeLead(null);
      setReanalyzeDraft(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Alanlar uygulanamadı");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleSuggestReply(leadId: string) {
    setPendingAction(`suggest-reply-${leadId}`);
    setError(null);
    try {
      const result = await apiFetch<SuggestReplyResult>(`/leads/${leadId}/suggest-reply`, { method: "POST" });
      setReplyDraft(result.draft);
      setOpenReplyLead(leadId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yanıt taslağı üretilemedi");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleSendReplyDraft(leadId: string) {
    if (!replyDraft.trim()) return;
    setPendingAction(`send-reply-${leadId}`);
    setError(null);
    try {
      const result = await apiFetch<FollowUpResult>(`/leads/${leadId}/follow-up`, {
        method: "POST",
        body: JSON.stringify({ message: replyDraft.trim() }),
      });
      setFollowUpResultByLead((prev) => ({ ...prev, [leadId]: result.message }));
      setOpenReplyLead(null);
      setReplyDraft("");
      await loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Yanıt gönderilemedi");
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

  function handleToggleAppointmentForm(lead: Lead) {
    if (openAppointmentLead === lead.id) {
      setOpenAppointmentLead(null);
      return;
    }
    setOpenAppointmentLead(lead.id);
    setAppointmentDateTime(lead.appointment_at ? lead.appointment_at.slice(0, 16) : "");
    setAppointmentLocation(lead.appointment_location ?? "");
    setAppointmentSendWhatsapp(true);
  }

  async function handleCreateAppointment(lead: Lead) {
    if (!appointmentDateTime || !appointmentLocation.trim()) return;
    setPendingAction(`appointment-${lead.id}`);
    setError(null);
    try {
      const result = await apiFetch<AppointmentResult>(`/leads/${lead.id}/appointment`, {
        method: "POST",
        body: JSON.stringify({
          appointment_at: new Date(appointmentDateTime).toISOString(),
          location: appointmentLocation.trim(),
          send_whatsapp_confirmation: appointmentSendWhatsapp,
        }),
      });
      setLeads((prev) => prev.map((l) => (l.id === result.lead.id ? result.lead : l)));
      setAppointmentResultByLead((prev) => ({
        ...prev,
        [lead.id]: result.whatsapp_confirmation_sent
          ? "Randevu kaydedildi, WhatsApp onay mesajı gönderildi."
          : `Randevu kaydedildi. ${result.whatsapp_confirmation_error ?? ""}`,
      }));
      setOpenAppointmentLead(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Randevu kaydedilemedi");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleCancelAppointment(lead: Lead) {
    setPendingAction(`appointment-cancel-${lead.id}`);
    setError(null);
    try {
      const updated = await apiFetch<Lead>(`/leads/${lead.id}/appointment`, { method: "DELETE" });
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      setAppointmentResultByLead((prev) => {
        const next = { ...prev };
        delete next[lead.id];
        return next;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Randevu iptal edilemedi");
    } finally {
      setPendingAction(null);
    }
  }

  async function handleDownloadIcs(lead: Lead) {
    try {
      const blob = await apiFetchBlob(`/leads/${lead.id}/appointment.ics`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "randevu.ics";
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Devrimi bir sonraki tick'e ertele — hemen iptal edilirse tarayıcının
      // indirmeyi başlatması (özellikle otomasyon ortamlarında) yarışa girip
      // sessizce başarısız olabiliyor.
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Takvim daveti indirilemedi");
    }
  }

  function handleToggleDealForm(lead: Lead) {
    if (openDealLead === lead.id) {
      setOpenDealLead(null);
      return;
    }
    setOpenDealLead(lead.id);
    setDealAmount(lead.deal_amount != null ? String(lead.deal_amount) : "");
    setCommissionAmount(lead.commission_amount != null ? String(lead.commission_amount) : "");
    setDealClosedAt(lead.deal_closed_at ? lead.deal_closed_at.slice(0, 10) : "");
  }

  async function handleSaveDeal(lead: Lead) {
    setPendingAction(`deal-${lead.id}`);
    setError(null);
    try {
      const updated = await apiFetch<Lead>(`/leads/${lead.id}/deal`, {
        method: "PATCH",
        body: JSON.stringify({
          deal_amount: dealAmount ? Number(dealAmount) : null,
          commission_amount: commissionAmount ? Number(commissionAmount) : null,
          deal_closed_at: dealClosedAt ? new Date(dealClosedAt).toISOString() : null,
        }),
      });
      setLeads((prev) => prev.map((l) => (l.id === updated.id ? updated : l)));
      setOpenDealLead(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anlaşma kaydedilemedi");
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
            />
            <Input
              id="contactName"
              label="İsim (opsiyonel)"
              placeholder="Örn. Ayşe Yılmaz"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
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
            <div className="flex flex-col gap-1.5">
              <label htmlFor="listingTypePreference" className="text-body-sm text-text-muted">
                İşlem tipi
              </label>
              <select
                id="listingTypePreference"
                value={listingTypePreference}
                onChange={(e) => setListingTypePreference(e.target.value as ListingType | "")}
                className="h-10 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
              >
                <option value="">Fark etmez</option>
                <option value="sale">Satılık</option>
                <option value="rent">Kiralık</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="propertyTypePreference" className="text-body-sm text-text-muted">
                Emlak tipi
              </label>
              <select
                id="propertyTypePreference"
                value={propertyTypePreference}
                onChange={(e) => setPropertyTypePreference(e.target.value as PropertyType | "")}
                className="h-10 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
              >
                <option value="">Fark etmez</option>
                <option value="residential">Konut</option>
                <option value="commercial">İş Yeri</option>
                <option value="land">Arsa</option>
              </select>
            </div>
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
          const activeTab = activeTabByLead[lead.id] ?? null;
          return (
            <Card key={lead.id}>
              <CardContent className="flex flex-col gap-4 p-6">
                {/* Kimlik satırı: avatar + telefon + durum; sağda durum seçici + sil */}
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-mint-accent text-secondary">
                      <Phone className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-title-md text-[17px] leading-tight text-primary">
                        {lead.contact_name?.trim() || lead.contact_phone}
                      </p>
                      <p className="text-[12px] text-text-muted">
                        {lead.contact_name?.trim() ? `${lead.contact_phone} · ` : ""}
                        Eklendi: {new Date(lead.created_at).toLocaleDateString("tr-TR")}
                      </p>
                    </div>
                    <Badge variant={statusVariant(lead.status)}>
                      {LEAD_STATUS_LABELS[lead.status] ?? lead.status}
                    </Badge>
                    {score && (
                      <Badge variant={scoreVariant(score.score)}>
                        <Gauge className="h-3 w-3" />
                        {score.score}/100
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={lead.status}
                      onChange={(e) => handleStatusChange(lead.id, e.target.value as LeadStatus)}
                      aria-label="Aday durumu"
                      className="h-9 rounded-full border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
                    >
                      {Object.entries(LEAD_STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      aria-label="Adayı sil"
                      onClick={() => setPendingDeleteId(lead.id)}
                      className="flex h-9 w-9 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-error/10 hover:text-error"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {/* Kriter ve durum çipleri */}
                <div className="flex flex-wrap items-center gap-1.5">
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
                  {lead.listing_type_preference && (
                    <Badge variant="neutral">{LISTING_TYPE_PREFERENCE_LABELS[lead.listing_type_preference]}</Badge>
                  )}
                  {lead.property_type_preference && (
                    <Badge variant="neutral">{PROPERTY_TYPE_PREFERENCE_LABELS[lead.property_type_preference]}</Badge>
                  )}
                  {lead.fields_extracted_by_ai && (
                    <Badge variant="brand">
                      <Sparkles className="h-3 w-3" />
                      AI ile dolduruldu
                    </Badge>
                  )}
                  {lead.auto_follow_up_enabled && (
                    <Badge variant="brand">
                      <Repeat className="h-3 w-3" />
                      Otomatik takip açık
                    </Badge>
                  )}
                  {lead.reminder_at && (
                    <Badge variant="warning">
                      <Clock className="h-3 w-3" />
                      Hatırlatma {new Date(lead.reminder_at).toLocaleDateString("tr-TR")}
                      {lead.reminder_note ? `: ${lead.reminder_note}` : ""}
                    </Badge>
                  )}
                  {lead.appointment_at && (
                    <Badge variant="brand">
                      <CalendarPlus className="h-3 w-3" />
                      Randevu {new Date(lead.appointment_at).toLocaleString("tr-TR")}
                      {lead.appointment_location ? ` · ${lead.appointment_location}` : ""}
                    </Badge>
                  )}
                  {lead.commission_amount != null && (
                    <Badge variant="success">
                      <DollarSign className="h-3 w-3" />
                      Komisyon {formatCurrency(lead.commission_amount)}
                    </Badge>
                  )}
                </div>

                {/* Sekme çubuğu — işlevler mantıksal gruplara ayrıldı */}
                <div className="flex w-fit max-w-full flex-wrap gap-1 rounded-full bg-surface-container p-1">
                  {LEAD_TABS.map((tab) => (
                    <button
                      key={tab.key}
                      type="button"
                      onClick={() => handleSelectTab(lead.id, tab.key)}
                      className={`rounded-full px-4 py-1.5 text-body-sm font-medium transition-colors ${
                        activeTab === tab.key
                          ? "bg-primary text-on-primary shadow-sm"
                          : "text-text-muted hover:text-primary"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {activeTab === "eslestirme" && (
                  <p className="text-[12px] text-text-muted">
                    <b>Skorla</b>: yanıt hızı (%40), mesaj yoğunluğu (%30) ve bütçe netliği (%30)
                    üzerinden 0-100 arası bir öncelik puanı üretir — gün içinde hangi adaya önce
                    dönmeniz gerektiğini gösterir. <b>Eşleştir</b>: adayın kriterlerine uyan kendi
                    portföylerinizi bulur.
                  </p>
                )}
                {activeTab === "eslestirme" && (
                  <div className="flex flex-wrap gap-2">
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
                      isLoading={pendingAction === `send-matches-${lead.id}`}
                      onClick={() => handleSendMatches(lead.id)}
                    >
                      <Send className="h-3.5 w-3.5" />
                      Eşleşenleri WhatsApp'tan Gönder
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={pendingAction === `suggest-reply-${lead.id}`}
                      onClick={() => handleSuggestReply(lead.id)}
                    >
                      <Wand2 className="h-3.5 w-3.5" />
                      AI ile Yanıt Öner
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      isLoading={pendingAction === `reanalyze-${lead.id}`}
                      onClick={() => handleReanalyze(lead.id)}
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      Mesajlardan Yeniden Analiz
                    </Button>
                  </div>
                )}

                {activeTab === "eslestirme" && score && (
                  <div className="flex flex-wrap items-center gap-2 rounded bg-surface-bright p-3 text-[12px] text-on-surface">
                    <span className="font-semibold text-primary">Skor detayı:</span>
                    <Badge variant="neutral">
                      Yanıt hızı {Math.round(Number(score.score_breakdown?.response_speed_score ?? 0))}/100
                    </Badge>
                    <Badge variant="neutral">
                      Mesaj yoğunluğu {Math.round(Number(score.score_breakdown?.message_count_score ?? 0))}/100
                    </Badge>
                    <Badge variant="neutral">
                      Bütçe netliği {Math.round(Number(score.score_breakdown?.budget_consistency_score ?? 0))}/100
                    </Badge>
                  </div>
                )}

                {activeTab === "mesajlar" && (
                  <p className="text-[12px] text-text-muted">
                    <b>Otomatik takip</b>: aday yanıt vermezse 1, 3 ve 7 gün sonra giderek yumuşayan
                    3 hatırlatma mesajı WhatsApp&apos;tan otomatik gönderilir; aday yanıt verdiği anda
                    zincir kendiliğinden durur.
                    {lead.auto_follow_up_enabled && lead.next_follow_up_at && (
                      <>
                        {" "}
                        Sıradaki mesaj: <b>{new Date(lead.next_follow_up_at).toLocaleString("tr-TR")}</b>.
                      </>
                    )}
                  </p>
                )}
                {activeTab === "mesajlar" && (
                  <div className="flex flex-wrap gap-2">
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
                      {lead.auto_follow_up_enabled ? "Otomatik Takip: Açık" : "Otomatik Takibi Aç"}
                    </Button>
                  </div>
                )}

                {activeTab === "notlar" && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant={openVoiceNoteLead === lead.id ? "primary" : "outline"}
                      size="sm"
                      onClick={() => handleToggleVoiceNote(lead.id)}
                    >
                      <Mic className="h-3.5 w-3.5" />
                      Sesli Not
                    </Button>
                  </div>
                )}

                {activeTab === "randevu" && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant={lead.appointment_at ? "primary" : "outline"}
                      size="sm"
                      onClick={() => handleToggleAppointmentForm(lead)}
                    >
                      <CalendarPlus className="h-3.5 w-3.5" />
                      {lead.appointment_at ? "Randevuyu Düzenle" : "Randevu Planla"}
                    </Button>
                    {lead.appointment_at && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => handleDownloadIcs(lead)}>
                          <Download className="h-3.5 w-3.5" />
                          Takvime Ekle
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          isLoading={pendingAction === `appointment-cancel-${lead.id}`}
                          onClick={() => handleCancelAppointment(lead)}
                        >
                          <X className="h-3.5 w-3.5" />
                          Randevuyu İptal Et
                        </Button>
                      </>
                    )}
                    <Button
                      variant={lead.commission_amount != null ? "primary" : "outline"}
                      size="sm"
                      onClick={() => handleToggleDealForm(lead)}
                    >
                      <DollarSign className="h-3.5 w-3.5" />
                      {lead.commission_amount != null ? "Anlaşmayı Düzenle" : "Anlaşma Kaydet"}
                    </Button>
                  </div>
                )}

                {activeTab === "randevu" && openDealLead === lead.id && (
                  <div className="flex flex-col gap-3 rounded bg-surface-bright p-3">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <Input
                        id={`deal-amount-${lead.id}`}
                        label="Satış/kira bedeli (TL)"
                        type="number"
                        value={dealAmount}
                        onChange={(e) => setDealAmount(e.target.value)}
                      />
                      <Input
                        id={`commission-amount-${lead.id}`}
                        label="Komisyon (TL)"
                        type="number"
                        value={commissionAmount}
                        onChange={(e) => setCommissionAmount(e.target.value)}
                      />
                      <Input
                        id={`deal-closed-at-${lead.id}`}
                        label="Kapanış tarihi"
                        type="date"
                        value={dealClosedAt}
                        onChange={(e) => setDealClosedAt(e.target.value)}
                      />
                    </div>
                    <div className="flex justify-between">
                      <Button variant="ghost" size="sm" onClick={() => setOpenDealLead(null)}>
                        Vazgeç
                      </Button>
                      <Button
                        size="sm"
                        isLoading={pendingAction === `deal-${lead.id}`}
                        onClick={() => handleSaveDeal(lead)}
                      >
                        Kaydet
                      </Button>
                    </div>
                  </div>
                )}

                {activeTab === "randevu" && openAppointmentLead === lead.id && (
                  <div className="flex flex-col gap-3 rounded bg-surface-bright p-3">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <Input
                        id={`appointment-datetime-${lead.id}`}
                        label="Randevu tarihi ve saati"
                        type="datetime-local"
                        value={appointmentDateTime}
                        onChange={(e) => setAppointmentDateTime(e.target.value)}
                      />
                      <Input
                        id={`appointment-location-${lead.id}`}
                        label="Konum"
                        placeholder="Örn. Kadıköy, İstanbul"
                        value={appointmentLocation}
                        onChange={(e) => setAppointmentLocation(e.target.value)}
                      />
                    </div>
                    <label className="flex items-center gap-2 text-body-sm text-on-surface">
                      <input
                        type="checkbox"
                        checked={appointmentSendWhatsapp}
                        onChange={(e) => setAppointmentSendWhatsapp(e.target.checked)}
                      />
                      Adaya WhatsApp'tan onay mesajı gönder
                    </label>
                    <div className="flex justify-between">
                      <Button variant="ghost" size="sm" onClick={() => setOpenAppointmentLead(null)}>
                        Vazgeç
                      </Button>
                      <Button
                        size="sm"
                        isLoading={pendingAction === `appointment-${lead.id}`}
                        disabled={!appointmentDateTime || !appointmentLocation.trim()}
                        onClick={() => handleCreateAppointment(lead)}
                      >
                        Randevuyu Kaydet
                      </Button>
                    </div>
                  </div>
                )}

                {appointmentResultByLead[lead.id] && (
                  <div className="rounded bg-mint-accent p-3 text-body-sm text-on-secondary-container">
                    {appointmentResultByLead[lead.id]}
                  </div>
                )}

                {activeTab === "notlar" && openVoiceNoteLead === lead.id && (
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

                {activeTab === "notlar" && (
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

                {activeTab === "mesajlar" && (
                  <div className="flex flex-col gap-2 rounded bg-surface-bright p-3">
                    {(messagesByLead[lead.id] ?? []).length === 0 ? (
                      <p className="text-body-sm text-text-muted">Henüz WhatsApp mesajı yok.</p>
                    ) : (
                      <ul className="flex flex-col gap-2">
                        {(messagesByLead[lead.id] ?? []).map((message) => (
                          <li
                            key={message.id}
                            className={`max-w-[85%] rounded p-2.5 text-body-sm ${
                              message.direction === "in"
                                ? "self-start bg-surface-container-lowest text-on-surface"
                                : "self-end bg-mint-accent text-on-secondary-container"
                            }`}
                          >
                            <p>{message.body}</p>
                            <p className="mt-1 text-[11px] opacity-70">
                              {message.direction === "in" ? "Aday" : "Ofis"} ·{" "}
                              {new Date(message.created_at).toLocaleString("tr-TR")}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}

                {activeTab === "eslestirme" && openReanalyzeLead === lead.id && reanalyzeDraft && (
                  <div className="flex flex-col gap-3 rounded bg-surface-bright p-3">
                    <p className="text-body-sm text-text-muted">
                      Gemini, adayın WhatsApp mesajlarından bu alanları önerdi — göndermeden önce düzenleyebilirsiniz.
                    </p>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                      <Input
                        id={`reanalyze-district-${lead.id}`}
                        label="Bölge"
                        value={reanalyzeDraft.district ?? ""}
                        onChange={(e) => setReanalyzeDraft({ ...reanalyzeDraft, district: e.target.value || null })}
                      />
                      <Input
                        id={`reanalyze-budget-max-${lead.id}`}
                        label="Maks. bütçe (TL)"
                        type="number"
                        value={reanalyzeDraft.budget_max ?? ""}
                        onChange={(e) =>
                          setReanalyzeDraft({
                            ...reanalyzeDraft,
                            budget_max: e.target.value ? Number(e.target.value) : null,
                          })
                        }
                      />
                      <Input
                        id={`reanalyze-room-count-${lead.id}`}
                        label="Oda sayısı"
                        value={reanalyzeDraft.room_count ?? ""}
                        onChange={(e) => setReanalyzeDraft({ ...reanalyzeDraft, room_count: e.target.value || null })}
                      />
                      <Input
                        id={`reanalyze-radius-${lead.id}`}
                        label="Arama yarıçapı (km)"
                        type="number"
                        value={reanalyzeDraft.radius_km ?? ""}
                        onChange={(e) =>
                          setReanalyzeDraft({
                            ...reanalyzeDraft,
                            radius_km: e.target.value ? Number(e.target.value) : null,
                          })
                        }
                      />
                      <div className="flex flex-col gap-1.5">
                        <label htmlFor={`reanalyze-listing-type-${lead.id}`} className="text-body-sm text-text-muted">
                          İşlem tipi
                        </label>
                        <select
                          id={`reanalyze-listing-type-${lead.id}`}
                          value={reanalyzeDraft.listing_type_preference ?? ""}
                          onChange={(e) =>
                            setReanalyzeDraft({
                              ...reanalyzeDraft,
                              listing_type_preference: (e.target.value || null) as ListingType | null,
                            })
                          }
                          className="h-10 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
                        >
                          <option value="">Fark etmez</option>
                          <option value="sale">Satılık</option>
                          <option value="rent">Kiralık</option>
                        </select>
                      </div>
                      <div className="flex flex-col gap-1.5">
                        <label htmlFor={`reanalyze-property-type-${lead.id}`} className="text-body-sm text-text-muted">
                          Emlak tipi
                        </label>
                        <select
                          id={`reanalyze-property-type-${lead.id}`}
                          value={reanalyzeDraft.property_type_preference ?? ""}
                          onChange={(e) =>
                            setReanalyzeDraft({
                              ...reanalyzeDraft,
                              property_type_preference: (e.target.value || null) as PropertyType | null,
                            })
                          }
                          className="h-10 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
                        >
                          <option value="">Fark etmez</option>
                          <option value="residential">Konut</option>
                          <option value="commercial">İş Yeri</option>
                          <option value="land">Arsa</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex justify-between">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setOpenReanalyzeLead(null);
                          setReanalyzeDraft(null);
                        }}
                      >
                        Vazgeç
                      </Button>
                      <Button
                        size="sm"
                        isLoading={pendingAction === `apply-reanalyze-${lead.id}`}
                        onClick={() => handleApplyReanalyzeDraft(lead.id)}
                      >
                        Uygula
                      </Button>
                    </div>
                  </div>
                )}

                {activeTab === "eslestirme" && openReplyLead === lead.id && (
                  <div className="flex flex-col gap-3 rounded bg-surface-bright p-3">
                    <p className="text-body-sm text-text-muted">
                      Gemini, mevcut portföylerinize dayanarak bir yanıt taslağı üretti — göndermeden önce düzenleyebilirsiniz.
                    </p>
                    <textarea
                      value={replyDraft}
                      onChange={(e) => setReplyDraft(e.target.value)}
                      rows={4}
                      className="w-full rounded border border-outline-variant bg-surface-container-lowest p-2.5 text-body-sm text-on-surface focus:border-secondary focus:outline-none"
                    />
                    <div className="flex justify-between">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setOpenReplyLead(null);
                          setReplyDraft("");
                        }}
                      >
                        Vazgeç
                      </Button>
                      <Button
                        size="sm"
                        isLoading={pendingAction === `send-reply-${lead.id}`}
                        onClick={() => handleSendReplyDraft(lead.id)}
                      >
                        <Send className="h-3.5 w-3.5" />
                        Gönder
                      </Button>
                    </div>
                  </div>
                )}

                {followUpResultByLead[lead.id] && (
                  <div className="rounded bg-mint-accent p-3 text-body-sm text-on-secondary-container">
                    Gönderildi: &ldquo;{followUpResultByLead[lead.id]}&rdquo;
                  </div>
                )}

                {activeTab === "eslestirme" && matches && (
                  <div className="rounded-lg bg-surface-bright p-4">
                    {matches.length === 0 ? (
                      <p className="text-body-sm text-text-muted">
                        Uygun portföy bulunamadı — kriterleri genişletmeyi (yarıçap, bütçe) deneyin.
                      </p>
                    ) : (
                      <ul className="flex flex-col gap-2">
                        {matches.map((match) => (
                          <li
                            key={match.listing_id}
                            className="flex flex-col gap-0.5 rounded bg-surface-container-lowest p-3"
                          >
                            <div className="flex items-center justify-between gap-3 text-body-sm text-on-surface">
                              <span className="font-medium">{match.title}</span>
                              <div className="flex shrink-0 items-center gap-2">
                                {match.relevance_score != null && (
                                  <Badge variant={scoreVariant(match.relevance_score)}>
                                    %{match.relevance_score} uygun
                                  </Badge>
                                )}
                                <span className="font-semibold text-primary">{formatCurrency(match.price)}</span>
                              </div>
                            </div>
                            {match.match_reason && (
                              <p className="text-[12px] text-text-muted">{match.match_reason}</p>
                            )}
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

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Adayı sil"
        description="Bu adayı kalıcı olarak silmek istediğinize emin misiniz? Bu işlem geri alınamaz."
        isLoading={pendingDeleteId !== null && pendingAction === `delete-${pendingDeleteId}`}
        onConfirm={() => pendingDeleteId && handleDeleteLead(pendingDeleteId)}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}
