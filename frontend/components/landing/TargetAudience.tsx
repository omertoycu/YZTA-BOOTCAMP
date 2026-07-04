import { Icon } from "@/components/ui/Icon";
import { Reveal } from "@/components/landing/Reveal";

const AUDIENCE = [
  {
    icon: "storefront",
    title: "1–5 danışmanlı bağımsız ofisler",
    description: "Büyük zincirler değil; hızlı karar alabilen, çevik ofisler için tasarlandı.",
  },
  {
    icon: "smartphone",
    title: "Hâlâ WhatsApp ve Excel'le çalışanlar",
    description: "Dijitalleşmemiş, elle takip yapan emlak danışmanları.",
  },
  {
    icon: "schedule",
    title: "Sahada zaman kaybedenler",
    description: "İlan girme ve müşteri takibinde en çok zaman kaybeden danışmanlar.",
  },
];

export function TargetAudience() {
  return (
    <section className="px-6 py-24 md:px-12">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mb-14 text-center">
          <h2 className="text-headline-lg text-primary sm:text-[40px] sm:leading-[48px]">Kimler için?</h2>
        </Reveal>

        <div className="grid gap-6 md:grid-cols-3">
          {AUDIENCE.map((item, i) => (
            <Reveal key={item.title} delay={i * 0.1}>
              <div className="flex h-full flex-col items-center gap-3 rounded-lg border border-outline-variant p-8 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-on-primary">
                  <Icon name={item.icon} />
                </div>
                <h3 className="text-title-md text-primary">{item.title}</h3>
                <p className="text-body-sm text-text-muted">{item.description}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
