// Merged lore hub worker: 301s the 7 old single-site hosts to their new
// sub-paths on lore.xiaosang.cc, and serves byte ranges for MP4s (Static
// Assets currently ignores Range on deployed MP4s; browsers need ranges
// for chapter seeking).
const REDIRECTS = {
  'elden-ring-lore.xiaosang.cc': '/elden-ring',
  'witcher-3-lore.xiaosang.cc': '/witcher-3',
  'gta5-lore.xiaosang.cc': '/gta5',
  'rdr2-lore.xiaosang.cc': '/rdr2',
  'cyberpunk-2077-lore.xiaosang.cc': '/cyberpunk-2077',
  'elden-ring-lore-video.xiaosang.cc': '/elden-ring-video',
  'dark-souls-3-lore.xiaosang.cc': '/dark-souls-3',
};

export function parseRange(value, size) {
  if (!value) return null;
  const match = /^bytes=(\d*)-(\d*)$/.exec(value);
  if (!match || (!match[1] && !match[2])) return false;
  const start = match[1] ? Number(match[1]) : Math.max(0, size - Number(match[2]));
  const end = match[1] && match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start < 0 || start >= size || end < start) return false;
  return { start, end };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const base = REDIRECTS[url.hostname];
    if (base) {
      const target = new URL(base + url.pathname, 'https://lore.xiaosang.cc');
      target.search = url.search;
      return Response.redirect(target.toString(), 301);
    }
    if (!['GET', 'HEAD'].includes(request.method) || !url.pathname.endsWith('.mp4')) {
      return env.ASSETS.fetch(request);
    }
    const sourceHeaders = new Headers(request.headers);
    sourceHeaders.delete('range');
    sourceHeaders.delete('if-range');
    const asset = await env.ASSETS.fetch(new Request(request.url, { method: 'GET', headers: sourceHeaders }));
    if (asset.status !== 200) return asset;
    const buffer = await asset.arrayBuffer();
    const size = buffer.byteLength;
    const headers = new Headers(asset.headers);
    headers.set('Accept-Ranges', 'bytes');
    headers.delete('Content-Encoding');
    const validator = request.headers.get('if-range');
    const matches = !validator || validator === headers.get('etag') || validator === headers.get('last-modified');
    const range = request.method === 'HEAD' || !matches ? null : parseRange(request.headers.get('range'), size);
    if (range === false) {
      headers.set('Content-Range', `bytes */${size}`);
      headers.delete('Content-Length');
      return new Response(null, { status: 416, headers });
    }
    if (range) {
      const bytes = new Uint8Array(buffer.slice(range.start, range.end + 1));
      headers.set('Content-Range', `bytes ${range.start}-${range.end}/${size}`);
      headers.set('Content-Length', String(bytes.byteLength));
      return new Response(bytes, { status: 206, headers });
    }
    headers.set('Content-Length', String(size));
    return new Response(request.method === 'HEAD' ? null : new Uint8Array(buffer), { headers });
  },
};
