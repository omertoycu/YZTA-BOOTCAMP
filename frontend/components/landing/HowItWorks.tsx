"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Icon } from "@/components/ui/Icon";
import { Reveal } from "@/components/landing/Reveal";

const STEPS = [
  {
    icon: "add_home",
    title: "Portföyünü ekle",
    description: "Sesle anlatarak, rehberli bir formla ya da ilan sayfasının kaynağını yapıştırarak.",
  },
  {
    icon: "chat",
    title: "Müşteri WhatsApp'tan yazar",
    description: "Gelen her mesaj otomatik olarak bir müşteri kaydına dönüşür.",
  },
  {
    icon: "auto_awesome",
    title: "Sistem otomatik puanlar ve eşleştirir",
    description: "Bütçe, oda tercihi ve bölgeye göre uygun portföylerle eşleşir.",
  },
  {
    icon: "check_circle",
    title: "Takip hiç unutulmaz",
    description: "Otomatik takip zinciri, müşteri yanıt verene kadar devam eder.",
  },
];

export function HowItWorks() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start 0.8", "end 0.4"],
  });
  const lineHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  return (
    <section id="nasil-calisir" className="px-6 py-24 md:px-12">
      <div className="mx-auto max-w-3xl">
        <Reveal className="mb-16 text-center">
          <h2 className="text-headline-lg text-primary sm:text-[40px] sm:leading-[48px]">Nasıl çalışır?</h2>
        </Reveal>

        <div ref={sectionRef} className="relative pl-14">
          <div className="absolute left-5 top-2 h-[calc(100%-16px)] w-[2px] bg-surface-variant" />
          <motion.div
            className="absolute left-5 top-2 w-[2px] bg-secondary"
            style={{ height: lineHeight }}
          />

          <div className="flex flex-col gap-14">
            {STEPS.map((step, i) => (
              <Reveal key={step.title} delay={i * 0.05}>
                <div className="relative">
                  <div className="absolute -left-14 flex h-10 w-10 items-center justify-center rounded-full bg-primary text-on-primary">
                    <Icon name={step.icon} className="text-[20px]" />
                  </div>
                  <p className="mb-1 text-label-caps text-secondary">Adım {i + 1}</p>
                  <h3 className="mb-2 text-title-md text-primary">{step.title}</h3>
                  <p className="text-body-sm text-text-muted">{step.description}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
