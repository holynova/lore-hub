import assert from 'node:assert/strict';
import worker, {parseRange} from './media.mjs';
assert.deepEqual(parseRange('bytes=2-5',10),{start:2,end:5});
assert.deepEqual(parseRange('bytes=5-',10),{start:5,end:9});
assert.deepEqual(parseRange('bytes=-3',10),{start:7,end:9});
assert.deepEqual(parseRange('bytes=0-99',10),{start:0,end:9});
for(const value of ['bytes=20-','bytes=5-2','bytes=-0','bytes=0-1,4-5','bytes=-','bytes=9007199254740992-']) assert.equal(parseRange(value,10),false);
const env={ASSETS:{fetch:async()=>new Response(new Uint8Array([0,1,2,3,4,5,6,7,8,9]),{headers:{'Content-Type':'video/mp4','ETag':'"test"'}})}};
const partial=await worker.fetch(new Request('https://example.test/movie.mp4',{headers:{Range:'bytes=2-5'}}),env);
assert.equal(partial.status,206);assert.equal(partial.headers.get('Content-Range'),'bytes 2-5/10');assert.deepEqual([...new Uint8Array(await partial.arrayBuffer())],[2,3,4,5]);
const invalid=await worker.fetch(new Request('https://example.test/movie.mp4',{headers:{Range:'bytes=20-'}}),env);assert.equal(invalid.status,416);assert.equal(invalid.headers.get('Content-Range'),'bytes */10');
const changed=await worker.fetch(new Request('https://example.test/movie.mp4',{headers:{Range:'bytes=2-5','If-Range':'"older"'}}),env);assert.equal(changed.status,200);assert.equal((await changed.arrayBuffer()).byteLength,10);
// Old-host redirects (301, path and query preserved).
for (const [host, sub] of [['witcher-3-lore.xiaosang.cc','/witcher-3'],['elden-ring-lore-video.xiaosang.cc','/elden-ring-video'],['dark-souls-3-lore.xiaosang.cc','/dark-souls-3']]) {
  const r = await worker.fetch(new Request(`https://${host}/`), env);
  assert.equal(r.status,301);
  assert.equal(r.headers.get('Location'),`https://lore.xiaosang.cc${sub}/`);
}
const deep = await worker.fetch(new Request('https://gta5-lore.xiaosang.cc/index.html?x=1'), env);
assert.equal(deep.status,301);
assert.equal(deep.headers.get('Location'),'https://lore.xiaosang.cc/gta5/index.html?x=1');
const hub = await worker.fetch(new Request('https://lore.xiaosang.cc/'), env);
assert.equal(hub.status,200);
console.log('Byte range, invalid range, suffix, If-Range and redirect checks passed');
