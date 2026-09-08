"use client";

import { useState } from "react";

import { ProcessView } from "@/components/studio/visual-explanation/process-view";
import { reviewScene } from "@/components/studio/visual-explanation/process-review-data";
import {
  initialProcessState,
  nextViewState,
  type ProcessMotionIntent,
  type ProcessScene,
  type ProcessViewState,
} from "@/components/studio/visual-explanation/process-model";
import {
  CoordinateConstruction,
  MathExpressionInput,
  SpatialPlacement,
  selectCanvasCapability,
  type CanvasVisualIntent,
  type GridPoint,
  type MathInput,
  type SemanticPlacement,
} from "@/lib/studio/visual-toolbelt";

const sequenceMotion: ProcessMotionIntent[] = [
  "REVEAL_IN_ORDER",
  "TRACE_SEQUENCE",
  "TRANSITION_FOCUS",
  "EMPHASIZE_RELATION",
];
const cycleMotion: ProcessMotionIntent[] = [
  "REVEAL_IN_ORDER",
  "TRACE_CYCLE",
  "TRANSITION_FOCUS",
  "EMPHASIZE_RELATION",
];
const sequenceScene: ProcessScene = { ...reviewScene(0, true), motion_intents: sequenceMotion };
const cycleScene: ProcessScene = { ...reviewScene(1, true), motion_intents: cycleMotion };

function SelectionResult({ intent }: { intent: CanvasVisualIntent }) {
  const selection = selectCanvasCapability(intent);
  return (
    <p className="canvas-selection" data-selection-input={JSON.stringify(intent)} data-selection-result={selection?.pattern} data-selection-adapter={selection?.adapter}>
      <span>النية الدلالية</span>
      <code dir="ltr">{intent.type}</code>
      <span aria-hidden="true">←</span>
      <strong dir="ltr">{selection?.pattern}</strong>
    </p>
  );
}

function ProcessPattern({ scene, label }: { scene: ProcessScene; label: string }) {
  const [state, setState] = useState<ProcessViewState>(initialProcessState);
  const [request, setRequest] = useState<string | null>(null);
  const intent: CanvasVisualIntent = { type: "explain_process", topology: scene.topology };
  const selection = selectCanvasCapability(intent);
  return (
    <article className="canvas-pattern canvas-process" data-canvas-pattern={selection?.pattern} data-canvas-adapter={selection?.adapter} data-process-topology={scene.topology}>
      <div className="canvas-pattern-heading">
        <span className="canvas-number">{label}</span>
        <div><p className="canvas-kicker">Process · {scene.topology}</p><h2>{scene.topology === "sequence" ? "تسلسل له بداية ونهاية" : "دورة تبدأ جيلًا جديدًا"}</h2></div>
      </div>
      <SelectionResult intent={intent}/>
      <ProcessView
        scene={scene}
        state={state}
        onAction={(action) => setState((current) => nextViewState(scene, current, action))}
        onExplain={(stageId) => setRequest(stageId)}
      />
      <output className="canvas-semantic-output" data-semantic-result={JSON.stringify({ topology: scene.topology, state, explanationStageId: request })}>
        النتيجة الدلالية · <code dir="ltr">{JSON.stringify({ topology: scene.topology, state, explanationStageId: request })}</code>
      </output>
    </article>
  );
}

