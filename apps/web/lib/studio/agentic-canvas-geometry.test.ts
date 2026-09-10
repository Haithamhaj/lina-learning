import assert from "node:assert/strict";
import test from "node:test";

import {
  diagramPositions,
  mathSurfaceKind,
  presentationLayout,
  spatialPrimitive,
} from "./agentic-canvas-geometry.ts";

test("PLOT keeps graph semantics instead of falling back to a number line", () => {
  assert.equal(mathSurfaceKind("NUMBER_LINE"), "number-line");
  assert.equal(mathSurfaceKind("CARTESIAN"), "cartesian");
  assert.equal(mathSurfaceKind("PLOT"), "plot");
});

test("Scene 2D objects retain their own deterministic primitives", () => {
  assert.equal(spatialPrimitive("CIRCLE"), "circle");
  assert.equal(spatialPrimitive("POLYGON"), "polygon");
  assert.equal(spatialPrimitive("ARROW"), "arrow");
  assert.equal(spatialPrimitive("LABEL"), "label");
  assert.notEqual(spatialPrimitive("POLYGON"), spatialPrimitive("RECTANGLE"));
});

test("stored presentation layout and reveal semantics produce distinct renderer plans", () => {
  assert.notDeepEqual(presentationLayout("FOCUS_SUPPORT", "PRIMARY", "FULL"), presentationLayout("STACK", "PRIMARY", "FULL"));
  assert.equal(presentationLayout("OVERLAY", "SUPPORT", "COMPACT").region, "overlay-support");
});

test("diagram topology changes deterministic geometry", () => {
  assert.notDeepEqual(diagramPositions("SEQUENCE", 4), diagramPositions("CYCLE", 4));
  assert.notDeepEqual(diagramPositions("CAUSE_EFFECT", 4), diagramPositions("HIERARCHY", 4));
});
