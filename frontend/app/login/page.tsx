"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { apiFetch, setToken } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { InteractiveDots } from "@/components/InteractiveDots";
import { cn } from "@/lib/utils";

type Mode = "login" | "register";

const VALUE_PROPS = [
  "İlk WhatsApp mesajından imzaya kadar hiçbir fırsatı kaçırmayın",
  "Adaylarınızı otomatik skorlayın, en sıcak müşteriye önce dönün",
  "Portföyünüze uygun alıcıyı saniyeler içinde eşleştirin",
];

// Backend'deki validate_password_strength ile aynı kurallar (bkz.
// app/schemas/auth.py) — burada tekrarlanıyor çünkü kullanıcı şifreyi
// yazarken anında geri bildirim istiyoruz, backend'e her tuşta istek atmadan.
const PASSWORD_RULES: { label: string; test: (v: string) => boolean }[] = [
  { label: "En az 8 karakter", test: (v) => v.length >= 8 },
  { label: "En az bir büyük harf", test: (v) => /[A-ZÇĞİÖŞÜ]/.test(v) },
  { label: "En az bir küçük harf", test: (v) => /[a-zçğıöşü]/.test(v) },
  { label: "En az bir rakam", test: (v) => /\d/.test(v) },
  { label: "En az bir özel karakter (!@#$% gibi)", test: (v) => /[^\w\s]/.test(v) },
];

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [officeName, setOfficeName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const passwordRuleResults = PASSWORD_RULES.map((rule) => rule.test(password));
  const isPasswordStrong = passwordRuleResults.every(Boolean);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const payload =
        mode === "login"
          ? { email, password }
          : { office_name: officeName, owner_email: email, owner_password: password };

      const { access_token } = await apiFetch<{ access_token: string }>(path, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setToken(access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bir hata oluştu");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-primary via-inverse-surface to-secondary p-12 text-on-primary lg:flex">
        <InteractiveDots />
        <div className="relative">
          <h1 className="text-headline-lg font-black tracking-tight">PortföyAI</h1>
          <p className="mt-1 text-body-sm text-white/70">Closing Assistant</p>
        </div>

        <div className="relative flex flex-col gap-6">
          <h1 className="max-w-md text-3xl font-semibold leading-tight">
            Emlak danışmanının dijital kapanış asistanı
          </h1>
          <ul className="flex flex-col gap-3">
            {VALUE_PROPS.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-body-sm text-white/90">
                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-white" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/60">1-5 danışmanlı bağımsız emlak ofisleri için.</p>
      </div>

      <div className="flex flex-col items-center justify-center bg-background px-6 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center lg:hidden">
            <h1 className="text-headline-lg font-black tracking-tight text-primary">PortföyAI</h1>
          </div>

          <div className="mb-6 flex gap-1 rounded-full bg-surface-container p-1 text-sm">
            <button
              type="button"
              onClick={() => setMode("login")}
              className={cn(
                "flex-1 rounded-full py-1.5 font-medium transition-colors",
                mode === "login" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-text-muted hover:text-on-surface"
              )}
            >
              Giriş yap
            </button>
            <button
              type="button"
              onClick={() => setMode("register")}
              className={cn(
                "flex-1 rounded-full py-1.5 font-medium transition-colors",
                mode === "register" ? "bg-surface-container-lowest text-primary shadow-sm" : "text-text-muted hover:text-on-surface"
              )}
            >
              Yeni ofis kaydet
            </button>
          </div>

          <h2 className="mb-1 text-title-md text-primary">
            {mode === "login" ? "Tekrar hoş geldiniz" : "Ofisinizi oluşturun"}
          </h2>
          <p className="mb-6 text-body-sm text-text-muted">
            {mode === "login"
              ? "Devam etmek için ofis hesabınıza giriş yapın."
              : "Birkaç saniyede ofisinizi kaydedip başlayın."}
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {mode === "register" && (
              <Input
                id="officeName"
                label="Ofis adı"
                required
                placeholder="Örn. Merkez Gayrimenkul"
                value={officeName}
                onChange={(e) => setOfficeName(e.target.value)}
              />
            )}
            <Input
              id="email"
              label="E-posta"
              required
              type="email"
              placeholder="ornek@ofis.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Input
              id="password"
              label="Şifre"
              required
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            {mode === "register" && password.length > 0 && (
              <ul className="flex flex-col gap-1">
                {PASSWORD_RULES.map((rule, i) => (
                  <li
                    key={rule.label}
                    className={cn(
                      "flex items-center gap-1.5 text-[12px]",
                      passwordRuleResults[i] ? "text-emerald-700" : "text-text-muted"
                    )}
                  >
                    <CheckCircle2 className={cn("h-3.5 w-3.5", passwordRuleResults[i] ? "text-emerald-600" : "text-outline-variant")} />
                    {rule.label}
                  </li>
                ))}
              </ul>
            )}

            {error && <Alert>{error}</Alert>}

            <Button
              type="submit"
              size="lg"
              isLoading={isSubmitting}
              disabled={mode === "register" && !isPasswordStrong}
              className="mt-1 w-full"
            >
              {mode === "login" ? "Giriş yap" : "Kaydol"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
