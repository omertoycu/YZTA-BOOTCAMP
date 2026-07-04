"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { href: "/listings", label: "İlanlar", icon: "home_work" },
  { href: "/leads", label: "Adaylar", icon: "group" },
  { href: "/assistant", label: "YZ Asistanı", icon: "psychology" },
  { href: "/reports", label: "Reports", icon: "assessment" },
  { href: "/billing", label: "Abonelik", icon: "credit_card" },
];

export function Sidebar() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    setIsAuthenticated(Boolean(getToken()));
  }, [pathname]);

  if (!isAuthenticated) return null;

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  function handleVoiceToListing() {
    router.push("/assistant");
  }

  return (
    <nav className="fixed left-0 top-0 z-40 hidden h-full w-72 flex-col bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] md:flex">
      <div className="mb-12">
        <h1 className="text-headline-lg font-black tracking-tight text-primary">PortföyAI</h1>
        <p className="mt-1 text-body-sm text-on-surface-variant">Closing Assistant</p>
      </div>

      <ul className="flex flex-1 flex-col gap-2">
        {NAV_LINKS.map((link) => {
          const isActive = pathname?.startsWith(link.href);
          return (
            <li key={link.href}>
              <Link
                href={link.href}
                className={cn(
                  "flex items-center gap-4 rounded-xl px-4 py-3 font-medium transition-all duration-200",
                  isActive
                    ? "bg-mint-accent font-bold text-primary"
                    : "text-on-surface-variant hover:bg-mint-accent/50"
                )}
              >
                <Icon name={link.icon} filled={isActive} />
                <span className="text-title-md text-[16px]">{link.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-auto border-t border-surface-variant pt-6">
        <button
          onClick={handleVoiceToListing}
          className="mb-6 flex w-full items-center justify-center gap-2 rounded-full bg-primary px-6 py-4 text-on-primary shadow-md transition-all hover:shadow-lg"
        >
          <Icon name="mic" />
          <span className="text-label-caps">Voice-to-Listing</span>
        </button>
        <ul className="flex flex-col gap-2">
          <li>
            <button className="flex w-full items-center gap-4 rounded-xl px-4 py-2 text-on-surface-variant transition-colors hover:bg-surface-container-low">
              <Icon name="help" />
              <span className="text-body-sm">Support</span>
            </button>
          </li>
          <li>
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-4 rounded-xl px-4 py-2 text-on-surface-variant transition-colors hover:bg-surface-container-low"
            >
              <Icon name="logout" />
              <span className="text-body-sm">Çıkış yap</span>
            </button>
          </li>
        </ul>
      </div>
    </nav>
  );
}
