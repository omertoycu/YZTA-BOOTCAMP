"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { buttonVariants } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";

export function Hero() {
  return (
    <section className="relative flex min-h-[92vh] w-full flex-col overflow-hidden bg-primary">
      <video
        className="absolute inset-0 h-full w-full object-cover opacity-80"
        src="/hero-villa.mp4"
        poster="/hero-villa-poster.jpg"
        autoPlay
        muted
        loop
        playsInline
      />
      <div className="absolute inset-0 bg-gradient-to-b from-primary/70 via-primary/40 to-background" />
      <div className="absolute inset-0 bg-gradient-to-r from-primary/60 via-transparent to-transparent" />

      <nav className="relative z-10 flex items-center justify-between px-6 py-6 md:px-12">
        <span className="text-title-md font-black tracking-tight text-on-primary">PortföyAI</span>
        <Link
          href="/login"
          className="rounded-full border border-on-primary/30 px-5 py-2 text-body-sm font-medium text-on-primary transition-colors hover:bg-on-primary/10"
        >
          Giriş Yap
        </Link>
      </nav>

      <div className="relative z-10 flex flex-1 flex-col justify-center px-6 md:px-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.21, 0.47, 0.32, 0.98] }}
          className="max-w-2xl"
        >
          <span className="mb-4 inline-flex w-fit items-center gap-2 rounded-full bg-on-primary/10 px-4 py-1.5 text-label-caps text-on-primary backdrop-blur-sm">
            Emlak Danışmanı için AI Kapanış Asistanı
          </span>
          <h1 className="text-display-lg text-on-primary sm:text-[56px] sm:leading-[60px]">
            İlk WhatsApp mesajından imzaya kadar hiçbir fırsatı kaçırmayın
          </h1>
          <p className="mt-6 max-w-lg text-body-lg text-on-primary/80">
            PortföyAI, emlak danışmanlarının WhatsApp&apos;tan gelen hiçbir müşteriyi kaçırmadan doğru
            alıcıyı doğru portföyle buluşturmasını sağlayan bir yapay zeka asistanı.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/login"
              className={cn(buttonVariants({ size: "lg" }), "bg-on-primary text-primary hover:opacity-90")}
            >
              Ücretsiz Dene
            </Link>
            <a
              href="#nasil-calisir"
              className="inline-flex items-center gap-2 text-body-lg font-medium text-on-primary/90 hover:text-on-primary"
            >
              Nasıl çalışır
              <Icon name="arrow_downward" />
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25, ease: [0.21, 0.47, 0.32, 0.98] }}
          className="mb-10 mt-16 flex max-w-sm items-center gap-3 self-start rounded-lg bg-surface-container-lowest/95 p-3 shadow-[0px_10px_30px_rgba(0,0,0,0.15)] backdrop-blur-sm"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-mint-accent text-secondary">
            <Icon name="apartment" />
          </div>
          <div className="flex-1">
            <p className="text-title-md leading-tight text-primary">Boğaz Manzaralı Villa</p>
            <p className="text-body-sm text-text-muted">4+1 · Sarıyer</p>
          </div>
          <span className="rounded-full bg-primary px-3 py-1 text-label-caps text-on-primary">Aktif</span>
        </motion.div>
      </div>
    </section>
  );
}
