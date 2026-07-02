import type { Metadata } from "next";
import { Inter } from "next/font/google";
import NavBar from "@/components/NavBar";
import { PageContainer } from "@/components/PageContainer";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "PortföyAI",
  description: "Emlak danışmanı için AI kapanış asistanı",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={inter.variable}>
      <body className="min-h-screen bg-slate-50 font-sans text-slate-900">
        <NavBar />
        <PageContainer>{children}</PageContainer>
      </body>
    </html>
  );
}
