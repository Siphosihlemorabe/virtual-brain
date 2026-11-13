/* Spam Lab screen: you do the maths, the colleague runs it on a whole inbox.
   All checking and classifying happens on the server (app/spamlab.py); this file draws and collects input. */
(function () {
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  let D = null, root = null;
  const st = { words: [], table: {}, tableRes: null, hand: '', handRes: null, mode: 'mine', threshold: 0.5, run: null,
               manual: {}, manualStart: null, explain: null, showManual: false };

  async function post(url, data) {
    const body = new FormData();
    Object.entries(data).forEach(([k, v]) => body.append(k, typeof v === 'string' ? v : JSON.stringify(v)));
    const r = await fetch(url, { method: 'POST', body });
    const d = await r.json();
    if (window.poll) window.poll();
    if (!r.ok) throw new Error(d.detail || 'Something went wrong.');
    return d;
  }
  const cells = () => ['p_spam', 'p_ham', ...st.words.map(w => `p_${w}_spam`), ...st.words.map(w => `p_${w}_ham`)];
  const has = (e, w) => new RegExp(`\\b${w}\\b`, 'i').test(e.subject + ' ' + e.body);
  const mark = (text, words) => words.reduce((t, w) => t.replace(new RegExp(`\\b(${w})\\b`, 'gi'), '<mark>$1</mark>'), esc(text));

  function meaning(n) {
    if (n === 'p_spam') return 'spam emails ÷ all 20 emails';
    if (n === 'p_ham') return 'normal emails ÷ all 20 emails';
    const [, w, pile] = n.match(/^p_(.+)_(spam|ham)$/);
    return `${pile === 'spam' ? 'spam' : 'normal'} emails containing “${w}” ÷ ${pile === 'spam' ? 'spam' : 'normal'} emails`;
  }
  function label(n) {
    if (n === 'p_spam') return 'P(spam)';
    if (n === 'p_ham') return 'P(ham)';
    const [, w, pile] = n.match(/^p_(.+)_(spam|ham)$/);
    return `P(${w} | ${pile})`;
  }

  // ---------------------------------------------------------------- sections
  function intro() {
    return `<div class="card"><div class="row" style="margin:0 0 6px"><button class="btn ghost small" id="sl-back">← Back to Real world</button></div>
      <h2>Spam Lab: how a spam filter really works</h2>
      <p class="lead" style="margin:0">Your phone sorts thousands of emails a day with <b>Naive Bayes</b>. It is not magic: it is the basic probability
      from your chapter, <b>P(E) = n(E) ÷ n(S)</b>, used inside two piles of email and then multiplied. You do the maths; your colleague runs it on a whole inbox.</p></div>`;
  }

  function problem() {
    const n = Object.keys(st.manual).length, total = D.inbox.length;
    const right = Object.entries(st.manual).filter(([id, l]) => D.inbox.find(e => e.id === id).label === l).length;
    const secs = st.manualStart ? (Date.now() - st.manualStart) / 1000 : 0;
    const left = n ? Math.round(secs / n * (total - n) / 60) : null;
    return `<div class="card"><h3>1. The problem: ${total} emails just arrived</h3>
      <p class="muted" style="margin:4px 0 10px">Some are spam, some are from friends, family and school. Someone has to sort them.</p>
      ${st.showManual ? `<div class="sl-progress"><b>${n}</b> of ${total} sorted by hand · ${right} right · ${Math.round(secs)}s so far
        ${left !== null ? ` · at this pace the rest takes about <b>${left} more minute${left === 1 ? '' : 's'}</b>` : ''}</div>` : ''}
      <div class="sl-inbox">${D.inbox.map(e => `<div class="sl-mail ${st.manual[e.id] ? 'done' : ''}" data-id="${e.id}">
          <div class="sl-from">${esc(e.from)}</div><div class="sl-subj"><b>${esc(e.subject)}</b> <span class="muted">${esc(e.body)}</span></div>
          ${st.showManual ? (st.manual[e.id] ? `<span class="tag">${st.manual[e.id] === 'spam' ? 'Spam' : 'Inbox'}</span>`
            : `<button class="chip" data-sort="spam">Spam</button><button class="chip" data-sort="ham">Not spam</button>`) : ''}</div>`).join('')}</div>
      <div class="row">${st.showManual ? '' : '<button class="btn ghost" id="sl-manual">Sort them myself</button>'}
        <a class="btn" href="#sl-learn">Let the maths do it ↓</a></div></div>`;
  }

  function learnFrom() {
    const r = st.tableRes;
    return `<div class="card" id="sl-learn"><h3>2. Learn from 20 emails someone already labelled</h3>
      <p class="muted" style="margin:4px 0 10px">Pick the words the filter should watch (up to 5). Watched words are highlighted below.</p>
      <div class="chips">${D.candidates.map(w => `<button class="chip pick ${st.words.includes(w) ? 'on' : ''}" data-word="${w}" aria-pressed="${st.words.includes(w)}">${w}</button>`).join('')}</div>
      <div class="sl-train">${['spam', 'ham'].map(pile => `<div><h4>${pile === 'spam' ? 'Spam pile' : 'Normal (ham) pile'} · ${D.training.filter(e => e.label === pile).length} emails</h4>
        ${D.training.filter(e => e.label === pile).map(e => `<div class="sl-mail small"><b>${mark(e.subject, st.words)}</b> <span class="muted">${mark(e.body, st.words)}</span></div>`).join('')}</div>`).join('')}</div>
      <h4 style="margin-top:14px">Your probability table</h4>
      <p class="muted" style="margin:0 0 8px;font-size:14px">Each cell is basic probability: count, then divide. For a word, the sample space is just one pile, so the bottom of the fraction is the size of that pile.</p>
      <table class="sl-table"><thead><tr><th>Probability</th><th>What to count</th><th>Your answer</th><th></th></tr></thead><tbody>
      ${cells().map(n => { const c = r && r.cells[n]; return `<tr><td><b>${label(n)}</b></td><td class="muted">${meaning(n)}</td>
        <td><input class="sl-cell" data-cell="${n}" value="${esc(st.table[n] || '')}" placeholder="e.g. 7/10" aria-label="${label(n)}"></td>
        <td>${c ? (c.ok ? '<span class="tag good">✓</span>' : `<span class="tag warn">✗</span> <span class="muted" style="font-size:12px">${esc(c.hint)}</span>`) : ''}</td></tr>`; }).join('')}
      </tbody></table>
      <div class="row"><button class="btn" id="sl-check-table">Check my table</button>
        <span class="muted" style="font-size:12px">Demo:</span><button class="chip" data-demo="table-slip">With a mistake</button><button class="chip" data-demo="table">Correct</button></div>
      ${r ? `<div class="verdict ${r.all_ok ? 'ok' : 'bad'}"><b>Reviewer:</b> ${r.all_ok ? 'Every cell matches the counts. Your filter has learned.' : `${r.wrong.length} cell(s) need another look. Hints are next to them.`}</div>` : ''}</div>`;
  }

  function byHand() {
    const e = D.inbox.find(x => x.id === D.hand_email), present = st.words.filter(w => has(e, w));
    return `<div class="card"><h3>3. Classify one email by hand</h3>
      <div class="sl-mail"><div class="sl-from">${esc(e.from)}</div><div><b>${mark(e.subject, st.words)}</b> <span class="muted">${mark(e.body, st.words)}</span></div></div>
      <div class="task" style="margin-top:10px">Watched words in this email: <b>${present.join(', ') || 'none'}</b>
score_spam = P(spam)${present.map(w => ` × P(${w} | spam)`).join('')}
score_ham = P(ham)${present.map(w => ` × P(${w} | ham)`).join('')}
p_spam = score_spam ÷ (score_spam + score_ham)      ← the chance this email is spam</div>
      <textarea class="mono" id="sl-hand" rows="3" style="margin-top:10px" placeholder="score_spam = 1/2 * … = …">${esc(st.hand)}</textarea>
      <div class="row"><button class="btn" id="sl-check-hand">Check my working</button>
        <span class="muted" style="font-size:12px">Demo:</span><button class="chip" data-demo="hand-slip">With a slip</button><button class="chip" data-demo="hand">Correct</button></div>
      ${st.handRes ? `<div class="verdict ${st.handRes.ok ? 'ok' : 'bad'}"><b>Reviewer:</b> ${esc(st.handRes.msg)}</div>` : ''}
      <details class="sl-why"><summary>Why multiply? (the “naive” part)</summary><p>Naive Bayes pretends each word appears independently of the others,
        like separate dice rolls, so it can multiply their probabilities. Real words are not independent (“win” and “prize” often come together),
        which is why it is called <i>naive</i>. It is still surprisingly good, and very fast.</p></details>
      <details class="sl-why"><summary>What if a probability is 0? (the zero problem)</summary><p>If a word never appeared in the normal pile,
        P(word | ham) = 0, and multiplying by 0 makes score_ham 0 no matter what else the email says. Data scientists fix this with
        <b>smoothing</b>: add 1 to every count (and 2 to every pile), so nothing is ever exactly impossible. Try it in step 4.</p></details></div>`;
  }

  function runPanel() {
    const r = st.run;
    return `<div class="card"><h3>4. Let your colleague run your maths on all ${D.inbox.length} emails</h3>
      <div class="sl-controls">
        <label><input type="radio" name="sl-mode" value="mine" ${st.mode === 'mine' ? 'checked' : ''}> Use <b>my table</b></label>
        <label><input type="radio" name="sl-mode" value="smoothed" ${st.mode === 'smoothed' ? 'checked' : ''}> Use the colleague's table <b>with smoothing</b></label>
        <label class="slider">Call it spam when P(spam | email) is more than <b id="sl-th-v">${st.threshold.toFixed(2)}</b>
          <input type="range" id="sl-th" min="0.05" max="0.95" step="0.05" value="${st.threshold}"></label></div>
      <div class="row"><button class="btn" id="sl-run">Run the filter</button></div>
      ${r ? `<div class="sl-score"><div><b>${r.right}/${r.total}</b>sorted right (${Math.round(r.accuracy * 100)}%)</div>
          <div><b>${r.tally.caught}</b>spam caught</div><div><b>${r.tally.missed}</b>spam missed</div><div><b>${r.tally.blocked}</b>good emails blocked</div>
          <div><b>${r.ms} ms</b>to sort them all</div></div>
        ${Object.keys(st.manual).length ? `<p class="muted" style="font-size:14px">By hand you sorted ${Object.keys(st.manual).length} emails in ${Math.round((Date.now() - st.manualStart) / 1000)}s. Your maths sorted all ${r.total} in ${r.ms} ms.</p>` : ''}
        <div class="sl-bins"><div><h4>🚫 Spam folder</h4><div class="sl-bin" id="sl-bin-spam"></div></div>
          <div><h4>📥 Inbox</h4><div class="sl-bin" id="sl-bin-ham"></div></div></div>
        <p class="muted" style="font-size:13px">Red outline = the filter got it wrong. Click any email to see its maths in English and in Python.</p>
        <div id="sl-explain"></div>` : ''}</div>`;
  }

  function codePanel() {
    return `<div class="card"><h3>5. The real code, explained line by line</h3>
      <p class="muted" style="margin:4px 0 10px">This is exactly the Python your colleague ran on the server, nothing hidden.</p>
      ${D.code.map(b => `<div class="sl-code"><pre>${esc(b.python)}</pre><div class="sl-en">${esc(b.english)}</div></div>`).join('')}</div>`;
  }

  // ---------------------------------------------------------------- behaviour
  function render() {
    root.innerHTML = intro() + problem() + learnFrom() + byHand() + runPanel() + codePanel();
    if (st.run) fillBins(false);
    if (st.explain) showExplain(st.explain);
  }

  function fillBins(animate) {
    const spam = root.querySelector('#sl-bin-spam'), ham = root.querySelector('#sl-bin-ham');
    if (!spam) return;
    spam.innerHTML = ham.innerHTML = '';
    const items = st.run.results;
    const add = r => {
      const e = D.inbox.find(x => x.id === r.id);
      const b = document.createElement('button');
      b.className = 'sl-chip' + (r.correct ? '' : ' wrong'); b.dataset.id = r.id;
      b.title = `${e.subject} · P(spam) = ${r.p}`;
      b.textContent = e.subject.length > 26 ? e.subject.slice(0, 25) + '…' : e.subject;
      (r.verdict === 'spam' ? spam : ham).appendChild(b);
    };
    if (!animate || reduceMotion) return items.forEach(add);
    items.forEach((r, i) => setTimeout(() => add(r), i * 12));
  }

  async function showExplain(id) {
    st.explain = id;
    const box = root.querySelector('#sl-explain');
    if (!box) return;
    try {
      const d = await post('/api/spamlab/explain', { email: id, words: st.words, table: st.table, mode: st.mode, threshold: String(st.threshold) });
      box.innerHTML = `<div class="sl-why-box"><div><b>${esc(d.subject)}</b> <span class="muted">${esc(d.body)}</span><br>
          <span class="tag ${d.verdict === d.label ? 'good' : 'warn'}">filter says ${d.verdict === 'spam' ? 'spam' : 'inbox'} · really ${d.label === 'spam' ? 'spam' : 'a normal email'}</span></div>
        <div class="sl-code"><div class="sl-en">${d.english.map(esc).join('<br>')}</div><pre>${esc(d.python.join('\n'))}</pre></div></div>`;
    } catch (err) { box.innerHTML = `<div class="error">${esc(err.message)}</div>`; }
  }

  async function demo(kind) {
    const slip = kind.endsWith('-slip');
    if (kind.startsWith('table')) {
      const d = await (await fetch(`/api/spamlab/demo?words=${encodeURIComponent(JSON.stringify(st.words))}&slip=${slip}`)).json();
      st.table = d.table; st.tableRes = null;
    } else {
      const d = await (await fetch(`/api/spamlab/demo?words=${encodeURIComponent(JSON.stringify(st.words))}&slip=${slip}&part=hand`)).json();
      st.hand = d.working; st.handRes = null;
    }
    render();
  }

  function bind() {
    root.addEventListener('click', async ev => {
      const t = ev.target.closest('button, a');
      if (!t || !root.contains(t)) return;
      try {
        if (t.id === 'sl-back') { window.showView('study'); return; }
        if (t.id === 'sl-manual') { st.showManual = true; render(); return; }
        if (t.dataset.sort) {
          const id = t.closest('.sl-mail').dataset.id;
          st.manualStart = st.manualStart || Date.now(); st.manual[id] = t.dataset.sort;
          const y = window.scrollY; render(); window.scrollTo(0, y); return;
        }
        if (t.dataset.word) {
          const w = t.dataset.word;
          st.words = st.words.includes(w) ? st.words.filter(x => x !== w) : (st.words.length < 5 ? [...st.words, w] : st.words);
          if (!st.words.length) st.words = [w];
          st.table = {}; st.tableRes = st.handRes = st.run = st.explain = null; st.hand = '';
          const y = window.scrollY; render(); window.scrollTo(0, y); return;
        }
        if (t.dataset.demo) { await demo(t.dataset.demo); return; }
        if (t.id === 'sl-check-table') { st.tableRes = await post('/api/spamlab/table', { words: st.words, table: st.table }); render(); return; }
        if (t.id === 'sl-check-hand') { st.handRes = await post('/api/spamlab/hand', { words: st.words, working: st.hand }); render(); return; }
        if (t.id === 'sl-run') {
          const t0 = performance.now();
          st.run = await post('/api/spamlab/run', { words: st.words, table: st.table, mode: st.mode, threshold: String(st.threshold) });
          st.run.ms = Math.max(1, Math.round(performance.now() - t0)); st.explain = null;
          render(); fillBins(true); return;
        }
        if (t.classList.contains('sl-chip')) { showExplain(t.dataset.id); return; }
      } catch (err) { alertIn(t, err.message); }
    });
    root.addEventListener('input', ev => {
      const t = ev.target;
      if (t.dataset && t.dataset.cell) st.table[t.dataset.cell] = t.value;
      if (t.id === 'sl-hand') st.hand = t.value;
      if (t.id === 'sl-th') { st.threshold = +t.value; root.querySelector('#sl-th-v').textContent = st.threshold.toFixed(2); }
      if (t.name === 'sl-mode') st.mode = t.value;
    });
  }
  function alertIn(el, msg) {
    const card = el.closest('.card'); if (!card) return;
    let box = card.querySelector('.sl-err'); if (!box) { box = document.createElement('div'); box.className = 'error sl-err'; card.appendChild(box); }
    box.textContent = msg;
  }

  window.SpamLab = {
    async open(el) {
      root = el;
      if (!D) {
        root.innerHTML = '<div class="card"><div class="working"><div class="spinner"></div><div>Opening the Spam Lab…</div></div></div>';
        D = await (await fetch('/api/spamlab')).json();
        st.words = [...D.default_words];
        bind();
      }
      render();
    },
  };
})();
