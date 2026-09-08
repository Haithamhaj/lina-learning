"use client";

import { useEffect, useRef, useState } from "react";
import type { MathfieldElement } from "mathlive";
import { serializeMathInput, type MathInput } from "../contracts";

export function MathLiveProof({ value, onValueChange, onSubmit, title = "اكتب كسرًا · Write a fraction", prompt = "اكتب تعبيرك، ثم أرسله عندما تكون مستعدًا." }: {
  value: string; onValueChange: (value: string) => void; onSubmit?: (value: MathInput) => void; title?: string; prompt?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const field = useRef<MathfieldElement | null>(null);
  const current = useRef({value, onValueChange}); current.current = {value, onValueChange};
  const [failed, setFailed] = useState(false);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    let dispose: (() => void) | undefined;
    import("mathlive").then(({ MathfieldElement }) => {
      if (!active || !host.current) return;
      MathfieldElement.fontsDirectory = "/mathlive/fonts";
      MathfieldElement.soundsDirectory = null;
      const element = new MathfieldElement();
      field.current = element;
      element.value = current.current.value;
      element.mathVirtualKeyboardPolicy = "auto";
      element.setAttribute("aria-label", "Mathematical expression input");
      element.setAttribute("dir", "ltr");
      const input = () => {
        const next = element.getValue("latex");
        current.current.onValueChange(next);
        // A parent may reject an edit. Reconcile even when its value did not change.
        queueMicrotask(() => {
          if (active && element.getValue("latex") !== current.current.value)
            element.setValue(current.current.value, { silenceNotifications: true });
        });
      };
      element.addEventListener("input", input);
      host.current.appendChild(element);
      dispose = () => { element.removeEventListener("input", input); element.blur(); element.remove(); field.current = null; };
    }).catch(() => { dispose?.(); if (active) setFailed(true); });
    return () => { active = false; dispose?.(); };
  }, []);
  useEffect(() => {
    if (field.current && field.current.getValue("latex") !== value)
      field.current.setValue(value, { silenceNotifications: true });
    setSubmitted(null); setError(null);
  }, [value]);
  return <section className="toolbelt-card" data-engine="mathlive">
    <span className="toolbelt-eyebrow">التعبير الرياضي</span><h2>{title}</h2>
    <p>{prompt}</p>
    <div className="toolbelt-math" dir="ltr" ref={host}/>
    {failed && <label>LaTeX<input dir="ltr" aria-label="Mathematical expression input" value={value} onChange={event => onValueChange(event.target.value)}/></label>}
    <div className="toolbelt-actions"><button aria-label="Submit expression" onClick={() => {
      try { const result = serializeMathInput(value); onSubmit?.(result); setSubmitted(result.value); setError(null); }
      catch { setError("اكتب تعبيرًا من 1 إلى 200 حرف · Enter 1–200 characters"); }
    }}>إرسال التعبير</button></div>
    <output dir="ltr" aria-live="polite">{error || (submitted === null ? value : `Submitted: ${submitted}`)}</output>
  </section>;
}
