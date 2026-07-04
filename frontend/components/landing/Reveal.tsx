"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Direction = "up" | "left" | "right" | "none";

const OFFSETS: Record<Direction, { x: number; y: number }> = {
  up: { x: 0, y: 28 },
  left: { x: -28, y: 0 },
  right: { x: 28, y: 0 },
  none: { x: 0, y: 0 },
};

export function Reveal({
  children,
  className,
  direction = "up",
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  direction?: Direction;
  delay?: number;
}) {
  const offset = OFFSETS[direction];
  return (
    <motion.div
      className={cn(className)}
      initial={{ opacity: 0, x: offset.x, y: offset.y }}
      whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.6, delay, ease: [0.21, 0.47, 0.32, 0.98] }}
    >
      {children}
    </motion.div>
  );
}
