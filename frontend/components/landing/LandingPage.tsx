import { Hero } from "@/components/landing/Hero";
import { ProblemSolution } from "@/components/landing/ProblemSolution";
import { HeroFeatures } from "@/components/landing/HeroFeatures";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { CoreFeatures } from "@/components/landing/CoreFeatures";
import { TargetAudience } from "@/components/landing/TargetAudience";
import { CTASection } from "@/components/landing/CTASection";
import { Footer } from "@/components/landing/Footer";

export function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Hero />
      <ProblemSolution />
      <HeroFeatures />
      <HowItWorks />
      <CoreFeatures />
      <TargetAudience />
      <CTASection />
      <Footer />
    </div>
  );
}
