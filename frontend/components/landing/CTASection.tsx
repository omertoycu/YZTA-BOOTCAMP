import Link from "next/link";
import { buttonVariants } from "@/components/ui/Button";
import { Reveal } from "@/components/landing/Reveal";
import { cn } from "@/lib/utils";

export function CTASection({ isAuthenticated = false }: { isAuthenticated?: boolean }) {
  return (
    <section className="bg-primary px-6 py-24 md:px-12">
      <Reveal className="mx-auto flex max-w-2xl flex-col items-center gap-6 text-center">
        <h2 className="text-headline-lg text-on-primary sm:text-[40px] sm:leading-[48px]">
          Ofisiniz için PortföyAI&apos;yi bugün deneyin
        </h2>
        <p className="text-body-lg text-on-primary/80">
          Kurulum birkaç dakika sürer. İlk portföyünüzü ekleyip ilk müşterinizi karşılamaya hemen başlayın.
        </p>
        <Link
          href={isAuthenticated ? "/dashboard" : "/login"}
          className={cn(buttonVariants({ size: "lg" }), "bg-on-primary text-primary hover:opacity-90")}
        >
          {isAuthenticated ? "Panele Git" : "Ücretsiz Dene"}
        </Link>
      </Reveal>
    </section>
  );
}
