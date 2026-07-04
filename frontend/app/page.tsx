"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import { Spinner } from "@/components/ui/Spinner";
import { LandingPage } from "@/components/landing/LandingPage";

export default function HomePage() {
  const router = useRouter();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    if (getToken()) {
      setIsAuthenticated(true);
      router.replace("/dashboard");
      return;
    }
    setCheckingAuth(false);
  }, [router]);

  if (checkingAuth || isAuthenticated) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  return <LandingPage />;
}
