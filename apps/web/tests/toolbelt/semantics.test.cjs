const { test } = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { mkdtempSync } = require('node:fs');
const path = require('node:path');
const out = mkdtempSync('/tmp/cs07-semantics-');
execFileSync(process.execPath, [require.resolve('typescript/bin/tsc'), path.resolve(__dirname, '../../lib/studio/visual-toolbelt/contracts.ts'), '--outDir', out, '--target', 'es2020', '--module', 'commonjs', '--skipLibCheck']);
const model = require(path.join(out, 'contracts.js'));
test('placement maps a bounded hit to stable semantic IDs and rejects non-finite coordinates', () => {
  assert.equal(typeof model.placementFromPoint, 'function');
  assert.deepEqual(model.placementFromPoint(250, 90), { objectId: 'object-a', targetId: 'target-b' });
  for (const point of [[20, 90], [NaN, 90], [250, Infinity]])
    assert.deepEqual(model.placementFromPoint(...point), { objectId: 'object-a', targetId: null });
});

test('placement preserves application-owned learning object and target IDs', () => {
  assert.deepEqual(
    model.placementFromPoint(250, 90, 'fraction-three-quarters', 'less-than-one'),
    { objectId: 'fraction-three-quarters', targetId: 'less-than-one' },
  );
  assert.deepEqual(
    model.placementFromPoint(20, 90, 'fraction-three-quarters', 'less-than-one'),
    { objectId: 'fraction-three-quarters', targetId: null },
  );
});
test('coordinate construction quantizes once to exact bounded integers', () => {
  assert.equal(typeof model.exactGridPoint, 'function');
  assert.deepEqual(model.exactGridPoint(1.9999999, -2.01), { x: 2, y: -2 });
  assert.deepEqual(model.exactGridPoint(-3, 5), { x: -3, y: 5 });
  assert.deepEqual(model.exactGridPoint(99, -99), { x: 10, y: -10 });
  assert.throws(() => model.exactGridPoint(NaN, 2));
});
test('coordinate state accepts only exact integers inside the semantic plane', () => {
  assert.equal(model.isExactGridPoint({ x: -10, y: 10 }), true);
  assert.equal(model.isExactGridPoint({ x: -3, y: 5 }), true);
  assert.equal(model.isExactGridPoint({ x: 11, y: 0 }), false);
  assert.equal(model.isExactGridPoint({ x: 0.5, y: 0 }), false);
});
test('math serialization preserves the exact authored fraction without evaluation', () => {
  assert.equal(typeof model.serializeMathInput, 'function');
  assert.deepEqual(model.serializeMathInput('\\frac{3}{4}+\\frac{1}{4}'), { format: 'latex', value: '\\frac{3}{4}+\\frac{1}{4}' });
  assert.throws(() => model.serializeMathInput('  '));
  assert.throws(() => model.serializeMathInput('1'.repeat(201)));
});
