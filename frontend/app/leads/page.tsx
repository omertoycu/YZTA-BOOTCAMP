"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Gauge, MapPin, Phone, Plus, Sparkles, Users, Wallet } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { Lead, LeadScore, MatchResult } from "@/lib/types";
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

export default function LeadsPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoresByLead, setScoresByLead] = useState<Record<string, LeadScore>>({});
  const [matchesByLead, setMatchesByLead] = useState<Record<string, MatchResult[]>>({});
  const [pendingAction, setPendingAction] = useState<string | null>(null);

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

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Lead&apos;ler</h1>
        <p className="mt-1 text-sm text-slate-500">
          Gelen talepleri skorlayın, en uygun portföyle eşleştirin.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Yeni lead ekle</CardTitle>
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
            <Button type="submit" className="lg:col-span-5 lg:w-fit">
              <Plus className="h-4 w-4" />
              Lead ekle
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

      {!isLoading && leads.length === 0 && (
        <EmptyState
          icon={Users}
          title="Henüz lead eklenmedi"
          description="Yukarıdaki formu kullanarak ilk lead'inizi ekleyin."
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
                    <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                      <Phone className="h-4 w-4 text-slate-400" />
                      {lead.contact_phone}
                    </div>
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
                      {score && (
                        <Badge variant={scoreVariant(score.score)}>
                          <Gauge className="h-3 w-3" />
                          Skor: {score.score}/100
                        </Badge>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2">
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
                  </div>
                </div>

                {matches && (
                  <div className="rounded-lg bg-slate-50 p-3">
                    {matches.length === 0 ? (
                      <p className="text-sm text-slate-500">Uygun portföy bulunamadı.</p>
                    ) : (
                      <ul className="flex flex-col gap-1.5">
                        {matches.map((match) => (
                          <li
                            key={match.listing_id}
                            className="flex items-center justify-between text-sm text-slate-700"
                          >
                            <span>{match.title}</span>
                            <span className="font-medium text-slate-900">{formatCurrency(match.price)}</span>
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
