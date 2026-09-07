"use client";

import { useEffect, useState } from "react";
import { MotionConfig, motion, useReducedMotion } from "motion/react";

export function MotionProof() {
  const reduced = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return <MotionConfig reducedMotion="user"><section data-engine="motion"><h2>Relation trace</h2><p>Focus moves from the source to the related idea.</p><svg viewBox="0 0 320 80" role="img" aria-label="A relation trace from source to target"><path d="M45 40H275" stroke="#94a3b8" strokeWidth="4" /><motion.circle initial={{ cx: 45 }} cy="40" r="10" fill="#4f46e5" animate={{ cx: 275 }} transition={reduced ? { duration: 0 } : { duration: 1.2, repeat: Infinity, repeatType: "reverse" }} /><circle cx="275" cy="40" r="12" fill="#10b981" /></svg><output>{mounted && reduced ? "Reduced motion: relation endpoints remain visible." : "Motion traces the relation."}</output></section></MotionConfig>;
}
