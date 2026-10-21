// A loader/BlendShapeProxy test using Kalidoface's published dependency versions.
// This is NOT a browser, renderer, camera or end-to-end Kalidoface test.
import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const require = createRequire(path.resolve('output/avatar/kalido-runtime/package.json'));
const { GLTFLoader } = await import(pathToFileURL(require.resolve('three/examples/jsm/loaders/GLTFLoader.js')));
const { VRM, VRMSchema } = require('@pixiv/three-vrm');
const buffer = await readFile('output/avatar/pineapple-kalidoface.vrm');
const ab = buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength);
const gltf = await new Promise((resolve, reject) => new GLTFLoader().parse(ab, '', resolve, reject));
const vrm = await VRM.from(gltf);
if (!vrm.blendShapeProxy) throw Error('Missing blendShapeProxy');
const meshes = [];
vrm.scene.traverse(o => { if(o.morphTargetInfluences) meshes.push(o); });
const checks = {};
for (const name of ['Blink', 'BlinkL', 'BlinkR', 'A', 'I', 'U', 'E', 'O']) {
  const preset = VRMSchema.BlendShapePresetName[name];
  vrm.blendShapeProxy.setValue(preset, 1);
  vrm.blendShapeProxy.update();
  const changed = meshes.filter(m => m.morphTargetInfluences.some(v => v > 0.99)).map(m => m.name);
  if (!changed.length) throw Error(`No morph target responds to ${name}`);
  checks[name] = changed;
  vrm.blendShapeProxy.setValue(preset, 0);
  vrm.blendShapeProxy.update();
}
const result = { scope: 'Node loader and expression binding test; no browser or webcam', three:'0.138.3', threeVrm:'0.6.10', checks };
await writeFile('output/avatar/kalidoface-runtime-validation.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));
