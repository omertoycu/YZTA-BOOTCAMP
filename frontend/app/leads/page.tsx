"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getToken } from "@/lib/api";
import type { Lead, LeadScore, MatchResult } from "@/lib/types";

export default function LeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoresByLead, setScoresByLead] = useState<Record<string, LeadScore>>({});
  const [matchesByLead, setMatchesByLead] = useState<Record<string, MatchResult[]>>({});

  const [contactPhone, setContactPhone] = useState("");
  const [district, setDistrict] = useState("");
  const [budgetMax, setBudgetMax] = useState("");
  const [roomCount, setRoomCount] = useState("2+1");

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
        }),
      });
      setContactPhone("");
      setDistrict("");
      setBudgetMax("");
      await loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lead eklenemedi");
    }
  }

  async function handleScore(leadId: string) {
    try {
      const score = await apiFetch<LeadScore>(`/leads/${leadId}/score`, { method: "POST" });
      setScoresByLead((prev) => ({ ...prev, [leadId]: score }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Skor hesaplanamadı");
    }
  }

  async function handleMatch(leadId: string) {
    try {
      const matches = await apiFetch<MatchResult[]>(`/leads/${leadId}/match`, { method: "POST" });
      setMatchesByLead((prev) => ({ ...prev, [leadId]: matches }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eşleştirme yapılamadı");
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Lead&apos;ler</h1>

      <form onSubmit={handleCreate} className="mb-8 flex flex-wrap items-end gap-3 rounded border border-gray-200 p-4">
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Telefon</label>
          <input
            required
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Bölge</label>
          <input
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Maks. bütçe (TL)</label>
          <input
            type="number"
            value={budgetMax}
            onChange={(e) => setBudgetMax(e.target.value)}
            className="w-32 rounded border border-gray-300 px-2 py-1"
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs text-gray-500">Oda sayısı</label>
          <input
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
        {leads.map((lead) => {
          const score = scoresByLead[lead.id];
          const matches = matchesByLead[lead.id];
          return (
            <div key={lead.id} className="rounded border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{lead.contact_phone}</p>
                  <p className="text-sm text-gray-500">
                    {lead.district ?? "Bölge belirtilmedi"} · {lead.room_count ?? "-"} ·{" "}
                    {lead.budget_max ? `${lead.budget_max.toLocaleString("tr-TR")} TL'ye kadar` : "Bütçe belirtilmedi"}
                  </p>
                </div>
                <div className="flex gap-3 text-sm">
                  <button onClick={() => handleScore(lead.id)} className="text-gray-500 underline hover:text-gray-900">
                    Skorla
                  </button>
                  <button onClick={() => handleMatch(lead.id)} className="text-gray-500 underline hover:text-gray-900">
                    Eşleştir
                  </button>
                </div>
              </div>
              {score && (
                <p className="mt-2 text-sm text-gray-600">
                  Skor: <span className="font-medium">{score.score}/100</span>
                </p>
              )}
              {matches && (
                <ul className="mt-2 list-inside list-disc text-sm text-gray-600">
                  {matches.length === 0 && <li>Uygun portföy bulunamadı.</li>}
                  {matches.map((match) => (
                    <li key={match.listing_id}>
                      {match.title} — {match.price.toLocaleString("tr-TR")} TL
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
        {!isLoading && leads.length === 0 && <p className="text-sm text-gray-500">Henüz lead eklenmedi.</p>}
      </div>
    </div>
  );
}
