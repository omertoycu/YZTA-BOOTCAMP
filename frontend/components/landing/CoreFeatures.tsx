import { Icon } from "@/components/ui/Icon";
import { Reveal } from "@/components/landing/Reveal";

const FEATURES = [
  { icon: "forum", label: "Müşteri Kaydı" },
  { icon: "content_paste", label: "İlan İçe Aktarma" },
  { icon: "hub", label: "Eşleştirme" },
  { icon: "military_tech", label: "Puanlama" },
  { icon: "payments", label: "Fiyat Önerisi" },
  { icon: "bar_chart", label: "Raporlama" },
  { icon: "apartment", label: "Çoklu Ofis Desteği" },
  { icon: "credit_card", label: "Abonelik ve Faturalama" },
];

export function CoreFeatures() {
  return (
    <section className="bg-surface-container-low px-6 py-24 md:px-12">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mb-14 text-center">
          <span className="mb-3 inline-flex items-center gap-2 rounded-full bg-surface-container px-4 py-1.5 text-label-caps text-on-surface-variant">
            Sektör standardı
          </span>
          <h2 className="text-headline-lg text-primary sm:text-[40px] sm:leading-[48px]">
            Temel özellikler
          </h2>
        </Reveal>

        <Reveal>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {FEATURES.map((feature) => (
              <div
                key={feature.label}
                className="flex flex-col items-center gap-3 rounded-lg bg-surface-container-lowest p-6 text-center shadow-[0px_10px_30px_rgba(0,0,0,0.04)]"
              >
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-mint-accent text-secondary">
                  <Icon name={feature.icon} />
                </div>
                <p className="text-body-sm font-medium text-on-surface">{feature.label}</p>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
