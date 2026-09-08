import React, { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { RelationFocusView as MotionProof, SpatialPlacement as KonvaProof, CoordinateConstruction as JsxGraphProof, MathExpressionInput as MathLiveProof, type SemanticPlacement } from '../../lib/studio/visual-toolbelt';
import Konva from 'konva';
import JXG from 'jsxgraph';
Object.assign(window, { spatialPositions: () => { const circle = Konva.stages[0].findOne("Circle")!; const label = Konva.stages[0].find("Text").find(node => (node as Konva.Text).text() === "A")! as Konva.Text; return { circle: circle.getAbsolutePosition(), label: { x: label.getAbsolutePosition().x + label.width() / 2, y: label.getAbsolutePosition().y + label.height() / 2 } }; }, engineCounts: () => ({ stages: Konva.stages.length, boards: Object.keys(JXG.boards as Record<string, unknown>).length }) });
function Fixture() {
  const [reject, setReject] = useState(false);
  const [submission, setSubmission] = useState<unknown>(null);
  const [mounted, mount] = useState(true);
  const [focus, setFocus] = useState<'source' | 'target'>('source');
  const [placement, setPlacement] = useState<SemanticPlacement>({ objectId: 'object-a', targetId: null });
  const [point, setPoint] = useState({ x: 2, y: 1 });
  const [math, setMath] = useState('\\frac{3}{4}');
  return <main className="toolbelt-review" dir="rtl"><h1>أدوات الاستكشاف · Lina</h1><label><input type="checkbox" checked={reject} onChange={e => setReject(e.target.checked)}/>Reject edits</label><button onClick={() => mount(!mounted)}>Toggle mounts</button><button onClick={() => {setFocus('source'); setPlacement({objectId:'object-a',targetId:null});setPoint({x:-3,y:2});setMath('\\frac{1}{2}');}}>External reset</button>{mounted && <><MotionProof focus={focus} onFocusChange={setFocus}/><KonvaProof value={placement} onSemanticPlacement={v => { if (!reject) setPlacement(v); }}/><JsxGraphProof value={point} onValueChange={v => { if (!reject) setPoint(v); }}/><MathLiveProof value={math} onValueChange={v => { if (!reject) setMath(v); }} onSubmit={setSubmission}/></>}<pre id="semantic-result">{JSON.stringify({focus,placement,point,math,submission})}</pre></main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><Fixture/></StrictMode>);
