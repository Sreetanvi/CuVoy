"use client";

import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

const TITLE = [
  { letter: "C", className: "font-[family-name:var(--font-permanent-marker)]" },
  { letter: "u", className: "font-[family-name:var(--font-caveat)]" },
  { letter: "V", className: "font-[family-name:var(--font-special-elite)]" },
  { letter: "o", className: "font-[family-name:var(--font-homemade-apple)]" },
  { letter: "y", className: "font-[family-name:var(--font-rock-salt)]" },
] as const;

export function LandingScreen({ onEnter }: { onEnter: () => void }) {
  const [showCta, setShowCta] = useState(false);

  useEffect(() => {
    const cta = window.setTimeout(() => setShowCta(true), 1800);
    return () => window.clearTimeout(cta);
  }, []);

  return (
    <div className="relative h-dvh w-full overflow-hidden text-white">
      <Image
        src="/road_backg.png"
        alt=""
        fill
        priority
        sizes="100vw"
        className="object-cover object-center"
      />
      <div className="absolute inset-0 bg-black/35" />
      <div className="relative z-10 flex h-full flex-col items-center justify-center px-6">
        <motion.div
          className="flex flex-col items-center text-center"
          animate={{ y: showCta ? -56 : 0 }}
          transition={{ duration: 0.7, ease: "easeInOut" }}
        >
          <h1 className="flex gap-1 text-7xl leading-none sm:text-8xl" aria-label="CuVoy">
            {TITLE.map((part) => (
              <span key={part.letter} className={part.className}>
                {part.letter}
              </span>
            ))}
          </h1>
          <p className="mt-4 font-[family-name:var(--font-caveat)] text-3xl sm:text-4xl">
            Curating your Voyage
          </p>
          <p className="mt-2 font-[family-name:var(--font-special-elite)] text-lg tracking-wide">
            Plot your escape
          </p>
        </motion.div>
        <AnimatePresence>
          {showCta ? (
            <motion.div
              className="mt-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6 }}
            >
              <Button type="button" size="lg" data-testid="start-curating" onClick={onEnter}>
                Start Curating
              </Button>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}
