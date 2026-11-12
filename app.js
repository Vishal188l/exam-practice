/* Exam Practice — Data Analytics in Accounting
   Static single-page app. All answers come from data/bank.js, which is generated
   from the course data files by gen.py. No server, no AI, no tracking. */
(function () {
  'use strict';
  const B = window.BANK;
  const Q = Object.fromEntries(B.questions.map(q => [q.id, q]));
  const EX = Object.fromEntries(B.exams.map(e => [e.id, e]));
  const IE = Object.fromEntries(B.interp.map(e => [e.id, e]));
  const main = document.getElementById('main');

  // ---------------------------------------------------------------- storage (this browser only)
  const KEY = 'dap-progress-v1';
  let progress = {};
  try { progress = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { progress = {}; }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(progress)); } catch (e) { /* storage unavailable */ } }
  function record(id, kind) {
    const p = progress[id] || { tries: 0 };
    p.tries += 1;
    if (p.s !== 'ok') p.s = kind === 'ok' ? 'ok' : (kind === 'mistake' ? 'mistake' : 'wrong');
    if (kind === 'mistake') p.m = (p.m || 0) + 1;
    progress[id] = p; save();
  }

  // ---------------------------------------------------------------- helpers
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const h = (html) => { const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstElementChild; };
  const fmt = (v, dec) => Number(v).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const dsName = k => (B.datasets[k] || { name: k }).name;
  const toolTag = t => `<span class="tag ${t.toLowerCase()}">${esc(t)}</span>`;
  function filesHtml(keys) {
    const seen = new Set();
    return keys.flatMap(k => B.datasets[k].files).filter(f => !seen.has(f) && seen.add(f))
      .map(f => `<a href="files/${encodeURIComponent(f)}" download>⬇ ${esc(f)}</a>`).join('');
  }

  // Parse what a student types: 1,234.56 · 1.234,56 · 1234,5 · (1,234) · -44,246.84 · 7.84% · $ 3,000
  function parseNumber(raw) {
    let s = String(raw).trim().replace(/[\s ]/g, '').replace(/[−–]/g, '-').replace(/^(usd|dkk|kr\.?|\$)/i, '').replace(/(usd|dkk|kr\.?|\$)$/i, '');
    let pct = false;
    if (s.endsWith('%')) { pct = true; s = s.slice(0, -1); }
    let neg = false;
    if (/^\(.*\)$/.test(s)) { neg = true; s = s.slice(1, -1); }
    if (s.startsWith('-')) { neg = !neg; s = s.slice(1); }
    if (!/^[\d.,]+$/.test(s) || !/\d/.test(s)) return null;
    const lc = s.lastIndexOf(','), ld = s.lastIndexOf('.');
    if (lc >= 0 && ld >= 0) {               // both separators: the last one is the decimal mark
      s = lc > ld ? s.replace(/\./g, '').replace(',', '.') : s.replace(/,/g, '');
    } else if (lc >= 0) {                    // only commas
      const parts = s.split(',');
      const thousands = parts.length > 2 || parts[parts.length - 1].length === 3;
      s = thousands ? s.replace(/,/g, '') : s.replace(',', '.');
    } else if ((s.match(/\./g) || []).length > 1) {
      s = s.replace(/\./g, '');             // 1.234.567 (Danish thousands)
    }
    const v = parseFloat(s);
    if (isNaN(v)) return null;
    return { v: neg ? -v : v, pct };
  }
  const norm = s => String(s).toLowerCase().replace(/^the\s+/, '').replace(/[“”"'.]/g, '').replace(/\s+/g, ' ').trim();

  const TIPS = {
    'import': 'Check how the file was imported: delimiter, and dates read as US month/day/year.',
    'date arithmetic': 'Excel stores dates as days. Multiply by 24 for hours; make sure both columns are real dates, not text.',
    'date filter': 'Filter on the date column the question names, and check the dates were imported as US dates.',
    'conditional count': 'Re-read every condition in the question — each one needs to be in your COUNTIFS / filter.',
    'conditional sum': 'Check which column you sum and that every condition is in your SUMIFS.',
    'text extraction': 'Look at a few codes that do not follow the simple pattern before trusting LEFT/MID/RIGHT.',
    'messy text': 'The codes are not all the same length — test your formula on the odd ones.',
    'JOIN': 'Check that you join on the right key and count rows from the right table.',
    'GROUP BY': 'Check what identifies one group (e.g. first initial AND last name).',
    'HAVING': 'Filter groups with HAVING after GROUP BY; check > vs >=.',
    'regression': 'Aggregate to one row per day before running the regression, and read the right row of the output.',
    'lookup': 'Check that every row found a match in the lookup table (no #N/A).',
    'two-key lookup': 'Is the lookup key unique? If not, you need to match on two columns.',
    'percentage': 'Check the denominator, and give the answer as a percentage (e.g. 7.84).',
  };

  function grade(check, mistakes, input) {
    if (check.type === 'choice') {
      if (input == null) return { kind: 'empty' };
      return input === check.answer ? { kind: 'ok' } : { kind: 'wrong' };
    }
    if (check.type === 'text') {
      if (!String(input || '').trim()) return { kind: 'empty' };
      const n = norm(input);
      if (n === norm(check.answer) || (check.accept || []).some(a => norm(a) === n)) return { kind: 'ok' };
      const m = (mistakes || []).find(m => norm(m.value) === n);
      return m ? { kind: 'mistake', why: m.why } : { kind: 'wrong' };
    }
    const p = parseNumber(input);
    if (!String(input || '').trim()) return { kind: 'empty' };
    if (!p) return { kind: 'unparsable' };
    const tol = 0.5 * Math.pow(10, -(check.dec || 0)) + 1e-9;
    const cands = [p.v];
    if (check.pct && !p.pct) cands.push(p.v * 100);          // 0.0784 typed for 7.84 %
    const raw = String(input).trim().replace(/^-/, '');
    if (!check.dec && /^\d{1,3}(\.\d{3})+$/.test(raw)) cands.push((String(input).trim().startsWith('-') ? -1 : 1) * +raw.replace(/\./g, '')); // Danish 4.504 = 4504
    const hit = target => cands.some(c => Math.abs(c - target) <= tol);
    if (hit(check.answer)) return { kind: 'ok' };
    const m = (mistakes || []).find(m => hit(m.value));
    if (m) return { kind: 'mistake', why: m.why };
    const rel = Math.abs(p.v - check.answer) / Math.max(1, Math.abs(check.answer));
    if (rel < 0.01) return { kind: 'close' };
    if (Math.abs(p.v + check.answer) <= tol && check.answer !== 0) return { kind: 'sign' };
    return { kind: 'wrong' };
  }

  function answerText(check) {
    if (check.type === 'number') return fmt(check.answer, check.dec || 0) + (check.pct ? ' %' : '');
    return check.answer;
  }

  function feedbackHtml(res, check, skills, tries) {
    const roundTxt = check.type === 'number' ? (check.dec ? `${check.dec} decimal${check.dec > 1 ? 's' : ''}` : 'a whole number') : '';
    switch (res.kind) {
      case 'ok': return `<div class="fb ok"><b>✓ Correct.</b>The answer is ${esc(answerText(check))}.</div>`;
      case 'mistake': return `<div class="fb warn"><b>Not quite — this is a recognised mistake.</b>${esc(res.why)}</div>`;
      case 'close': return `<div class="fb warn"><b>Very close.</b>You are within 1% of the answer. Check your rounding — the answer is ${roundTxt} — or a small filter difference.</div>`;
      case 'sign': return `<div class="fb warn"><b>Right size, wrong sign.</b>Check which value you subtract from which (or whether returns should be negative).</div>`;
      case 'empty': return `<div class="fb bad"><b>No answer yet.</b>Type your result first.</div>`;
      case 'unparsable': return `<div class="fb bad"><b>That is not a number I can read.</b>Type just the number, e.g. 1234.56 or 1.234,56.</div>`;
      default: {
        const tip = skills.map(s => TIPS[s]).filter(Boolean)[0];
        return `<div class="fb bad"><b>Not correct${tries > 1 ? ` (attempt ${tries})` : ''}.</b>${tip ? esc(tip) : 'Re-read the question and check each condition.'}${tries >= 2 ? ' You can reveal the solution below.' : ''}</div>`;
      }
    }
  }

  function solutionHtml(q) {
    const body = q.tool === 'SQL' ? `<pre>${esc(q.solution)}</pre>` : `<div>${esc(q.solution)}</div>`;
    return `<div class="sol"><b>Worked solution</b> — answer: <b>${esc(answerText(q.check))}</b>${body}</div>`;
  }

  // Answer widget. mode 'practice' checks immediately; mode 'exam' only stores the input.
  function answerWidget(q, opts) {
    const c = q.check, id = 'a_' + (opts.key || q.id).replace(/\W/g, '_');
    const el = h(`<div class="answerbox"></div>`);
    let input;
    if (c.type === 'choice') {
      el.innerHTML = `<label>${esc(c.prompt || 'Choose one answer')}</label><div class="choices">${c.options.map((o, i) =>
        `<label><input type="radio" name="${id}" value="${i}">${esc(o)}</label>`).join('')}</div>`;
      input = () => { const r = el.querySelector('input:checked'); return r ? c.options[+r.value] : null; };
    } else {
      const hint = c.type === 'number' ? (c.dec ? `Number, ${c.dec} decimal${c.dec > 1 ? 's' : ''}${c.pct ? ', as a percentage' : ''}` : 'Whole number') : 'Text';
      el.innerHTML = `<label for="${id}">Your answer <span class="meta">(${hint})</span></label>
        <div class="row"><input type="text" id="${id}" autocomplete="off" inputmode="${c.type === 'number' ? 'decimal' : 'text'}"></div>`;
      input = () => el.querySelector('input').value;
    }
    const prev = opts.store && opts.store[opts.key];
    if (prev != null) {
      if (c.type === 'choice') { const i = c.options.indexOf(prev); if (i >= 0) el.querySelectorAll('input')[i].checked = true; }
      else el.querySelector('input').value = prev;
    }
    const out = h('<div aria-live="polite"></div>');
    if (opts.mode === 'practice') {
      const row = h(`<div class="row" style="margin-top:10px"><button class="btn">Check my answer</button><button class="btn sec">Show solution</button></div>`);
      const [chk, show] = row.querySelectorAll('button');
      let tries = 0, shown = false;
      const doCheck = () => {
        const res = grade(c, q.mistakes, input());
        if (!['empty', 'unparsable'].includes(res.kind)) { tries++; record(q.id, res.kind); }
        out.innerHTML = feedbackHtml(res, c, q.skills || [], tries);
        if (res.kind === 'ok' && !shown) { out.insertAdjacentHTML('beforeend', solutionHtml(q)); shown = true; }
        if (opts.onChange) opts.onChange();
      };
      chk.onclick = doCheck;
      el.addEventListener('keydown', e => { if (e.key === 'Enter' && e.target.tagName === 'INPUT' && e.target.type === 'text') doCheck(); });
      show.onclick = () => {
        if (!shown && tries < 1 && !confirm('Try first? Checking your own answer is what makes practice stick. Show the solution anyway?')) return;
        if (!shown) { out.insertAdjacentHTML('beforeend', solutionHtml(q)); shown = true; }
      };
      el.append(row, out);
    } else {
      el.addEventListener('input', () => { opts.store[opts.key] = input(); if (opts.onChange) opts.onChange(); });
      el.addEventListener('change', () => { opts.store[opts.key] = input(); if (opts.onChange) opts.onChange(); });
      el.append(out);
    }
    el.getValue = input;
    el.showResult = (res) => { out.innerHTML = feedbackHtml(res, c, q.skills || [], 1) + (res.kind === 'ok' ? '' : solutionHtml(q)); };
    return el;
  }

  // ---------------------------------------------------------------- timer
  function timer(minutes, onExpire) {
    const el = h(`<div class="timer" role="group" aria-label="Exam timer">
      <div><div class="meta">Time remaining</div><div class="clock" data-r>${minutes}:00</div></div>
      <div><div class="meta">Elapsed</div><div class="clock" data-e style="font-size:18px">0:00</div></div>
      <button class="btn small">Start timer</button><button class="btn small sec">Pause</button><button class="btn small sec">Reset</button>
      <span class="meta" data-msg aria-live="polite"></span></div>`);
    const [start, pause, reset] = el.querySelectorAll('button');
    let t = 0, id = null, fired = false;
    const mm = s => `${s < 0 ? '−' : ''}${Math.floor(Math.abs(s) / 60)}:${String(Math.abs(s) % 60).padStart(2, '0')}`;
    const draw = () => {
      const left = minutes * 60 - t;
      el.querySelector('[data-r]').textContent = mm(left);
      el.querySelector('[data-r]').classList.toggle('low', left <= 60);
      el.querySelector('[data-e]').textContent = mm(t);
      if (left <= 0 && !fired) { fired = true; el.querySelector('[data-msg]').textContent = 'Time is up — finish the question you are on, then check your answers.'; if (onExpire) onExpire(); }
    };
    start.onclick = () => { if (!id) id = setInterval(() => { t++; draw(); }, 1000); };
    pause.onclick = () => { clearInterval(id); id = null; };
    reset.onclick = () => { clearInterval(id); id = null; t = 0; fired = false; el.querySelector('[data-msg]').textContent = ''; draw(); };
    el.stop = () => clearInterval(id);
    return el;
  }
  let activeTimer = null;

  // ---------------------------------------------------------------- pages
  function home() {
    const done = Object.values(progress).filter(p => p.s === 'ok').length;
    const caught = Object.values(progress).reduce((a, p) => a + (p.m || 0), 0);
    main.innerHTML = `
      <section class="hero">
        <h1>Practise the exam you will actually get</h1>
        <p class="lead">At the oral exam you receive one data manipulation exam (Excel + SQL) and one data interpretation exam (regression). Every question here is built from the course cases and data files.</p>
        <div class="how">
          <div><b>1 · Download the data</b>The same files used in the course cases.</div>
          <div><b>2 · Solve it in Excel or SQL</b>Work exactly as you would at the exam.</div>
          <div><b>3 · Check my answer</b>Type your result. You get right/wrong instantly — and if your number matches a typical mistake, you are told which one.</div>
        </div>
      </section>
      <div class="grid">
        <div class="card"><h2 style="margin-top:0">Data manipulation exams</h2><p>${B.exams.length} exams, each with 3 Excel and 3 SQL questions on two datasets.</p><a class="btn" href="#/exams">Go to exams</a></div>
        <div class="card"><h2 style="margin-top:0">Question bank</h2><p>${B.questions.length} single questions across ${Object.keys(B.datasets).length} datasets. Filter by dataset, tool or skill.</p><a class="btn" href="#/questions">Browse questions</a></div>
        <div class="card"><h2 style="margin-top:0">Data interpretation exams</h2><p>${B.interp.length} regression exams based on the restaurant case: predict, interpret, test significance.</p><a class="btn" href="#/interp">Go to interpretation</a></div>
      </div>
      <div class="card"><b>Your progress in this browser:</b> ${done} of ${B.questions.length} questions solved${caught ? ` · ${caught} typical mistakes caught` : ''}. <a href="#/progress">See weak spots</a></div>`;
  }

  function examsPage(page = 1) {
    const per = 25, pages = Math.ceil(B.exams.length / per);
    const list = B.exams.slice((page - 1) * per, page * per).map(e => {
      const sc = progress['exam:' + e.id];
      return `<a class="item" href="#/exam/${e.id}"><span class="id">${e.id}</span>${esc(dsName(e.datasets[0]))} (Excel) + ${esc(dsName(e.datasets[1]))} (SQL) · ${e.minutes} min
        ${sc ? `<span class="status ${sc.best === 6 ? 'ok' : ''}">best ${sc.best}/6</span>` : ''}</a>`;
    }).join('');
    main.innerHTML = `<h1>Data manipulation exams</h1><p class="lead">Each exam combines three Excel questions on one dataset and three SQL questions on one database. Download both files before starting the timer — importing is part of the exam.</p>
      <div class="row"><button class="btn" id="pick">Choose one for me</button><span class="meta">${B.exams.length} exams</span></div>
      <div class="qlist">${list}</div>
      <div class="pager">${page > 1 ? `<a class="btn sec small" href="#/exams/${page - 1}">Previous</a>` : ''}<span class="meta">Page ${page} of ${pages}</span>${page < pages ? `<a class="btn sec small" href="#/exams/${page + 1}">Next</a>` : ''}</div>`;
    document.getElementById('pick').onclick = () => {
      const fresh = B.exams.filter(e => !progress['exam:' + e.id]);
      const pool = fresh.length ? fresh : B.exams;
      location.hash = '#/exam/' + pool[Math.floor(Math.random() * pool.length)].id;
    };
  }

  function examPage(id) {
    const e = EX[id]; if (!e) return notFound();
    const store = {};
    let cur = 0, finished = false;
    const results = {};
    main.innerHTML = `<p><a href="#/exams">← All exams</a></p>
      <div class="meta">DATA MANIPULATION EXAM · ${e.id} · ${e.minutes} MINUTES</div>
      <h1>Exam ${e.id}</h1>
      <div class="card files"><b>Files:</b> ${filesHtml(e.datasets)}<div class="note">Download and open both files before you press Start. Answers are checked when you press <i>Finish &amp; check</i>.</div></div>`;
    activeTimer = timer(e.minutes);
    main.append(activeTimer);
    const tabs = h('<div class="tabs" role="tablist"></div>');
    const body = h('<div class="card"></div>');
    const fin = h('<div class="row"><button class="btn">Finish &amp; check all answers</button><span class="meta" aria-live="polite"></span></div>');
    main.append(tabs, body, fin);
    const widgets = {};
    function drawTabs() {
      tabs.innerHTML = e.questions.map((qid, i) => {
        const q = Q[qid];
        const st = finished ? (results[qid] === 'ok' ? 'ok' : results[qid] === 'mistake' ? 'warn' : 'bad') : (store[qid] ? 'answered' : '');
        return `<button role="tab" class="${i === cur ? 'on' : ''}" aria-selected="${i === cur}">${String(i + 1).padStart(2, '0')} · ${q.tool}<span class="dot ${st}"></span></button>`;
      }).join('');
      tabs.querySelectorAll('button').forEach((b, i) => b.onclick = () => { cur = i; draw(); });
    }
    function draw() {
      const q = Q[e.questions[cur]];
      body.innerHTML = `<div>${toolTag(q.tool)}<span class="tag">${esc(dsName(q.dataset))}</span><span class="meta">${q.id} · ~${Math.round(q.secs / 60 * 2) / 2} min</span></div><div class="qtext">${esc(q.text)}</div>`;
      const w = answerWidget(q, { mode: 'exam', store, key: q.id, onChange: drawTabs });
      widgets[q.id] = w; body.append(w);
      if (finished) w.showResult(grade(q.check, q.mistakes, store[q.id]));
      const nav = h(`<div class="row" style="margin-top:12px">${cur > 0 ? '<button class="btn sec small">← Previous</button>' : ''}${cur < e.questions.length - 1 ? '<button class="btn sec small">Next →</button>' : ''}</div>`);
      const bs = nav.querySelectorAll('button');
      if (cur > 0) bs[0].onclick = () => { cur--; draw(); };
      if (cur < e.questions.length - 1) bs[bs.length - 1].onclick = () => { cur++; draw(); };
      body.append(nav);
      drawTabs();
    }
    fin.querySelector('button').onclick = () => {
      if (!finished && e.questions.some(q => !store[q]) && !confirm('Some questions have no answer. Finish anyway?')) return;
      finished = true; activeTimer.stop();
      let score = 0, caught = 0;
      e.questions.forEach(qid => {
        const r = grade(Q[qid].check, Q[qid].mistakes, store[qid]);
        results[qid] = r.kind; if (r.kind === 'ok') score++; if (r.kind === 'mistake') caught++;
        if (!['empty', 'unparsable'].includes(r.kind)) record(qid, r.kind);
      });
      const k = 'exam:' + e.id; progress[k] = { best: Math.max(score, (progress[k] || {}).best || 0) }; save();
      fin.innerHTML = `<div class="card" style="width:100%"><div class="score">${score} / ${e.questions.length}</div>
        <div>${caught ? `${caught} answer${caught > 1 ? 's' : ''} matched a typical mistake — open those questions to see which one.` : ''} Click each question to see feedback and the worked solution.</div>
        <div class="row" style="margin-top:10px"><a class="btn sec" href="#/exam/${e.id}" id="retry">Try again</a><a class="btn" href="#/exams">Another exam</a></div></div>`;
      fin.querySelector('#retry').onclick = (ev) => { ev.preventDefault(); route(true); };
      draw();
    };
    draw();
  }

  let qFilter = { tool: '', ds: '', skill: '', status: '', text: '', page: 1 };
  function questionsPage() {
    const skills = [...new Set(B.questions.flatMap(q => q.skills))].sort();
    main.innerHTML = `<h1>Question bank</h1><p class="lead">Single questions you can practise one at a time. Each one checks your answer and explains typical mistakes.</p>
      <div class="filters">
        <select id="f_tool" aria-label="Tool"><option value="">Excel and SQL</option><option>Excel</option><option>SQL</option></select>
        <select id="f_ds" aria-label="Dataset"><option value="">All datasets</option>${Object.entries(B.datasets).map(([k, d]) => `<option value="${k}">${esc(d.name)} (${d.count})</option>`).join('')}</select>
        <select id="f_skill" aria-label="Skill"><option value="">All skills</option>${skills.map(s => `<option>${esc(s)}</option>`).join('')}</select>
        <select id="f_status" aria-label="Status"><option value="">Any status</option><option value="new">Not tried</option><option value="open">Tried, not solved</option><option value="ok">Solved</option></select>
        <input type="search" id="f_text" placeholder="Search questions" aria-label="Search">
      </div><div id="res"></div>`;
    const ids = ['tool', 'ds', 'skill', 'status', 'text'];
    ids.forEach(k => { const el = document.getElementById('f_' + k); el.value = qFilter[k]; el.oninput = () => { qFilter[k] = el.value; qFilter.page = 1; drawList(); }; });
    function drawList() {
      const f = qFilter, t = f.text.toLowerCase();
      const list = B.questions.filter(q => (!f.tool || q.tool === f.tool) && (!f.ds || q.dataset === f.ds) && (!f.skill || q.skills.includes(f.skill)) &&
        (!t || q.text.toLowerCase().includes(t) || q.id.toLowerCase() === t) &&
        (!f.status || (f.status === 'new' ? !progress[q.id] : f.status === 'ok' ? (progress[q.id] || {}).s === 'ok' : progress[q.id] && progress[q.id].s !== 'ok')));
      const per = 25, pages = Math.max(1, Math.ceil(list.length / per)); f.page = Math.min(f.page, pages);
      const items = list.slice((f.page - 1) * per, f.page * per).map(q => {
        const p = progress[q.id];
        return `<a class="item" href="#/q/${q.id}"><span class="id">${q.id}</span>${esc(q.text)}
          ${p ? `<span class="status ${p.s === 'ok' ? 'ok' : 'bad'}">${p.s === 'ok' ? '✓ solved' : 'not yet'}</span>` : ''}
          <div>${toolTag(q.tool)}<span class="tag">${esc(dsName(q.dataset))}</span>${q.skills.map(s => `<span class="tag">${esc(s)}</span>`).join('')}${q.mistakes.length ? `<span class="meta"> · ${q.mistakes.length} typical mistake${q.mistakes.length > 1 ? 's' : ''} recognised</span>` : ''}</div></a>`;
      }).join('');
      const res = document.getElementById('res');
      res.innerHTML = `<div class="meta">${list.length} questions</div><div class="qlist">${items || '<p>No questions match.</p>'}</div>
        <div class="pager"><button class="btn sec small" ${f.page <= 1 ? 'disabled' : ''}>Previous</button><span class="meta">Page ${f.page} of ${pages}</span><button class="btn sec small" ${f.page >= pages ? 'disabled' : ''}>Next</button></div>`;
      const [pv, nx] = res.querySelectorAll('.pager button');
      pv.onclick = () => { f.page--; drawList(); window.scrollTo(0, 0); };
      nx.onclick = () => { f.page++; drawList(); window.scrollTo(0, 0); };
    }
    drawList();
  }

  function questionPage(id) {
    const q = Q[id]; if (!q) return notFound();
    const n = B.questions.indexOf(q);
    main.innerHTML = `<p><a href="#/questions">← Back to questions</a></p>
      <div class="meta">QUESTION · ${q.id}${q.source ? ' · from ' + esc(q.source) : ''}</div>
      <div class="card">
        <div>${toolTag(q.tool)}<span class="tag">${esc(dsName(q.dataset))}</span>${q.skills.map(s => `<span class="tag">${esc(s)}</span>`).join('')}<span class="meta"> · ~${Math.round(q.secs / 60 * 2) / 2} min</span></div>
        <div class="files" style="margin:8px 0"><b>File:</b> ${filesHtml([q.dataset])}</div>
        <div class="qtext">${esc(q.text)}</div>
      </div>`;
    const card = main.querySelector('.card');
    card.append(answerWidget(q, { mode: 'practice' }));
    main.append(h(`<div class="row">${n > 0 ? `<a class="btn sec small" href="#/q/${B.questions[n - 1].id}">← Previous question</a>` : ''}${n < B.questions.length - 1 ? `<a class="btn sec small" href="#/q/${B.questions[n + 1].id}">Next question →</a>` : ''}</div>`));
  }

  function interpList() {
    const items = B.interp.map(e => {
      const sc = progress['exam:' + e.id];
      return `<a class="item" href="#/interp/${e.id}"><span class="id">${e.id}</span>Restaurant sales — ${esc(e.model)} model · 4 questions${sc ? `<span class="status ${sc.best === 4 ? 'ok' : ''}">best ${sc.best}/4</span>` : ''}</a>`;
    }).join('');
    main.innerHTML = `<h1>Data interpretation exams</h1><p class="lead">Each exam shows the output of a regression run on the restaurant case data (daily sales, weather and football games). Read the output, make a prediction and interpret the results. 5 minutes per exam.</p>
      <div class="row"><button class="btn" id="pick">Choose one for me</button></div><div class="qlist">${items}</div>`;
    document.getElementById('pick').onclick = () => {
      const fresh = B.interp.filter(e => !progress['exam:' + e.id]); const pool = fresh.length ? fresh : B.interp;
      location.hash = '#/interp/' + pool[Math.floor(Math.random() * pool.length)].id;
    };
  }

  function interpPage(id) {
    const e = IE[id]; if (!e) return notFound();
    const store = {}; let finished = false;
    const pfmt = p => p < 0.001 ? '< 0.001' : p.toFixed(3);
    main.innerHTML = `<p><a href="#/interp">← All interpretation exams</a></p>
      <div class="meta">DATA INTERPRETATION EXAM · ${e.id}</div><h1>Restaurant sales — ${esc(e.model)}</h1>
      <div class="card"><p>Bob's restaurant: the outcome is <b>total daily sales (USD)</b>. ${e.n} days of 2018 data.</p>
        <table><tr><th>Variable</th><th>Meaning</th></tr>${e.vars.map(v => `<tr><td>${esc(v.name)}</td><td>${esc(v.desc)}</td></tr>`).join('')}</table>
        <p><code>${esc(e.equation)}</code></p>
        <table><tr><th>Parameter</th><th>Term</th><th>Estimate</th><th>p-value</th></tr>
        ${e.rows.map(r => `<tr><td>${r.name}</td><td>${esc(r.term)}</td><td class="num">${fmt(r.est, 4)}</td><td class="num">${pfmt(r.p)}</td></tr>`).join('')}</table>
        <div class="meta">R² = ${e.r2.toFixed(4)} · n = ${e.n}</div></div>`;
    activeTimer = timer(5); main.append(activeTimer);
    const widgets = [];
    e.questions.forEach((iq, i) => {
      const q = { id: e.id + '-' + (i + 1), check: iq.check, mistakes: iq.mistakes, solution: iq.solution, tool: 'Interpretation', skills: [] };
      const c = h(`<div class="card"><div class="meta">Question ${i + 1}</div><div class="qtext">${esc(iq.text)}</div></div>`);
      const w = answerWidget(q, { mode: 'exam', store, key: q.id }); widgets.push([q, w]); c.append(w); main.append(c);
    });
    const fin = h('<div class="row"><button class="btn">Finish &amp; check all answers</button></div>'); main.append(fin);
    fin.querySelector('button').onclick = () => {
      if (finished) return; finished = true; activeTimer.stop();
      let score = 0;
      widgets.forEach(([q, w]) => { const r = grade(q.check, q.mistakes, store[q.id]); if (r.kind === 'ok') score++; w.showResult(r); });
      const k = 'exam:' + e.id; progress[k] = { best: Math.max(score, (progress[k] || {}).best || 0) }; save();
      fin.innerHTML = `<div class="card" style="width:100%"><div class="score">${score} / 4</div><div class="row"><a class="btn sec" href="#/interp">Back to list</a></div></div>`;
    };
  }

  function progressPage() {
    const qs = B.questions;
    const tried = qs.filter(q => progress[q.id]), solved = tried.filter(q => progress[q.id].s === 'ok');
    const bySkill = {};
    qs.forEach(q => q.skills.forEach(s => {
      const b = bySkill[s] = bySkill[s] || { n: 0, tried: 0, ok: 0, m: 0 };
      b.n++; const p = progress[q.id];
      if (p) { b.tried++; if (p.s === 'ok') b.ok++; b.m += p.m || 0; }
    }));
    const weak = Object.entries(bySkill).filter(([, b]) => b.tried > 0).sort((a, b) => (a[1].ok / a[1].tried) - (b[1].ok / b[1].tried)).slice(0, 8);
    const dsRows = Object.entries(B.datasets).map(([k, d]) => {
      const n = qs.filter(q => q.dataset === k).length, ok = qs.filter(q => q.dataset === k && (progress[q.id] || {}).s === 'ok').length;
      return `<tr><td>${esc(d.name)}</td><td>${esc(d.case)}</td><td style="width:35%"><div class="bar"><span style="width:${100 * ok / n}%"></span></div></td><td class="num">${ok}/${n}</td></tr>`;
    }).join('');
    main.innerHTML = `<h1>My progress</h1><p class="lead">Stored only in this browser — nothing is sent anywhere.</p>
      <div class="card"><b>${solved.length}</b> of ${qs.length} questions solved · ${tried.length} tried</div>
      <h2>Weak spots</h2>${weak.length ? `<table><tr><th>Skill</th><th>Solved / tried</th><th>Typical mistakes made</th><th></th></tr>${weak.map(([s, b]) =>
        `<tr><td>${esc(s)}</td><td class="num">${b.ok}/${b.tried}</td><td class="num">${b.m}</td><td><a href="#/questions" data-skill="${esc(s)}">Practise</a></td></tr>`).join('')}</table>` : '<p class="meta">Try a few questions first.</p>'}
      <h2>By dataset</h2><table><tr><th>Dataset</th><th>Course case</th><th>Solved</th><th></th></tr>${dsRows}</table>
      <p><button class="btn sec small" id="reset">Reset my progress</button></p>`;
    main.querySelectorAll('[data-skill]').forEach(a => a.onclick = () => { qFilter = { tool: '', ds: '', skill: a.dataset.skill, status: '', text: '', page: 1 }; });
    document.getElementById('reset').onclick = () => { if (confirm('Delete all progress stored in this browser?')) { progress = {}; save(); progressPage(); } };
  }

  function notFound() { main.innerHTML = '<h1>Not found</h1><p><a href="#/">Go to the start page</a></p>'; }

  // ---------------------------------------------------------------- router
  function route(force) {
    if (activeTimer) { activeTimer.stop(); activeTimer = null; }
    const parts = location.hash.replace(/^#\/?/, '').split('/');
    document.querySelectorAll('[data-nav]').forEach(a => a.classList.toggle('on', a.dataset.nav === parts[0] || (parts[0] === 'exam' && a.dataset.nav === 'exams') || (parts[0] === 'q' && a.dataset.nav === 'questions')));
    switch (parts[0]) {
      case '': home(); break;
      case 'exams': examsPage(+parts[1] || 1); break;
      case 'exam': examPage(parts[1]); break;
      case 'questions': questionsPage(); break;
      case 'q': questionPage(parts[1]); break;
      case 'interp': parts[1] ? interpPage(parts[1]) : interpList(); break;
      case 'progress': progressPage(); break;
      default: notFound();
    }
    if (!force) { window.scrollTo(0, 0); main.focus({ preventScroll: true }); }
  }
  window.addEventListener('hashchange', () => route());
  route();
})();
