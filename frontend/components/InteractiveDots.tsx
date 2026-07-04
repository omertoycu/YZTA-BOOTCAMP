"use client";

import { useEffect, useRef } from "react";

/**
 * Login panelindeki nokta deseni: imleç hareketine göre iki katman farklı
 * hızlarda kayar (parallax) ve imlecin çevresindeki noktalar hafifçe parlar.
 * Mouse, üst panelden (parentElement) dinlenir — katmanların kendisi
 * pointer-events-none olduğu için içerikteki etkileşimler bozulmaz.
 * React state yerine doğrudan DOM'a yazılır; mousemove frekansında
 * re-render tetiklememek için.
 */
export function InteractiveDots() {
  const rootRef = useRef<HTMLDivElement>(null);
  const layerSlow = useRef<HTMLDivElement>(null);
  const layerFast = useRef<HTMLDivElement>(null);
  const glow = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const parent = rootRef.current?.parentElement;
    if (!parent) return;

    let frame: number | null = null;

    function handleMove(e: MouseEvent) {
      if (!parent) return;
      const rect = parent.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const relX = x / rect.width - 0.5;
      const relY = y / rect.height - 0.5;

      if (frame !== null) cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (layerSlow.current)
          layerSlow.current.style.transform = `translate(${relX * -14}px, ${relY * -14}px)`;
        if (layerFast.current)
          layerFast.current.style.transform = `translate(${relX * -32}px, ${relY * -32}px)`;
        if (glow.current)
          glow.current.style.background = `radial-gradient(280px circle at ${x}px ${y}px, rgba(224,242,241,0.16), transparent 70%)`;
      });
    }

    parent.addEventListener("mousemove", handleMove);
    return () => {
      parent.removeEventListener("mousemove", handleMove);
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div ref={rootRef} aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div
        ref={layerSlow}
        className="absolute -inset-10 opacity-20 transition-transform duration-300 ease-out"
        style={{
          backgroundImage: "radial-gradient(circle, white 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
      <div
        ref={layerFast}
        className="absolute -inset-10 opacity-10 transition-transform duration-200 ease-out"
        style={{
          backgroundImage: "radial-gradient(circle, white 1.5px, transparent 1.5px)",
          backgroundSize: "96px 96px",
          backgroundPosition: "24px 24px",
        }}
      />
      <div ref={glow} className="absolute inset-0" />
    </div>
  );
}
