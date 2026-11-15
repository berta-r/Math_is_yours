/* Standalone problem map (T-107). Precomputed coordinates from /api/map, no layout work
   and no external requests. Pan/zoom logic copied from graph.js (KnowledgeMap). */
const PALETTE = ['#2f6f4f', '#c0703a', '#4a6fa5', '#9c4f7d', '#7a8c2e', '#3d8f8c', '#b5523b', '#6b5aa6',
  '#c49a2c', '#55794a', '#a2475f', '#2d7a9a', '#8a6d3b', '#5f8f6b', '#7d6f91'];
const NS = 'http://www.w3.org/2000/svg';
const W = 600, H = 520, PAD = 18;
const $ = id => document.getElementById(id);
const colour = cluster => PALETTE[((cluster % PALETTE.length) + PALETTE.length) % PALETTE.length];

const state = {student: '', nodes: [], byId: new Map(), transform: {x: 0, y: 0, k: 1}, drag: null, suppressClick: false, goal: null};
const svg = $('map');
svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

function element(tag, attrs = {}) {
  const node = document.createElementNS(NS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}
function status(text) { $('status').textContent = text; }

async function post(route, data) {
  const response = await fetch('/api/' + route, {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({student: state.student, ...data})});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Request failed');
  return body;
}

function point(event) {
  const p = svg.createSVGPoint(); p.x = event.clientX; p.y = event.clientY;
  return p.matrixTransform(svg.getScreenCTM().inverse());
}
function paintTransform() {
  if (state.world) state.world.setAttribute('transform', `translate(${state.transform.x} ${state.transform.y}) scale(${state.transform.k})`);
}
function zoom(factor, at = {x: W / 2, y: H / 2}) {
  const next = Math.min(12, Math.max(.6, state.transform.k * factor)), ratio = next / state.transform.k;
  state.transform.x = at.x - (at.x - state.transform.x) * ratio;
  state.transform.y = at.y - (at.y - state.transform.y) * ratio;
  state.transform.k = next; paintTransform();
}
function reset() { state.transform = {x: 0, y: 0, k: 1}; paintTransform(); }

function draw(data) {
  svg.replaceChildren();
  state.nodes = data.nodes; state.byId = new Map(data.nodes.map(n => [n.id, n]));
  const xs = data.nodes.map(n => n.x), ys = data.nodes.map(n => n.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const scale = Math.min((W - 2 * PAD) / Math.max(1e-9, maxX - minX), (H - 2 * PAD) / Math.max(1e-9, maxY - minY));
  const offX = (W - scale * (maxX - minX)) / 2, offY = (H - scale * (maxY - minY)) / 2;
  data.nodes.forEach(n => { n.px = offX + (n.x - minX) * scale; n.py = offY + (n.y - minY) * scale; });
  state.world = element('g'); svg.append(state.world);
  const dots = element('g');
  state.route = element('g');
  // Solved dots last so their rings sit on top.
  const order = [...data.nodes].sort((a, b) => (a.solved - b.solved) || a.id.localeCompare(b.id));
  for (const n of order) {
    const cls = n.solved ? 'solved' : n.exposed ? 'exposed' : 'unseen';
    const dot = element('circle', {cx: n.px.toFixed(2), cy: n.py.toFixed(2), r: n.solved ? 5 : 3, fill: colour(n.cluster),
      class: `dot ${cls}`, 'data-id': n.id});
    n.element = dot; dots.append(dot);
  }
  state.world.append(dots, state.route);
  paintTransform();
  legend(data.clusters, data.nodes);
}

function legend(clusters, nodes) {
  const list = $('legend'); list.replaceChildren();
  const counts = new Map();
  nodes.forEach(n => counts.set(n.cluster, (counts.get(n.cluster) || 0) + 1));
  const rows = clusters.length ? clusters : [...counts.keys()].sort((a, b) => a - b).map(id => ({id, keywords: []}));
  for (const c of rows) {
    const li = document.createElement('li');
    const swatch = document.createElement('i'); swatch.className = 'swatch'; swatch.style.background = colour(c.id);
    const text = document.createElement('span');
    const words = (c.keywords || []).slice(0, 4).join(', ') || 'mixed';
    const count = counts.get(c.id) || c.size || 0;
    text.textContent = words;
    const meta = document.createElement('small');
    meta.textContent = `${count} problem${count === 1 ? '' : 's'}${c.mean_level != null ? ` · about level ${Math.round(Number(c.mean_level))}` : ''}`;
    text.append(meta);
    li.append(swatch, text); list.append(li);
  }
}

function tooltip(event, node) {
  const tip = $('tooltip');
  if (!node) { tip.hidden = true; return; }
  const box = svg.parentElement.getBoundingClientRect();
  tip.textContent = `${node.id} · level ${node.level ?? '?'}${node.solved ? ' · solved' : node.exposed ? ' · tried' : ''}`;
  tip.style.left = `${event.clientX - box.left}px`; tip.style.top = `${event.clientY - box.top}px`;
  tip.hidden = false;
}

async function choose(id) {
  const goal = state.byId.get(id);
  if (!goal) return;
  state.nodes.forEach(n => n.element.classList.toggle('goal', n.id === id));
  status(`Finding a path to ${id}…`);
  try {
    const lang = (navigator.language || 'en').toLowerCase().startsWith('ca') ? 'cat' : 'eng';
    const result = await post('path', {goal: id, language: lang});
    showPath(result);
    status('');
  } catch (error) { status(error.message); }
}

function showPath(result) {
  state.route.replaceChildren();
  const list = $('steps'); list.replaceChildren();
  const summary = $('path-summary');
  if (!result.reachable) { summary.textContent = `No connected path to ${result.goal} yet. Try a nearby problem.`; return; }
  if (!result.steps.length) { summary.textContent = `You already solved ${result.goal}.`; return; }
  const more = result.remaining ? ` (${result.remaining} earlier steps not shown)` : '';
  summary.textContent = `${result.steps.length} step${result.steps.length === 1 ? '' : 's'} to ${result.goal}${more}.`;
  const points = result.steps.map(s => state.byId.get(s.id)).filter(Boolean);
  if (points.length > 1) state.route.append(element('polyline', {class: 'route', points: points.map(n => `${n.px.toFixed(2)},${n.py.toFixed(2)}`).join(' ')}));
  points.forEach(n => state.route.append(element('circle', {class: 'route-stop', cx: n.px.toFixed(2), cy: n.py.toFixed(2), r: 3.5, 'data-id': n.id})));
  for (const step of result.steps) {
    const li = document.createElement('li');
    const head = document.createElement('p');
    if (step.key) {
      const link = document.createElement('a');
      link.href = '/?problem=' + encodeURIComponent(step.key); link.textContent = step.id;
      head.append(link);
    } else head.textContent = step.id;
    const meta = document.createElement('small');
    meta.textContent = `Level ${step.level ?? '?'}`;
    li.append(head, meta);
    if (step.text_preview) {
      const text = document.createElement('p'); text.textContent = step.text_preview + (step.text_preview.length >= 90 ? '…' : '');
      li.append(text);
    }
    list.append(li);
  }
}

svg.addEventListener('pointerdown', event => {
  if (state.drag || event.button !== 0) return;
  const p = point(event);
  state.drag = {pointer: event.pointerId, id: event.target.closest('[data-id]')?.dataset.id, point: p, start: p, moved: false};
  state.suppressClick = false; svg.setPointerCapture(event.pointerId);
});
svg.addEventListener('pointermove', event => {
  if (!state.drag) { const id = event.target.closest?.('[data-id]')?.dataset.id; tooltip(event, id && state.byId.get(id)); return; }
  if (event.pointerId !== state.drag.pointer) return;
  const p = point(event), dx = p.x - state.drag.point.x, dy = p.y - state.drag.point.y;
  if (Math.hypot(p.x - state.drag.start.x, p.y - state.drag.start.y) > 5) state.drag.moved = true;
  if (state.drag.moved) { state.transform.x += dx; state.transform.y += dy; paintTransform(); tooltip(event, null); }
  state.drag.point = p;
});
function end(event) {
  if (!state.drag || event.pointerId !== state.drag.pointer) return;
  const {id, moved} = state.drag; state.drag = null;
  if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId);
  // Pointer capture retargets clicks to the SVG, so choose on release.
  if (id && !moved) choose(id);
}
svg.addEventListener('pointerup', end);
svg.addEventListener('pointercancel', end);
svg.addEventListener('pointerleave', event => tooltip(event, null));
svg.addEventListener('wheel', event => { event.preventDefault(); zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15, point(event)); }, {passive: false});
svg.addEventListener('keydown', event => {
  if (event.key === '+' || event.key === '=') zoom(1.2);
  else if (event.key === '-') zoom(1 / 1.2);
  else if (event.key === '0') reset();
  else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
    const shifts = {ArrowLeft: [35, 0], ArrowRight: [-35, 0], ArrowUp: [0, 35], ArrowDown: [0, -35]};
    state.transform.x += shifts[event.key][0]; state.transform.y += shifts[event.key][1]; paintTransform();
  } else return;
  event.preventDefault();
});
$('zoom-in').onclick = () => zoom(1.3);
$('zoom-out').onclick = () => zoom(1 / 1.3);
$('zoom-reset').onclick = reset;

async function load() {
  status('Loading the map…');
  try {
    const data = await post('map', {edges: false});
    if (!data.enabled) { status('The problem map is not installed on this device (data/ml/problem_map.json).'); return; }
    draw(data);
    const solved = data.nodes.filter(n => n.solved).length;
    status(`${data.nodes.length} problems. ${state.student}, you have solved ${solved}.`);
  } catch (error) { status(error.message); }
}

$('who').addEventListener('submit', event => {
  event.preventDefault();
  const name = $('student').value.trim();
  if (!name) return;
  state.student = name;
  const url = new URL(location.href); url.searchParams.set('student', name); history.replaceState(null, '', url);
  load();
});
const initial = new URLSearchParams(location.search).get('student');
if (initial && initial.trim()) { $('student').value = initial.trim(); state.student = initial.trim(); load(); }
else status('Enter your nickname to see your map.');