export function CanvasFinalReview() {
  const spatialIntent: CanvasVisualIntent = { type: "place_object", relation: "inside" };
  const coordinateIntent: CanvasVisualIntent = { type: "construct_coordinate", domain: "integer_grid" };
  const mathIntent: CanvasVisualIntent = { type: "author_math", format: "latex" };
  const [placement, setPlacement] = useState<SemanticPlacement>({ objectId: "fraction-three-quarters", targetId: null });
  const [point, setPoint] = useState<GridPoint>({ x: -2, y: 3 });
  const [math, setMath] = useState("\\frac{3}{4}+\\frac{1}{4}");
  const [submittedMath, setSubmittedMath] = useState<MathInput | null>(null);
  const spatialSelection = selectCanvasCapability(spatialIntent);
  const coordinateSelection = selectCanvasCapability(coordinateIntent);
  const mathSelection = selectCanvasCapability(mathIntent);

  return (
    <main className="canvas-final" dir="rtl">
      <header className="canvas-hero">
        <p className="canvas-kicker">Canvas · final product review</p>
        <h1>تعلّم بصري يمكن لمسه وتجربته</h1>
        <p>أربع طرق واضحة تساعد لينا على تتبّع العمليات، وتحريك الأفكار، وبناء الرياضيات، وكتابة التعبير بنفسها.</p>
        <nav aria-label="أنماط Canvas النهائية">
          <a href="#process-sequence">التسلسل</a><a href="#process-cycle">الدورة</a><a href="#spatial">التصنيف المكاني</a><a href="#coordinates">الإحداثيات</a><a href="#math-input">التعبير الرياضي</a>
        </nav>
      </header>

      <section className="canvas-review-note" aria-label="حدود سطح المراجعة">
        <strong>سطح مراجعة داخلي مباشر</strong>
        <span>يعرض المحولات الفعلية ونتائجها الدلالية محليًا. لا يكتب Evidence ولا يرسل طلب Tutor.</span>
      </section>

      <div id="process-sequence"><ProcessPattern scene={sequenceScene} label="01"/></div>
      <div id="process-cycle"><ProcessPattern scene={cycleScene} label="02"/></div>

      <article id="spatial" className="canvas-pattern" data-canvas-pattern={spatialSelection?.pattern} data-canvas-adapter={spatialSelection?.adapter}>
        <div className="canvas-pattern-heading"><span className="canvas-number">03</span><div><p className="canvas-kicker">Spatial manipulation</p><h2>صنّف الكسر حسب قيمته</h2></div></div>
        <SelectionResult intent={spatialIntent}/>
        <SpatialPlacement
          value={placement}
          onSemanticPlacement={setPlacement}
          object={{ id: "fraction-three-quarters", label: "¾" }}
          target={{ id: "less-than-one", label: "< 1" }}
          title="هل ¾ أصغر من ١؟"
          prompt="اسحب الكسر إلى المنطقة المناسبة، أو استخدم زر لوحة المفاتيح."
        />
        <output className="canvas-semantic-output" data-semantic-result={JSON.stringify(placement)}>
          النتيجة الدلالية · <code dir="ltr">{JSON.stringify(placement)}</code>
        </output>
      </article>

      <article id="coordinates" className="canvas-pattern" data-canvas-pattern={coordinateSelection?.pattern} data-canvas-adapter={coordinateSelection?.adapter}>
        <div className="canvas-pattern-heading"><span className="canvas-number">04</span><div><p className="canvas-kicker">Mathematical construction</p><h2>ابنِ النقطة P على المستوى</h2></div></div>
        <SelectionResult intent={coordinateIntent}/>
        <CoordinateConstruction value={point} onValueChange={setPoint}/>
        <output className="canvas-semantic-output" data-semantic-result={JSON.stringify(point)}>
          النتيجة الدلالية · <code dir="ltr">{JSON.stringify(point)}</code>
        </output>
      </article>

      <article id="math-input" className="canvas-pattern" data-canvas-pattern={mathSelection?.pattern} data-canvas-adapter={mathSelection?.adapter}>
        <div className="canvas-pattern-heading"><span className="canvas-number">05</span><div><p className="canvas-kicker">Math expression</p><h2>اكتب مجموع كسرين</h2></div></div>
        <SelectionResult intent={mathIntent}/>
        <MathExpressionInput value={math} onValueChange={setMath} onSubmit={setSubmittedMath}/>
        <output className="canvas-semantic-output" data-semantic-result={JSON.stringify({ value: math, submitted: submittedMath })}>
          النتيجة الدلالية · <code dir="ltr">{JSON.stringify({ value: math, submitted: submittedMath })}</code>
        </output>
      </article>
    </main>
  );
}
