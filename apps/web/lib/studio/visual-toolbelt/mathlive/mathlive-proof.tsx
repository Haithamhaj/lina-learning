"use client";

import { useEffect, useRef, useState } from "react";

export function MathLiveProof({ onValueChange }: { onValueChange?: (value: string) => void }) {
  const host = useRef<HTMLDivElement>(null); const [value, setValue] = useState("x^2+1");
  useEffect(() => { let field: any; let active = true; import("mathlive").then(({ MathfieldElement }) => { if (!active || !host.current) return; MathfieldElement.fontsDirectory = "/mathlive/fonts"; MathfieldElement.soundsDirectory = null; field = document.createElement("math-field") as any; field.value = value; field.setAttribute("aria-label", "Mathematical expression input"); field.addEventListener("input", () => { setValue(field.value); onValueChange?.(field.value); }); host.current.appendChild(field); }); return () => { active = false; field?.remove(); }; }, [onValueChange]);
  return <section data-engine="mathlive" dir="rtl"><h2>إدخال رياضي / Math input</h2><div dir="ltr" ref={host} /><output dir="ltr">Browser value: {value}. This is input only, not academic validation.</output></section>;
}
