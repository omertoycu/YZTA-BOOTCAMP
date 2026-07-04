import { Icon } from "@/components/ui/Icon";
import { Reveal } from "@/components/landing/Reveal";

const TODAY = [
  "WhatsApp'ta onlarca ayrı sohbette kaybolan müşteri talepleri",
  "Excel'de elle tutulan, güncelliğini hızla yitiren portföy listesi",
  "Sahada alınan notların ofise dönünce ilana dönüşmesi saatler sürüyor",
  "Takip edilmesi unutulan, soğuyan müşteri adayları",
];

const WITH_PORTFOYAI = [
  "Her WhatsApp mesajı otomatik olarak müşteri kaydına dönüşür",
  "Portföy tek bir yerde, her zaman güncel ve aranabilir",
  "Sesli not, saniyeler içinde yapılandırılmış bir ilan taslağına dönüşür",
  "Otomatik takip zinciri, müşteri yanıt verene kadar hiç durmaz",
];

export function ProblemSolution() {
  return (
    <section className="px-6 py-24 md:px-12">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mb-14 text-center">
          <h2 className="text-headline-lg text-primary sm:text-[40px] sm:leading-[48px]">
            Bugün nasıl çalışıyorsunuz?
          </h2>
        </Reveal>

        <div className="grid gap-6 md:grid-cols-2">
          <Reveal direction="left">
            <div className="h-full rounded-lg border border-outline-variant bg-surface-container-lowest p-8">
              <span className="mb-6 inline-flex items-center gap-2 rounded-full bg-surface-container px-3 py-1 text-label-caps text-on-surface-variant">
                Bugün
              </span>
              <ul className="flex flex-col gap-4">
                {TODAY.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-body-lg text-on-surface-variant">
                    <Icon name="close" className="mt-0.5 shrink-0 text-outline" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          <Reveal direction="right" delay={0.1}>
            <div className="h-full rounded-lg bg-primary p-8 text-on-primary">
              <span className="mb-6 inline-flex items-center gap-2 rounded-full bg-mint-accent px-3 py-1 text-label-caps text-on-secondary-container">
                PortföyAI ile
              </span>
              <ul className="flex flex-col gap-4">
                {WITH_PORTFOYAI.map((item) => (
                  <li key={item} className="flex items-start gap-3 text-body-lg text-on-primary/90">
                    <Icon name="check" className="mt-0.5 shrink-0 text-secondary-fixed" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
