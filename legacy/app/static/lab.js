/* Virtual Brain chance lab: 3D dice and coins (three.js), experiment vs theory.
   Exact probabilities and the favourable outcomes come from the server (app/simulate.py);
   this file only rolls, counts and draws. Works without WebGL by falling back to flat faces. */
(function () {
  const states = {};          // per lab id: survives re-renders of the page
  const live = new Map();     // container element -> lab instance
  const reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const FACES = { dice: ['1', '2', '3', '4', '5', '6'], coins: ['H', 'T'] };
  const DIE_GLYPH = { 1: '⚀', 2: '⚁', 3: '⚂', 4: '⚃', 5: '⚄', 6: '⚅' };
  const PIPS = {
    1: [[.5, .5]], 2: [[.27, .27], [.73, .73]], 3: [[.27, .27], [.5, .5], [.73, .73]],
    4: [[.27, .27], [.73, .27], [.27, .73], [.73, .73]],
    5: [[.27, .27], [.73, .27], [.5, .5], [.27, .73], [.73, .73]],
    6: [[.27, .25], [.73, .25], [.27, .5], [.73, .5], [.27, .75], [.73, .75]],
  };
  // BoxGeometry face order: +x, -x, +y, -y, +z, -z. Opposite faces add to 7.
  const BOX_FACES = [1, 6, 2, 5, 3, 4];
  // rotation that turns each value's face towards the camera (+z)
  const DIE_ROT = { 3: [0, 0], 4: [0, Math.PI], 1: [0, -Math.PI / 2], 6: [0, Math.PI / 2], 2: [Math.PI / 2, 0], 5: [-Math.PI / 2, 0] };
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function canvasTexture(draw) {
    const c = document.createElement('canvas'); c.width = c.height = 128;
    draw(c.getContext('2d'));
    const t = new THREE.CanvasTexture(c); t.anisotropy = 4; return t;
  }
  function dieMaterial(v) {
    return new THREE.MeshStandardMaterial({ roughness: .45, map: canvasTexture(g => {
      g.fillStyle = '#fbfaf7'; g.fillRect(0, 0, 128, 128);
      g.strokeStyle = '#d9d4c7'; g.lineWidth = 6; g.strokeRect(3, 3, 122, 122);
      g.fillStyle = v === 1 ? '#c0392b' : '#1c1b22';
      PIPS[v].forEach(([x, y]) => { g.beginPath(); g.arc(x * 128, y * 128, v === 1 ? 15 : 11, 0, Math.PI * 2); g.fill(); });
    }) });
  }
  function coinMaterial(letter) {
    const map = canvasTexture(g => {
      g.fillStyle = '#d4a017'; g.fillRect(0, 0, 128, 128);
      g.strokeStyle = '#8a6a0c'; g.lineWidth = 8; g.beginPath(); g.arc(64, 64, 54, 0, Math.PI * 2); g.stroke();
      g.fillStyle = '#5b4206'; g.font = 'bold 64px system-ui, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(letter, 64, 68);
    });
    map.center.set(.5, .5); map.rotation = -Math.PI / 2;  // cylinder caps map the canvas sideways; turn the letter upright
    return new THREE.MeshStandardMaterial({ metalness: .5, roughness: .35, map });
  }

  function makeScene(stage, ev) {
    if (!window.THREE) return null;
    let renderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch (e) { return null; }
    const w = stage.clientWidth || 480, h = 210;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h);
    stage.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, w / h, .1, 100);
    camera.position.set(0, 2, 6.2); camera.lookAt(0, 0, 0);
    scene.add(new THREE.AmbientLight(0xffffff, .65));
    const sun = new THREE.DirectionalLight(0xffffff, .8); sun.position.set(3, 6, 5); scene.add(sun);
    const objects = [];
    for (let i = 0; i < ev.count; i++) {
      let mesh;
      if (ev.objects === 'dice') {
        mesh = new THREE.Mesh(new THREE.BoxGeometry(1.5, 1.5, 1.5), BOX_FACES.map(dieMaterial));
      } else {
        const side = new THREE.MeshStandardMaterial({ color: 0xb8860b, metalness: .6, roughness: .4 });
        const coin = new THREE.Mesh(new THREE.CylinderGeometry(.95, .95, .14, 48), [side, coinMaterial('H'), coinMaterial('T')]);
        mesh = new THREE.Group(); mesh.add(coin); coin.rotation.x = 0;  // cap faces are set by the group's x rotation
      }
      mesh.position.x = ev.count === 1 ? 0 : (i === 0 ? -1.3 : 1.3);
      scene.add(mesh); objects.push(mesh);
    }
    let anim = null;
    function frame(now) {
      if (anim) {
        const t = Math.min(1, (now - anim.start) / anim.ms), e = 1 - Math.pow(1 - t, 3);
        anim.items.forEach(a => {
          a.obj.rotation.x = a.from[0] + (a.to[0] - a.from[0]) * e;
          a.obj.rotation.y = a.from[1] + (a.to[1] - a.from[1]) * e;
          a.obj.position.y = Math.sin(Math.PI * t) * 1.1;
        });
        if (t >= 1) anim = null;
      }
      renderer.render(scene, camera);
      if (anim) requestAnimationFrame(frame);
    }
    function target(face) {
      if (ev.objects === 'dice') return DIE_ROT[face];
      return [face === 'H' ? Math.PI / 2 : -Math.PI / 2, 0];   // cap with H (top) or T (bottom) towards the camera
    }
    function show(outcome, animate) {
      const items = outcome.map((face, i) => {
        const obj = objects[i], [tx, ty] = target(face);
        const spins = animate ? 2 + Math.floor(Math.random() * 2) : 0;
        const norm = a => a % (Math.PI * 2);
        const from = [norm(obj.rotation.x), norm(obj.rotation.y)];
        return { obj, from, to: [tx + spins * Math.PI * 2, ty + (ev.objects === 'dice' ? spins * Math.PI * 2 : 0)] };
      });
      if (!animate || reduceMotion) {
        items.forEach(a => { a.obj.rotation.x = a.to[0]; a.obj.rotation.y = a.to[1]; a.obj.position.y = 0; });
        renderer.render(scene, camera); return;
      }
      anim = { start: performance.now(), ms: 750, items };
      requestAnimationFrame(frame);
    }
    function resize() {
      const nw = stage.clientWidth || w;
      renderer.setSize(nw, h); camera.aspect = nw / h; camera.updateProjectionMatrix(); renderer.render(scene, camera);
    }
    function dispose() {
      anim = null;
      scene.traverse(o => {
        if (o.geometry) o.geometry.dispose();
        (Array.isArray(o.material) ? o.material : o.material ? [o.material] : []).forEach(m => { if (m.map) m.map.dispose(); m.dispose(); });
      });
      renderer.dispose(); renderer.forceContextLoss && renderer.forceContextLoss();
    }
    return { show, resize, dispose };
  }

  function flatFaces(stage) {  // no WebGL: show the outcome as plain symbols
    const box = document.createElement('div'); box.className = 'lab-flat'; stage.appendChild(box);
    return {
      show(outcome) { box.textContent = outcome.map(f => DIE_GLYPH[f] || (f === 'H' ? 'Heads' : 'Tails')).join('  '); },
      resize() {}, dispose() {},
    };
  }

  function mount(el, events) {
    if (live.has(el) || !events.length) return;
    const id = el.dataset.lab;
    const st = states[id] = states[id] && events.some(e => e.id === states[id].eventId) ? states[id]
      : { eventId: events[0].id, n: 0, hits: 0, history: [], last: null };
    el.innerHTML = `<div class="lab">
      <div class="lab-top">${events.length > 1
        ? `<label class="muted">Experiment <select class="lab-pick">${events.map(e => `<option value="${e.id}">${esc(e.label)}</option>`).join('')}</select></label>`
        : `<b>${esc(events[0].label)}</b>`}<span class="lab-theory"></span></div>
      <div class="lab-stage" role="img" aria-label="3D view of the latest roll"></div>
      <div class="lab-last" aria-live="polite"></div>
      <div class="row lab-buttons">
        <button class="btn small" data-n="1">Roll once</button><button class="btn ghost small" data-n="10">×10</button>
        <button class="btn ghost small" data-n="100">×100</button><button class="btn ghost small" data-n="1000">×1000</button>
        <button class="chip" data-n="0">Reset</button></div>
      <div class="lab-stats"></div>
      <svg class="lab-chart" viewBox="0 0 300 110" preserveAspectRatio="none" role="img" aria-label="Running result against the theory"></svg>
      <div class="muted lab-caption">The green line is the experiment so far; the dashed line is the exact theory. Roll more and watch them meet.</div></div>`;
    const q = s => el.querySelector(s);
    if (q('.lab-pick')) q('.lab-pick').value = st.eventId;
    let ev = events.find(e => e.id === st.eventId), fav = new Set(ev.favourable), scene = null;

    function build() {
      if (scene) scene.dispose();
      q('.lab-stage').innerHTML = '';
      scene = makeScene(q('.lab-stage'), ev) || flatFaces(q('.lab-stage'));
      scene.show(st.last || (ev.objects === 'dice' ? ['3', '5'] : ['H', 'T']).slice(0, ev.count), false);
    }
    function roll() { return Array.from({ length: ev.count }, () => FACES[ev.objects][Math.floor(Math.random() * FACES[ev.objects].length)]); }
    function describe(o) {
      const sum = ev.objects === 'dice' && ev.count === 2 ? ` (sum ${+o[0] + +o[1]})` : '';
      return `${o.join(' and ')}${sum}`;
    }
    function update() {
      const [a, b] = ev.p.split('/').map(Number), p = b ? a / b : a;
      q('.lab-theory').innerHTML = `Theory: <b>${ev.p}</b> ≈ ${p.toFixed(3)} <span class="muted">(${ev.favourable.length} of ${ev.total} outcomes)</span>`;
      if (st.last) {
        const hit = fav.has(st.last.join('-'));
        q('.lab-last').innerHTML = `Last: <b>${esc(describe(st.last))}</b> ${hit ? '<span class="tag good">counts</span>' : '<span class="tag">does not count</span>'}`;
      } else q('.lab-last').textContent = 'Predict the probability first, then roll.';
      const f = st.n ? st.hits / st.n : 0;
      q('.lab-stats').innerHTML = st.n
        ? `After <b>${st.n}</b> ${ev.objects === 'dice' ? 'rolls' : 'tosses'}: ${st.hits} counted → experiment <b>${f.toFixed(3)}</b>, theory ${p.toFixed(3)}, off by ${Math.abs(f - p).toFixed(3)}`
        : 'No rolls yet.';
      const H = 110, y = v => (H - 8) - v * (H - 16), pts = st.history, maxN = Math.max(st.n, 10);
      const line = pts.map(([n, v]) => `${(n / maxN * 300).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
      q('.lab-chart').innerHTML = `<line x1="0" x2="300" y1="${y(p)}" y2="${y(p)}" class="theory"/>
        <line x1="0" x2="300" y1="${y(0)}" y2="${y(0)}" class="axis"/><line x1="0" x2="300" y1="${y(1)}" y2="${y(1)}" class="axis"/>
        ${pts.length ? `<polyline points="${line}" class="exp"/>` : ''}
        <text x="2" y="${y(1) + 10}" class="lbl">1</text><text x="2" y="${y(0) - 2}" class="lbl">0</text>`;
    }
    function run(n) {
      if (n === 0) { st.n = st.hits = 0; st.history = []; st.last = null; update(); return; }
      for (let i = 0; i < n; i++) {
        const o = roll(); st.n++; if (fav.has(o.join('-'))) st.hits++; st.last = o;
        if (st.n <= 50 || st.n % Math.ceil(st.n / 200) === 0) st.history.push([st.n, st.hits / st.n]);
      }
      if (st.history.length > 400) st.history = st.history.filter((_, i) => i % 2 === 0);
      scene.show(st.last, true); update();
    }
    el.querySelectorAll('[data-n]').forEach(b => b.onclick = () => run(+b.dataset.n));
    if (q('.lab-pick')) q('.lab-pick').onchange = e => {
      ev = events.find(x => x.id === e.target.value); fav = new Set(ev.favourable);
      Object.assign(st, { eventId: ev.id, n: 0, hits: 0, history: [], last: null }); build(); update();
    };
    build(); update();
    const onResize = () => scene && scene.resize();
    window.addEventListener('resize', onResize);
    live.set(el, { dispose() { window.removeEventListener('resize', onResize); scene && scene.dispose(); } });
  }

  window.Lab = {
    mount,
    sweep() { for (const [el, inst] of live) if (!document.body.contains(el)) { inst.dispose(); live.delete(el); } },
    webgl: () => !!window.THREE,
  };
})();
