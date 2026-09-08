"use client";

import { MotionConfig, motion, useReducedMotion } from "motion/react";
import type { RelationFocus } from "../contracts";

/** A controlled finite focus transition; retargeting interrupts the same animated node. */
export function MotionProof({ focus, onFocusChange }: {
  focus: RelationFocus; onFocusChange: (value: RelationFocus) => void;
}) {
  const reduced = useReducedMotion();
  const target = focus === "target";
  return <MotionConfig reducedMotion="user"><section className="toolbelt-card" data-engine="motion">
    <span className="toolbelt-eyebrow">01 · روابط الأفكار</span><h2>اتبع العلاقة · Follow the relation</h2>
    <p>اختر الفكرة التي تريد التركيز عليها.</p>
    <svg className="toolbelt-surface" viewBox="0 0 320 110" role="img" aria-label={`Relation focus: ${focus}`}>
      <path d="M50 48H270" stroke="#c1ccd0" strokeWidth="3"/>
      <circle cx="50" cy="48" r="20" fill="#dbe9ff"/><circle cx="270" cy="48" r="20" fill="#c9f1df"/>
      <motion.circle initial={false} animate={{cx: target ? 270 : 50}} cy="48" r="26" fill="none" stroke="#315eaf" strokeWidth="3" transition={{duration: reduced ? 0 : 0.35, ease: "easeOut"}}/>
      <text x="50" y="94" textAnchor="middle">A</text><text x="270" y="94" textAnchor="middle">B</text>
    </svg>
    <div className="toolbelt-actions"><button aria-label="Focus source" aria-pressed={!target} onClick={() => onFocusChange("source")}>الفكرة A</button><button aria-label="Focus target" aria-pressed={target} onClick={() => onFocusChange("target")}>الفكرة B</button></div>
    <output aria-live="polite">{target ? "التركيز: B · Focus: B" : "التركيز: A · Focus: A"}</output>
  </section></MotionConfig>;
}
