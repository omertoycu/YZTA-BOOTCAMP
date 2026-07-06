"use client";

import { useRef } from "react";
import Link from "next/link";
import {
  motion,
  useMotionValueEvent,
  useScroll,
  useSpring,
  useTransform,
  type MotionValue,
} from "framer-motion";
import { buttonVariants } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";

/**
 * Scroll-scrub hero: video sayfaya sabitlenir, kullanıcı kaydırdıkça
 * videonun currentTime'ı scroll ilerlemesiyle senkron ilerler
 * (video dosyası her karesi keyframe olacak şekilde encode edildi,
 * aksi halde seek'ler kare atlar). Metin fazları da aynı ilerlemeye bağlı.
 */

const PHASES = [
  {
    range: [0.02, 0.08, 0.2, 0.26] as const,
    kicker: "Emlak Danışmanı için AI Kapanış Asistanı",
    title: "İlk mesajdan imzaya, hiçbir fırsatı kaçırmayın",
  },
  {
    range: [0.32, 0.38, 0.5, 0.56] as const,
    kicker: "Sesli Not → İlan",
    title: "Sesli notunuz, saniyeler içinde ilana dönüşür",
  },
  {
    range: [0.6, 0.66, 0.78, 0.84] as const,
    kicker: "Akıllı Eşleştirme",
    title: "Her aday otomatik puanlanır, doğru portföyle buluşur",
  },
] as const;

function Phase({
  progress,
  range,
  kicker,
  title,
}: {
  progress: MotionValue<number>;
  range: readonly [number, number, number, number];
  kicker: string;
  title: string;
}) {
  const opacity = useTransform(progress, [...range], [0, 1, 1, 0]);
  const y = useTransform(progress, [range[0], range[1]], [40, 0]);

  return (
    <motion.div
      style={{ opacity, y }}
      className="absolute inset-x-6 top-1/2 -translate-y-1/2 md:inset-x-12"
    >
      <div className="mx-auto max-w-4xl">
        <p className="mb-4 text-label-caps tracking-[0.2em] text-on-primary/80 [text-shadow:0_1px_12px_rgba(0,0,0,0.5)]">
          {kicker}
        </p>
        <h2 className="max-w-2xl text-display-lg text-on-primary [text-shadow:0_2px_28px_rgba(0,0,0,0.55)] sm:text-[64px] sm:leading-[70px]">
          {title}
        </h2>
      </div>
    </motion.div>
  );
}

export function Hero({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });
  const progress = useSpring(scrollYProgress, { stiffness: 140, damping: 28, mass: 0.4 });

  useMotionValueEvent(progress, "change", (v) => {
    const video = videoRef.current;
    if (!video || !video.duration || Number.isNaN(video.duration)) return;
    video.currentTime = Math.min(v, 1) * (video.duration - 0.001);
  });

  const hintOpacity = useTransform(progress, [0, 0.06], [1, 0]);

  // Final faz: CTA
  const ctaOpacity = useTransform(progress, [0.86, 0.93], [0, 1]);
  const ctaY = useTransform(progress, [0.86, 0.93], [40, 0]);

  return (
    <section ref={containerRef} className="relative h-[450vh] bg-primary">
      <div className="sticky top-0 h-screen overflow-hidden">
        <video
          ref={videoRef}
          className="absolute inset-0 h-full w-full object-cover"
          src="/hero-villa.mp4"
          poster="/hero-villa-poster.jpg"
          preload="auto"
          muted
          playsInline
        />
        <div className="absolute inset-0 bg-gradient-to-t from-primary/55 via-transparent to-primary/45" />
        <div className="absolute inset-0 bg-gradient-to-r from-primary/70 via-primary/30 to-transparent" />

        <nav className="absolute inset-x-0 top-0 z-10 flex items-center justify-between px-6 py-6 md:px-12">
          <span className="text-title-md font-black tracking-tight text-on-primary">PortföyAI</span>
          <Link
            href={isAuthenticated ? "/dashboard" : "/login"}
            className="rounded-full border border-on-primary/30 px-5 py-2 text-body-sm font-medium text-on-primary backdrop-blur-sm transition-colors hover:bg-on-primary/10"
          >
            {isAuthenticated ? "Panele Git" : "Giriş Yap"}
          </Link>
        </nav>

        {PHASES.map((phase) => (
          <Phase key={phase.kicker} progress={progress} {...phase} />
        ))}

        <motion.div
          style={{ opacity: ctaOpacity, y: ctaY }}
          className="absolute inset-x-6 top-1/2 -translate-y-1/2 md:inset-x-12"
        >
          <div className="mx-auto flex max-w-4xl flex-col items-start gap-8">
            <h2 className="max-w-2xl text-display-lg text-on-primary [text-shadow:0_2px_28px_rgba(0,0,0,0.55)] sm:text-[64px] sm:leading-[70px]">
              Takip hiç unutulmaz
            </h2>
            <Link
              href={isAuthenticated ? "/dashboard" : "/login"}
              className={cn(
                buttonVariants({ size: "lg" }),
                "bg-on-primary px-10 text-primary hover:opacity-90"
              )}
            >
              {isAuthenticated ? "Panele Git" : "Ücretsiz Dene"}
            </Link>
          </div>
        </motion.div>

        <motion.div
          style={{ opacity: hintOpacity }}
          className="absolute inset-x-0 bottom-8 z-10 flex flex-col items-center gap-1 text-on-primary/80"
        >
          <span className="text-label-caps tracking-[0.2em]">Kaydırın</span>
          <Icon name="keyboard_arrow_down" className="animate-bounce" />
        </motion.div>
      </div>
    </section>
  );
}
