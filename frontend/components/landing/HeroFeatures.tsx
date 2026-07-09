import { Icon } from "@/components/ui/Icon";
import { Reveal } from "@/components/landing/Reveal";

const FEATURES = [
  {
    icon: "mic",
    title: "Sesli Not → İlan",
    description:
      "Danışman telefonuna konuşur; yapay zeka kaydı dinleyip ilan taslağını (başlık, bölge, fiyat, oda sayısı, m²) otomatik hazırlar.",
  },
  {
    icon: "sync_alt",
    title: "Sesli Not → CRM Güncellemesi",
    description:
      "Bir aday hakkındaki görüşmeyi sesli anlat; yapay zeka görüşme özeti, önerilen pipeline durumu ve hatırlatma taslağı hazırlar — onay olmadan hiçbir şey yazılmaz.",
  },
  {
    icon: "forum",
    title: "Otomatik WhatsApp Takip Zinciri",
    description:
      "“Otomatik Takip” açıldığında sistem müşteriye giderek yumuşayan hatırlatma mesajları gönderir; müşteri yanıt verdiği an zincir otomatik durur.",
  },
];

export function HeroFeatures() {
  return (
    <section className="bg-surface-container-low px-6 py-24 md:px-12">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mx-auto mb-14 max-w-2xl text-center">
          <span className="mb-3 inline-flex items-center gap-2 rounded-full bg-mint-accent px-4 py-1.5 text-label-caps text-on-secondary-container">
            Rakiplerde olmayan
          </span>
          <h2 className="text-headline-lg text-primary sm:text-[40px] sm:leading-[48px]">
            Öne çıkan özellikler
          </h2>
        </Reveal>

        <div className="grid gap-6 md:grid-cols-3">
          {FEATURES.map((feature, i) => (
            <Reveal key={feature.title} delay={i * 0.12}>
              <div className="flex h-full flex-col rounded-lg bg-surface-container-lowest p-8 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] transition-shadow duration-300 hover:shadow-[0px_15px_40px_rgba(0,0,0,0.08)]">
                <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-full bg-mint-accent text-secondary">
                  <Icon name={feature.icon} className="text-[26px]" />
                </div>
                <h3 className="mb-3 text-title-md text-primary">{feature.title}</h3>
                <p className="text-body-sm text-text-muted">{feature.description}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
