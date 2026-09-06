import React from 'react';
import test from 'node:test';
import assert from 'node:assert/strict';
import {renderToStaticMarkup} from 'react-dom/server';
import {DecimalPlaceValueWorkspace} from './decimal-place-value-workspace';
test('unreadable workspace offers recovery while leaving Tutor available',()=>{
  const html=renderToStaticMarkup(<DecimalPlaceValueWorkspace sceneId="s" sceneVersion={1} state={null} locale="en" onOperation={async()=>{}} onReload={()=>{}}/>);
  assert.match(html,/Reload Workspace/);assert.match(html,/role="alert"/);
});
