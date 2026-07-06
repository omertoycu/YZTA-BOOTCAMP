"use client";

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";
import { LandingPage } from "@/components/landing/LandingPage";

// Girişli kullanıcı da bu sayfayı görebilmeli — sidebar'daki "PortföyAI"
// logosu buraya bağlanıyor (uygulamanın "reklam yüzü"), bu yüzden artık
// otomatik /dashboard'a yönlendirme YOK. Sadece CTA'lar isAuthenticated'a
// göre "Panele Git"e dönüşüyor (bkz. Hero/CTASection).
export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setIsAuthenticated(Boolean(getToken()));
  }, []);

  return <LandingPage isAuthenticated={isAuthenticated} />;
}
