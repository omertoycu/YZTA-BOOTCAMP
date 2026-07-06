"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { apiFetch, clearToken, getToken } from "@/lib/api";
import type { Office } from "@/lib/types";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { href: "/listings", label: "İlanlar", icon: "home_work" },
  { href: "/listings/import", label: "Portföy Aktar", icon: "cloud_download" },
  { href: "/leads", label: "Adaylar", icon: "group" },
  { href: "/assistant", label: "YZ Asistanı", icon: "psychology" },
  { href: "/reports", label: "Reports", icon: "assessment" },
  { href: "/billing", label: "Abonelik", icon: "credit_card" },
  { href: "/settings", label: "Ayarlar", icon: "settings" },
];

export function Sidebar() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [office, setOffice] = useState<Office | null>(null);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    setIsAuthenticated(Boolean(getToken()));
  }, [pathname]);

  // Hangi ofis hesabıyla giriş yapıldığı arayüzde hiçbir yerde
  // belirtilmiyordu — sidebar her sayfada göründüğü için burada tek seferden
  // çekilip footer'da (ve /profile'da) gösteriliyor.
  useEffect(() => {
    if (!isAuthenticated) return;
    apiFetch<Office>("/offices/me")
      .then(setOffice)
      .catch(() => setOffice(null));
  }, [isAuthenticated]);

  // Sayfa değiştiğinde mobil açılır menüyü otomatik kapat.
  useEffect(() => {
    setIsMobileOpen(false);
  }, [pathname]);

  if (!isAuthenticated) return null;

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  function handleVoiceToListing() {
    router.push("/assistant");
  }

  function renderNavLinks() {
    // "/listings/import" da "/listings"'in prefix'i olduğu için basit
    // startsWith ikisini birden aktif gösterirdi — en uzun eşleşen href'i
    // tek aktif sekme olarak seçiyoruz.
    const activeHref = NAV_LINKS.filter((l) => pathname?.startsWith(l.href)).sort(
      (a, b) => b.href.length - a.href.length
    )[0]?.href;

    return (
      <ul className="flex flex-1 flex-col gap-2">
        {NAV_LINKS.map((link) => {
          const isActive = link.href === activeHref;
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
    );
  }

  function renderFooter() {
    return (
      <div className="mt-auto border-t border-surface-variant pt-6">
        <Link
          href="/profile"
          className="mb-4 flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors hover:bg-surface-container-low"
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-mint-accent text-sm font-semibold text-secondary">
            {office?.name?.charAt(0).toUpperCase() ?? <Icon name="apartment" className="text-[18px]" />}
          </div>
          <div className="flex-1 overflow-hidden">
            <p className="truncate text-body-sm font-medium text-on-surface">
              {office?.name ?? "Yükleniyor..."}
            </p>
            <p className="truncate text-[11px] text-text-muted">Hesap ve profil bilgileri</p>
          </div>
        </Link>
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
    );
  }

  return (
    <>
      {/* Masaüstü sabit sidebar */}
      <nav className="fixed left-0 top-0 z-40 hidden h-full w-72 flex-col bg-surface-container-lowest p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] md:flex">
        <Link href="/" className="mb-12 block w-fit">
          <h1 className="text-headline-lg font-black tracking-tight text-primary">PortföyAI</h1>
          <p className="mt-1 text-body-sm text-on-surface-variant">Closing Assistant</p>
        </Link>
        {renderNavLinks()}
        {renderFooter()}
      </nav>

      {/* Mobil üst bar — sidebar md altında tamamen gizli olduğu için tek
          navigasyon yolu bu; hamburger'a basınca açılır menü render edilir. */}
      <div className="fixed left-0 right-0 top-0 z-40 flex items-center justify-between bg-surface-container-lowest px-4 py-3 shadow-[0px_4px_20px_rgba(0,0,0,0.06)] md:hidden">
        <Link href="/" className="text-title-md font-black tracking-tight text-primary">
          PortföyAI
        </Link>
        <button
          type="button"
          onClick={() => setIsMobileOpen(true)}
          aria-label="Menüyü aç"
          className="flex h-10 w-10 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low"
        >
          <Menu className="h-6 w-6" />
        </button>
      </div>

      {/* Mobil açılır menü (drawer) */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setIsMobileOpen(false)} />
          <nav className="relative flex h-full w-72 flex-col bg-surface-container-lowest p-6 shadow-xl">
            <div className="mb-8 flex items-center justify-between">
              <Link href="/" className="text-headline-lg font-black tracking-tight text-primary">
                PortföyAI
              </Link>
              <button
                type="button"
                onClick={() => setIsMobileOpen(false)}
                aria-label="Menüyü kapat"
                className="flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-low"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {renderNavLinks()}
            {renderFooter()}
          </nav>
        </div>
      )}
    </>
  );
}
