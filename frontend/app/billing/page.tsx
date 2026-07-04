"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BadgeCheck, CreditCard } from "lucide-react";
import { apiFetch, getToken } from "@/lib/api";
import type { CheckoutResult, PlanInfo } from "@/lib/types";
import { formatCurrency } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";

const CALLBACK_MESSAGES: Record<string, { tone: "success" | "error"; text: string }> = {
  success: { tone: "success", text: "Ödemeniz alındı, planınız güncellendi. Hoş geldiniz!" },
  failed: { tone: "error", text: "Ödeme tamamlanamadı. Kart bilgilerinizi kontrol edip tekrar deneyin." },
  error: { tone: "error", text: "Ödeme doğrulanırken bir sorun oluştu. Hesabınızdan para çekildiyse bize ulaşın." },
};

function BillingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackStatus = searchParams.get("status");

  const [plans, setPlans] = useState<PlanInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingPlan, setPendingPlan] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    loadPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadPlans() {
    setIsLoading(true);
    try {
      const data = await apiFetch<PlanInfo[]>("/billing/plans");
      setPlans(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Planlar yüklenemedi");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCheckout(planId: string) {
    setPendingPlan(planId);
    setError(null);
    try {
      const result = await apiFetch<CheckoutResult>("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ plan: planId }),
      });
      // Ödeme iyzico'nun barındırdığı sayfada tamamlanır; dönüşte backend
      // callback'i bizi /billing?status=... adresine geri yönlendirir.
      window.location.href = result.payment_page_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ödeme başlatılamadı");
      setPendingPlan(null);
    }
  }

  const callbackMessage = callbackStatus ? CALLBACK_MESSAGES[callbackStatus] : null;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-headline-lg text-primary">Abonelik</h1>
        <p className="mt-1 text-body-sm text-text-muted">
          Ofisinize uygun planı seçin. Ödemeler iyzico güvencesiyle alınır, dilediğiniz zaman plan değiştirebilirsiniz.
        </p>
      </div>

      {callbackMessage && (
        <Alert
          className={
            callbackMessage.tone === "success"
              ? "border-mint-accent bg-mint-accent text-on-secondary-container"
              : undefined
          }
        >
          {callbackMessage.text}
        </Alert>
      )}
      {error && <Alert>{error}</Alert>}

      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-16 text-body-sm text-text-muted">
          <Spinner />
          Yükleniyor...
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.id} className={plan.is_current ? "ring-2 ring-primary" : undefined}>
            <CardContent className="flex h-full flex-col gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-title-lg font-bold text-primary">{plan.name}</h2>
                {plan.is_current && (
                  <Badge variant="brand">
                    <BadgeCheck className="h-3 w-3" />
                    Mevcut plan
                  </Badge>
                )}
              </div>
              <p className="text-headline-lg font-black text-on-surface">
                {plan.monthly_price === 0 ? "Ücretsiz" : `${formatCurrency(plan.monthly_price)}/ay`}
              </p>
              <ul className="flex flex-1 flex-col gap-2">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-body-sm text-on-surface">
                    <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    {feature}
                  </li>
                ))}
              </ul>
              {plan.monthly_price > 0 && !plan.is_current && (
                <Button
                  isLoading={pendingPlan === plan.id}
                  onClick={() => handleCheckout(plan.id)}
                >
                  <CreditCard className="h-4 w-4" />
                  {plan.name} planına geç
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function BillingPage() {
  // useSearchParams, Next.js'te Suspense sınırı gerektirir (aksi halde build
  // sırasında prerender hatası verir).
  return (
    <Suspense fallback={null}>
      <BillingContent />
    </Suspense>
  );
}
