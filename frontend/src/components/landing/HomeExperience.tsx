"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import { LandingScreen } from "@/components/landing/LandingScreen";
import { PlannerPage } from "@/components/planner/PlannerPage";

export function HomeExperience() {
  const [landing, setLanding] = useState(true);

  return (
    <>
      <PlannerPage />
      <AnimatePresence>
        {landing ? (
          <motion.div
            className="fixed inset-0 z-50"
            exit={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
          >
            <LandingScreen onEnter={() => setLanding(false)} />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  );
}
