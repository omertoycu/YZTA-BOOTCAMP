"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getToken } from "@/lib/api";

export default function NavBar() {
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

  const links = [
    { href: "/listings", label: "Portföyler" },
    { href: "/leads", label: "Lead'ler" },
  ];

  return (
    <nav className="flex items-center justify-between border-b border-gray-200 px-6 py-3">
      <div className="flex items-center gap-6">
        <span className="font-semibold text-gray-900">PortföyAI</span>
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`text-sm ${
              pathname?.startsWith(link.href) ? "font-medium text-gray-900" : "text-gray-500 hover:text-gray-900"
            }`}
          >
            {link.label}
          </Link>
        ))}
      </div>
      <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-900">
        Çıkış yap
      </button>
    </nav>
  );
}
