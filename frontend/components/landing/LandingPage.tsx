import { Hero } from "@/components/landing/Hero";
import { HeroFeatures } from "@/components/landing/HeroFeatures";
import { CTASection } from "@/components/landing/CTASection";
import { Footer } from "@/components/landing/Footer";

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Hero />
      <HeroFeatures />
      <CTASection />
      <Footer />
    </div>
  );
}
