"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setToken } from "@/lib/api";

type Mode = "login" | "register";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [officeName, setOfficeName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      router.push("/listings");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bir hata oluştu");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="mb-6 text-2xl font-semibold">
        {mode === "login" ? "Ofis Girişi" : "Ofis Kaydı"}
      </h1>

      <div className="mb-6 flex gap-4 text-sm">
        <button
          className={mode === "login" ? "font-medium text-gray-900" : "text-gray-400"}
          onClick={() => setMode("login")}
        >
          Giriş yap
        </button>
        <button
          className={mode === "register" ? "font-medium text-gray-900" : "text-gray-400"}
          onClick={() => setMode("register")}
        >
          Yeni ofis kaydet
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {mode === "register" && (
          <input
            required
            placeholder="Ofis adı"
            value={officeName}
            onChange={(e) => setOfficeName(e.target.value)}
            className="rounded border border-gray-300 px-3 py-2"
          />
        )}
        <input
          required
          type="email"
          placeholder="E-posta"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border border-gray-300 px-3 py-2"
        />
        <input
          required
          type="password"
          placeholder="Şifre"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border border-gray-300 px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-gray-900 px-3 py-2 text-white disabled:opacity-50"
        >
          {mode === "login" ? "Giriş yap" : "Kaydol"}
        </button>
      </form>
    </div>
  );
}
