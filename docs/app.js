/* Renascor: the catalogue list, filters, timeline, records and URL state, from data.json
 * (scripts/build_site.py). The header figures and the methodology are static in index.html. */
(function () {
'use strict';

// == Constants ==
const REPO = 'https://github.com/Pantagrueliste/renascor';
const MIN = 1450, MAX = 1700, SPAN = MAX - MIN, NBINS = 25, LANG_TOP = 8;
// [label, definition], in rank order.
const ENC = {
	tei: ['TEI XML', 'XML following the Text Encoding Initiative guidelines.'],
	xml: ['Other XML', 'XML in a project-specific schema, not TEI.'],
	json: ['JSON', 'Structured text data in JSON files.'],
	html: ['HTML', 'Texts published as web pages.'],
	wikitext: ['Wikitext', 'Wiki markup, as used by Wikisource.'],
	'plain-text': ['Plain text', 'Text files without structural markup.'],
	markdown: ['Markdown', 'Text with lightweight Markdown markup.'],
	other: ['Other', 'Another format, such as TSV, CoNLL-U or JSON.']
};
const ENC_ORDER = Object.keys(ENC);
const FILE_LABEL = {
	tei: 'TEI XML files', xml: 'Other XML files', json: 'JSON files', html: 'HTML files', wikitext: 'Wikitext files',
	'plain-text': 'Plain-text files', markdown: 'Markdown files', other: 'Other files', none: 'No files recorded'
};
const STATUS = {
	active: ['Active', 'Online and maintained.'],
	archived: ['Archived', 'Still online, but no longer maintained.'],
	discontinued: ['Discontinued', 'No longer online; the link may lead to an archived copy.']
};
const STATUS_ORDER = Object.keys(STATUS);
const SIZES = [
	['10m-plus', 'Over 10 million words'], ['1m-10m', '1–10 million words'], ['100k-1m', '100,000–1 million words'],
	['10k-100k', '10,000–100,000 words'], ['under-10k', 'Under 10,000 words'], ['none', 'No word count']
];
const SIZE_LABEL = Object.fromEntries(SIZES);
const firstDir = key => (key === 'words' || key === 'texts' ? 'desc' : 'asc');
const LIST_KEYS = ['lang', 'encoding', 'status', 'size', 'files', 'area', 'country'];
const FACET_LABEL = { lang: 'Language', encoding: 'Encoding', status: 'Status', size: 'Size', files: 'Files', area: 'Area', country: 'Country', period: 'Period' };
const FACET_VALUES = {
	lang: r => r.labels, encoding: r => [r.e.encoding], status: r => [r.e.status], size: r => [r.d.size_band || 'none'],
	files: r => r.fileKeys, area: r => r.areas, country: r => r.countries
};
const DECADES = Array.from({ length: NBINS }, (_, i) => MIN + 10 * i);
const binEnd = i => (i === NBINS - 1 ? MAX : DECADES[i] + 9);
const VIEW_KEY = 'renascor.view';

// == State ==
const state = { q: '', from: MIN, to: MAX, sort: 'title-asc', view: 'table' };
let meta = {}, records = [], shown = [], terms = [], PSEUDO = new Set(), facetOpts = {};
const byId = Object.create(null), open = new Set();
let langExpanded = false, hasFiles = false, ready = false;
let decadeScale = 1, lastCounts = new Array(NBINS).fill(0), wordsSorted = [], totalWords = 0;

const nf = new Intl.NumberFormat('en');
const $ = id => document.getElementById(id);
// "q-clear" becomes els.qClear; "tl-plot" becomes TL.plot.
function grab(ids, prefix) {
	const o = {};
	ids.split(' ').forEach(id => { o[id.replace(prefix, '').replace(/-(\w)/g, (_, c) => c.toUpperCase())] = $(id); });
	return o;
}
const els = grab('q q-clear search-row catalogue live notice chips sort results tbody view-table view-cards state ' +
	'view-table-btn view-cards-btn facets facet-list facets-slot clear-facets filter-toggle filter-badge ' +
	'filters-dialog sheet-body sheet-close sheet-clear sheet-done cite-copy cite-text', '');
const TL = grab('tl-state tl-clear y-from y-to tl-plot tl-band tl-bars tl-h0 tl-h1 tl-hover tl-axis tl-note', 'tl-');
TL.presets = Array.from(document.querySelectorAll('.tl-presets button'));
const SORTS = Array.from(els.sort.options, o => o.value);
const narrowMQ = matchMedia('(max-width: 799px)'), wideMQ = matchMedia('(min-width: 1280px)');

const ICON = Object.fromEntries(['chev', 'ext', 'down', 'x'].map(n =>
	[n, `<svg class="ico${n === 'chev' ? ' chev' : ''}" aria-hidden="true"><use href="#i-${n}"/></svg>`]));
const NEW_TAB = '<span class="sr-only"> (opens in a new tab)</span>';
const NOT_RECORDED = '<span class="q">Not recorded</span>';
const DASH = '<span class="dash" aria-hidden="true">—</span><span class="sr-only">not recorded</span>';

// == Helpers ==
const ENT = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => (s == null ? '' : String(s).replace(/[&<>"']/g, c => ENT[c]));
// Only web links reach an href.
const safeURL = u => (/^https?:\/\//i.test(String(u || '')) ? String(u) : '#');
const fold = s => String(s || '').normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
	.replace(/[^\p{L}\p{N}\s]/gu, '').replace(/\s+/g, ' ').trim();
const fmt = n => nf.format(n);
const plural = (n, one, many) => fmt(n) + ' ' + (n === 1 ? one : many || one + 's');
const hasNum = v => typeof v === 'number' && isFinite(v);
const has = (o, k) => Object.hasOwn(o, k);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const frac = y => clamp((y - MIN) / SPAN, 0, 1);
const encLabel = v => (has(ENC, v) ? ENC[v][0] : v || '');
const statusLabel = v => (has(STATUS, v) ? STATUS[v][0] : v || '');
const periodActive = () => state.from !== MIN || state.to !== MAX;
const yearsLabel = (a, b) => (a === b ? String(a) : a + '–' + b);
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const on = (el, type, fn) => el.addEventListener(type, fn);
const setExp = (el, v) => el.setAttribute('aria-expanded', String(v));
function debounce(fn, ms) {
	let t = 0;
	const d = (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
	d.cancel = () => clearTimeout(t);
	return d;
}
const sub = e => (e.institution ? `<span class="sub">${esc(e.institution)}</span>` : '');
const tog = (r, attrs) => `<button type="button" class="tog"${attrs} aria-expanded="false">${ICON.chev}<span class="ti">${esc(r.e.title)}</span></button>${sub(r.e)}`;
const filesLink = (r, inner, cls) => extLink(r.e.data_url, inner, `${cls} aria-label="${esc(filesLinkLabel(r))}"`);
const extLink = (url, inner, attrs = '') => `<a href="${esc(safeURL(url))}" target="_blank" rel="noopener"${attrs}>${inner}</a>`;
const countryName = code => { const c = (meta.countries || {})[code]; return c ? c.name : code; };
const filesNoun = f => ({ tei: 'TEI XML files', xml: 'XML files', json: 'JSON files', 'plain-text': 'text files' })[f] || 'files';
const dataFormats = e => e.data_formats || [e.data_format];
const formatsLabel = e => dataFormats(e).map(encLabel).join(' / ');
const downloadNoun = e => dataFormats(e).length > 1 ? formatsLabel(e) + ' files' : filesNoun(e.data_format);
const filesLinkLabel = r => `Download the ${downloadNoun(r.e)} of ${r.e.title} (opens in a new tab)`;
const anyFilter = () => LIST_KEYS.some(k => state[k].length) || periodActive();
// A search of punctuation only folds to no term and narrows nothing.
const narrowed = () => terms.length > 0 || anyFilter();
const facetFilterCount = () => LIST_KEYS.reduce((n, k) => n + state[k].length, 0);
const effectiveView = () => (narrowMQ.matches ? 'table' : state.view);
function setQ(v) { state.q = els.q.value = v; els.qClear.hidden = !v; }

// == Loading ==
function load() {
	fetch('data.json', { cache: 'no-cache' })
		.then(res => { if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); })
		.then(init)
		.catch(err => {
			if (ready) { console.error(err); return; }
			$('main').classList.add('load-failed');
			els.results.removeAttribute('aria-busy');
			els.catalogue.textContent = 'The catalogue could not be loaded';
			els.viewTable.hidden = els.viewCards.hidden = true;
			els.state.innerHTML = `<div class="state"><p class="state-text">The catalogue data could not be loaded (${esc(err.message)}). ` +
				'Try reloading the page. The full catalogue is also available as <a href="renascor.csv">renascor.csv</a> and ' +
				`<a href="renascor.json">renascor.json</a>, or as one JSON file per edition on <a href="${REPO}/tree/main/data/entries">GitHub</a>.</p></div>`;
		});
}

function init(data) {
	meta = data.meta || {};
	const stats = meta.stats || {}, derived = data.derived || [];
	PSEUDO = new Set(stats.pseudo_languages || []);
	records = (data.entries || []).map((e, i) => buildRecord(e, derived[i] || {}, i));
	records.forEach(r => { byId[r.id] = r; });
	hasFiles = records.some(r => r.e.data_url);
	decadeScale = Math.max(1, ...(meta.timeline && meta.timeline.decade_words || []));
	wordsSorted = records.map(r => r.e.words).filter(hasNum).sort((a, b) => a - b);
	totalWords = wordsSorted.reduce((a, b) => a + b, 0);
	readURL();
	buildFacets();
	buildTimeline();
	wireEvents();
	ready = true;
	els.results.removeAttribute('aria-busy');
	render();
	announce.cancel();   // loading is not a change
	updateStickyH();
	if (location.hash.length > 1) openFromHash();
}

function buildRecord(e, d, i) {
	const id = d.id || 'entry-' + i;
	const labels = Array.isArray(e.languages) ? e.languages : [];
	const real = labels.filter(l => !PSEUDO.has(l));
	const C = meta.countries || {};
	const codes = Array.isArray(e.countries) ? e.countries : [];
	const areas = [];
	codes.forEach(c => { const a = C[c] && C[c].area; if (a && !areas.includes(a)) areas.push(a); });
	const countryNames = codes.map(countryName);
	const r = {
		id, e, d, labels, real: real.length ? real : labels.slice(), countries: codes, countryNames, areas,
		p: d.period && hasNum(d.period.start) && hasNum(d.period.end) ? d.period : null,
		fileKeys: e.data_url ? dataFormats(e).map(f => has(ENC, f) ? f : 'other') : ['none']
	};
	r.hay = fold([e.title, e.institution, labels.join(' '), d.notes_display, e.region, countryNames.join(' '), areas.join(' '),
		e.author, e.date, e.doi, d.period && d.period.label, e.period, encLabel(e.encoding), e.encoding,
		e.data_url ? formatsLabel(e) : '', e.license, e.license_note, statusLabel(e.status), d.host, d.url_display, d.data_display, id
	].filter(Boolean).join(' '));
	return r;
}

// == Filters panel ==
const optHTML = (key, value, label) => `<li><label class="opt"><input type="checkbox" data-facet="${key}" value="${esc(value)}">` +
	`<span class="name">${label}</span><span class="n"></span></label></li>`;
const optList = (key, values, label) => '<ul class="opts">' + values.map(v => optHTML(key, v, label(v))).join('') + '</ul>';
const facetHTML = (key, title, body, note) => `<div class="facet" id="facet-${key}" role="group" aria-labelledby="fh-${key}">` +
	`<div class="facet-h"><h3 id="fh-${key}">${title}</h3><span class="facet-v" id="fv-${key}"></span>` +
	`<button type="button" class="linkbtn" data-clear-facet="${key}" hidden>Clear<span class="sr-only"> ${title}</span></button></div>` +
	body + (note ? `<p class="facet-note">${note}</p>` : '') + '</div>';

function buildFacets() {
	const stats = meta.stats || {};
	const labels = (stats.language_counts || []).map(x => x[0]);
	const pseudo = labels.filter(l => PSEUDO.has(l)), realLabels = labels.filter(l => !PSEUDO.has(l));
	const present = (key, f) => records.some(r => f(r) === key);
	let html = facetHTML('lang', 'Language',
		'<input type="search" class="lang-find" id="lang-find" placeholder="Find a language" aria-label="Find a language" autocomplete="off" spellcheck="false" hidden>' +
		'<div class="lang-list" id="lang-list">' + optList('lang', realLabels, esc) +
		(pseudo.length ? '<h4 class="opts-h" id="lang-other-h" hidden>Other labels</h4>' + optList('lang', pseudo, esc) : '') + '</div>' +
		'<button type="button" class="linkbtn more-btn" id="lang-more" aria-expanded="false" aria-controls="lang-list" data-n="' +
		(hasNum(stats.languages) ? stats.languages : realLabels.length) + '"></button>');
	html += facetHTML('encoding', 'Encoding', optList('encoding', ENC_ORDER.filter(k => present(k, r => r.e.encoding)), k => ENC[k][0]));
	html += facetHTML('status', 'Status', optList('status', STATUS_ORDER, k => `<span class="st ${k}">${STATUS[k][0]}</span>`));
	html += facetHTML('size', 'Size', optList('size', SIZES.map(s => s[0]).filter(k => present(k, r => r.d.size_band || 'none')), k => SIZE_LABEL[k]));
	if (hasFiles) {
		html += facetHTML('files', 'Files', optList('files', ENC_ORDER.concat('none').filter(k => records.some(r => r.fileKeys.includes(k))), k => FILE_LABEL[k]),
			'The format of the files that can be downloaded for each edition: repository, download page or dataset record.');
	}
	if (meta.countries && records.some(r => r.countries.length)) {
		const C = meta.countries, n = {};
		records.forEach(r => r.areas.concat(r.countries).forEach(v => { n[v] = (n[v] || 0) + 1; }));
		const without = records.filter(r => !r.countries.length).length;
		html += facetHTML('area', 'Area', '<ul class="opts opts-area">' + (meta.areas || []).filter(a => n[a]).map((a, i) => {
			const cs = Object.keys(C).filter(c => n[c] && C[c].area === a).sort((x, y) => n[y] - n[x] || cmp(countryName(x), countryName(y)));
			return `<li class="area-item"><label class="opt"><input type="checkbox" data-facet="area" value="${esc(a)}"><span class="name">${esc(a)}</span>` +
				`<span class="n"></span></label><button type="button" class="linkbtn area-more" aria-expanded="false" aria-controls="ac-${i}">` +
				`Show countries<span class="sr-only">: ${esc(a)}</span></button><ul class="opts opts-c" id="ac-${i}" hidden>` +
				cs.map(c => optHTML('country', c, esc(countryName(c)))).join('') + '</ul></li>';
		}).join('') + '</ul>', 'Areas group the present-day countries where the documents were written or printed.' +
			(without ? ` ${plural(without, 'edition')} ${without === 1 ? 'has' : 'have'} no country recorded.` : ''));
	}
	els.facetList.innerHTML = html;
	facetOpts = {};
	els.facetList.querySelectorAll('input[data-facet]').forEach(input => {
		const key = input.dataset.facet, label = input.closest('.opt');
		(facetOpts[key] = facetOpts[key] || []).push({
			value: input.value, input, label, n: label.querySelector('.n'), li: input.closest('li'),
			folded: fold(label.textContent), pseudo: key === 'lang' && PSEUDO.has(input.value)
		});
	});
}

// Disjunctive counts: a facet ignores its own selection.
function updateFacets() {
	Object.keys(facetOpts).forEach(key => {
		const c = Object.create(null), skip = key === 'country' ? 'area' : key;
		records.forEach(r => { if (matches(r, skip)) FACET_VALUES[key](r).forEach(v => { c[v] = (c[v] || 0) + 1; }); });
		facetOpts[key].forEach(o => {
			const n = c[o.value] || 0, checked = state[key].includes(o.value);
			o.n.textContent = fmt(n);
			o.input.checked = checked;
			o.input.disabled = !n && !checked;
			o.label.classList.toggle('zero', o.input.disabled);
		});
	});
	LIST_KEYS.slice(0, 6).forEach(key => {
		const v = $('fv-' + key);
		if (!v) return;
		const n = state[key].length + (key === 'area' ? state.country.length : 0);
		v.textContent = n ? n + ' selected' : '';
		els.facetList.querySelector(`[data-clear-facet="${key}"]`).hidden = !n;
	});
	// Countries stay shown while one is selected.
	els.facetList.querySelectorAll('.area-more').forEach(btn => {
		if ($(btn.getAttribute('aria-controls')).querySelector('input:checked')) showCountries(btn, true);
	});
	els.clearFacets.hidden = !facetFilterCount();
	updateLangVisibility();
}

function showCountries(btn, exp) {
	setExp(btn, exp);
	$(btn.getAttribute('aria-controls')).hidden = !exp;
}

function updateLangVisibility() {
	const find = $('lang-find'), more = $('lang-more'), other = $('lang-other-h'), q = fold(find.value);
	let rank = 0, pseudoShown = 0;
	(facetOpts.lang || []).forEach(o => {
		const visible = langExpanded ? !q || o.folded.includes(q) : (!o.pseudo && rank < LANG_TOP) || state.lang.includes(o.value);
		if (!o.pseudo) rank++;
		o.li.hidden = !visible;
		if (o.pseudo && visible) pseudoShown++;
	});
	if (other) other.hidden = !pseudoShown;
	find.hidden = !langExpanded;
	$('lang-list').classList.toggle('scroll', langExpanded);
	setExp(more, langExpanded);
	more.textContent = langExpanded ? 'Show fewer languages' : 'Show all ' + plural(+more.dataset.n, 'language');
}

// == Period timeline ==
function buildTimeline() {
	TL.bars.innerHTML = '<span></span>'.repeat(NBINS);
	TL.barEls = Array.from(TL.bars.children);
	let ax = '';
	for (let i = 0; i <= NBINS; i++) ax += `<i${i % 5 ? '' : ' class="major"'} style="left:${(i / NBINS * 100).toFixed(2)}%"></i>`;
	for (let y = MIN; y <= MAX; y += 50) {
		ax += `<span${y === MIN ? ' class="first"' : y === MAX ? ' class="last"' : ''} style="left:${(frac(y) * 100).toFixed(2)}%">${y}</span>`;
	}
	TL.axis.innerHTML = ax;
}

let tlShown = null, yearsApplying = false;
function renderTimeline() {
	// A range set elsewhere replaces what was typed in the year fields.
	if (!yearsApplying && tlShown && (tlShown[0] !== state.from || tlShown[1] !== state.to)) {
		applyYearsSoon.cancel();
		delete TL.yFrom.dataset.dirty;
		delete TL.yTo.dataset.dirty;
	}
	tlShown = [state.from, state.to];
	const counts = new Array(NBINS).fill(0);
	let undated = 0, missing = false, known = false;
	records.forEach(r => {
		if (!matches(r, 'period')) return;
		const p = r.d.period_words;
		if (!p) { missing = true; return; }
		known = true;
		p.decades.forEach((words, i) => { counts[i] += words; });
		undated += p.undated;
	});
	lastCounts = known ? counts : null;
	const active = periodActive(), inRange = i => active && DECADES[i] <= state.to && binEnd(i) >= state.from;
	TL.barEls.forEach((b, i) => {
		b.style.height = counts[i] ? `max(2px, ${(Math.min(counts[i], decadeScale) / decadeScale * 100).toFixed(2)}%)` : '0px';
		b.classList.toggle('in', inRange(i));
	});
	TL.bars.setAttribute('aria-label', known ? 'Corpus words per decade: ' + counts.map((n, i) =>
		DECADES[i] + '–' + binEnd(i) + ': ' + plural(n, 'word')).join('; ') : 'Word counts not recorded for these collections.');
	const l = frac(state.from) * 100, r = frac(state.to + 1) * 100;
	TL.band.hidden = !active;
	TL.band.style.cssText = `left:${l.toFixed(3)}%;width:${Math.max(0, r - l).toFixed(3)}%`;
	setHandle(TL.h0, l, state.from);
	setHandle(TL.h1, r, state.to);
	TL.state.innerHTML = active ? `<b>${yearsLabel(state.from, state.to)}</b>` : 'All years';
	TL.clear.hidden = !active;
	if (!TL.yFrom.dataset.dirty) TL.yFrom.value = state.from;
	if (!TL.yTo.dataset.dirty) TL.yTo.value = state.to;
	TL.presets.forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.from === state.from && +b.dataset.to === state.to)));
	TL.note.hidden = false;
	const note = known ? ['Deduplicated corpus words (June 2026); dates include estimates.'] : ['No dated corpus word counts recorded for these collections.'];
	if (undated) note.push(`${plural(undated, 'undated word')} omitted.`);
	if (missing && known) note.push('Collections without dated corpus counts are omitted.');
	TL.note.textContent = note.join(' ');
}

function setHandle(h, left, year) {
	h.style.left = left.toFixed(3) + '%';
	h.setAttribute('aria-valuenow', year);
	h.setAttribute('aria-valuetext', year);
	h.firstElementChild.textContent = year;
}

function setPeriod(from, to) {
	from = clamp(Math.round(from), MIN, MAX);
	to = clamp(Math.round(to), MIN, MAX);
	if (from > to) [from, to] = [to, from];
	if (from === state.from && to === state.to) return;
	state.from = from;
	state.to = to;
	render();
}

function selectDecade(i, extend) {
	const y0 = DECADES[i], y1 = binEnd(i);
	if (extend && periodActive()) setPeriod(Math.min(state.from, y0), Math.max(state.to, y1));
	else if (state.from === y0 && state.to === y1) setPeriod(MIN, MAX);
	else setPeriod(y0, y1);
}

// Pointer events: one code path for mouse, pen and touch.
let drag = null, dragRaf = 0;
function plotFrac(clientX) {
	const b = TL.plot.getBoundingClientRect();
	return b.width ? clamp((clientX - b.left) / b.width, 0, 1) : 0;
}
// The band runs from the start of the first year to the end of the last.
const yearStartAt = f => clamp(Math.round(MIN + f * SPAN), MIN, MAX);
const yearEndAt = f => { const y = Math.round(MIN + f * SPAN); return y >= MAX ? MAX : clamp(y - 1, MIN, MAX); };
// Half the width of a handle's hit area (see the CSS).
const handleReach = h => h.offsetWidth / 2 - (parseFloat(getComputedStyle(h, '::before').left) || 0);
const focusHandle = mode => (mode === 'start' ? TL.h0 : TL.h1).focus({ preventScroll: true });

function onPlotDown(ev) {
	if (drag || (ev.pointerType === 'mouse' && ev.button !== 0)) return;
	const onHandle = ev.target.closest('.tl-handle');
	const W = TL.plot.getBoundingClientRect().width, f = plotFrac(ev.clientX);
	const l = frac(state.from), r = frac(state.to + 1);
	const x = f * W, xl = l * W, xr = r * W, band = xr - xl;
	let mode = 'new';
	if (onHandle) {
		// Hit areas overlap around a narrow band: take the nearer handle, the band in its middle
		// third, and for handles at one spot let the drag direction decide.
		const d0 = Math.abs(x - xl), d1 = Math.abs(x - xr);
		if (band < 8) mode = 'pick';
		else if (x > xl && x < xr && Math.min(d0, d1) > band / 3) mode = 'move';
		else mode = d0 <= d1 ? 'start' : 'end';
	} else if (periodActive() && f >= l && f <= r) mode = 'move';
	drag = {
		mode, id: ev.pointerId, x0: ev.clientX, f0: f, f, l, r, from0: state.from, to0: state.to, moved: false, shift: ev.shiftKey,
		off: mode === 'start' ? f - l : mode === 'end' ? f - r : 0,
		// A click on a handle selects the bar beneath only where handles cover the bars.
		barClick: !onHandle || !periodActive() || band < 2 * handleReach(onHandle)
	};
	if (mode === 'start' || mode === 'end') focusHandle(mode);
	if (onHandle || ev.pointerType !== 'touch') ev.preventDefault();
	try { TL.plot.setPointerCapture(ev.pointerId); } catch { /* optional */ }
	hideHover();
}

function onPlotMove(ev) {
	if (!drag) { if (ev.pointerType !== 'touch') showHover(ev); return; }
	if (ev.pointerId !== drag.id) return;
	if (!drag.moved) {
		if (Math.abs(ev.clientX - drag.x0) < 4) return;
		drag.moved = true;
		TL.plot.classList.add('dragging');
		els.results.style.minHeight = els.results.offsetHeight + 'px';
	}
	drag.f = plotFrac(ev.clientX);
	if (!dragRaf) dragRaf = requestAnimationFrame(applyDrag);
}

function applyDrag() {
	dragRaf = 0;
	const d = drag;
	if (!d || !d.moved) return;
	const f = d.f;
	if (d.mode === 'pick') {
		d.mode = f < d.f0 ? 'start' : 'end';
		d.off = d.f0 - (d.mode === 'start' ? d.l : d.r);
		focusHandle(d.mode);
	}
	let from = state.from, to = state.to;
	if (d.mode === 'new') {
		from = yearStartAt(Math.min(d.f0, f));
		to = Math.max(from, yearEndAt(Math.max(d.f0, f)));
	} else if (d.mode === 'start') {
		from = Math.min(yearStartAt(clamp(f - d.off, 0, 1)), state.to);
	} else if (d.mode === 'end') {
		to = Math.max(yearEndAt(clamp(f - d.off, 0, 1)), state.from);
	} else {
		const w = d.to0 - d.from0;
		from = clamp(d.from0 + Math.round((f - d.f0) * SPAN), MIN, MAX - w);
		to = from + w;
	}
	if (from !== state.from || to !== state.to) {
		state.from = from;
		state.to = to;
		render();
	}
}

function onPlotUp(ev) {
	if (!drag || ev.pointerId !== drag.id) return;
	const d = drag;
	if (d.moved) {
		d.f = plotFrac(ev.clientX);
		applyDrag();
	}
	endDrag();
	if (!d.moved && d.barClick) selectDecade(Math.min(NBINS - 1, Math.floor(d.f0 * NBINS)), d.shift);
}

function endDrag() {
	if (!drag) return;
	const id = drag.id, moved = drag.moved;
	drag = null;
	if (dragRaf) { cancelAnimationFrame(dragRaf); dragRaf = 0; }
	TL.plot.classList.remove('dragging');
	els.results.style.minHeight = '';
	try { if (TL.plot.hasPointerCapture(id)) TL.plot.releasePointerCapture(id); } catch { /* already released */ }
	if (moved) writeURL(true);
}

function showHover(ev) {
	if (ev.target.closest('.tl-handle')) { hideHover(); return; }
	const i = Math.min(NBINS - 1, Math.floor(plotFrac(ev.clientX) * NBINS));
	TL.hover.textContent = DECADES[i] + '–' + binEnd(i) + ' · ' + (lastCounts ? plural(lastCounts[i], 'word') : 'word count not recorded');
	TL.hover.hidden = false;
	const W = TL.plot.clientWidth, w = TL.hover.offsetWidth;
	TL.hover.style.left = clamp((i + 0.5) / NBINS * W - w / 2, -8, Math.max(-8, W - w + 8)).toFixed(1) + 'px';
}
const hideHover = () => { TL.hover.hidden = true; };

function onHandleKey(ev) {
	const isStart = ev.currentTarget === TL.h0, step = ev.shiftKey ? 10 : 1;
	let v = isStart ? state.from : state.to;
	switch (ev.key) {
		case 'ArrowLeft': case 'ArrowDown': v -= step; break;
		case 'ArrowRight': case 'ArrowUp': v += step; break;
		case 'PageDown': v -= 10; break;
		case 'PageUp': v += 10; break;
		case 'Home': v = isStart ? MIN : state.from; break;
		case 'End': v = isStart ? state.to : MAX; break;
		default: return;
	}
	ev.preventDefault();
	if (isStart) setPeriod(clamp(v, MIN, state.to), state.to);
	else setPeriod(state.from, clamp(v, state.from, MAX));
}

// Year fields apply at four digits (after a pause), on Enter, change and blur.
function applyYears(strict) {
	const fa = !!TL.yFrom.dataset.dirty, fb = !!TL.yTo.dataset.dirty;
	const a = TL.yFrom.value.trim(), b = TL.yTo.value.trim();
	const va = fa && /^\d{4}$/.test(a) ? +a : null, vb = fb && /^\d{4}$/.test(b) ? +b : null;
	if (!strict && ((fa && a !== '' && va === null) || (fb && b !== '' && vb === null))) return;
	let from = clamp(va === null ? state.from : va, MIN, MAX), to = clamp(vb === null ? state.to : vb, MIN, MAX);
	if (from > to) [from, to] = [to, from];
	if (strict) {
		delete TL.yFrom.dataset.dirty;
		delete TL.yTo.dataset.dirty;
		TL.yFrom.value = from;
		TL.yTo.value = to;
	}
	yearsApplying = true;
	setPeriod(from, to);
	yearsApplying = false;
}
const applyYearsSoon = debounce(() => applyYears(false), 400);

// == Filtering and sorting ==
function matches(r, skip) {
	if (skip !== 'q') for (const t of terms) if (!r.hay.includes(t)) return false;
	const e = r.e, S = state;
	if (skip !== 'lang' && S.lang.length && !r.labels.some(l => S.lang.includes(l))) return false;
	if (skip !== 'encoding' && S.encoding.length && !S.encoding.includes(e.encoding)) return false;
	if (skip !== 'status' && S.status.length && !S.status.includes(e.status)) return false;
	if (skip !== 'size' && S.size.length && !S.size.includes(r.d.size_band || 'none')) return false;
	if (skip !== 'files' && S.files.length && !S.files.some(f => r.fileKeys.includes(f))) return false;
	if (skip !== 'area' && (S.area.length || S.country.length) &&
		!r.areas.some(a => S.area.includes(a)) && !r.countries.some(c => S.country.includes(c))) return false;
	if (skip !== 'period' && periodActive() && (!r.p || r.p.start > S.to || r.p.end < S.from)) return false;
	return true;
}

const byTitle = (a, b) => cmp(a.d.sort_title || '', b.d.sort_title || '') || cmp(a.id, b.id);
function rankOf(r, key) {
	const i = key === 'encoding' ? ENC_ORDER.indexOf(r.e.encoding) : STATUS_ORDER.indexOf(r.e.status);
	return i < 0 ? null : i;
}
// Missing values last in both directions; ties by title.
function compare(a, b) {
	const [key, d] = state.sort.split('-'), dir = d === 'desc' ? -1 : 1;
	if (key === 'title') return dir * cmp(a.d.sort_title || '', b.d.sort_title || '') || cmp(a.id, b.id);
	let va, vb;
	if (key === 'words' || key === 'texts') {
		va = hasNum(a.e[key]) ? a.e[key] : null;
		vb = hasNum(b.e[key]) ? b.e[key] : null;
	} else if (key === 'period') {
		va = a.p; vb = b.p;
	} else {
		va = rankOf(a, key); vb = rankOf(b, key);
	}
	if (va === null || vb === null) return va === vb ? byTitle(a, b) : va === null ? 1 : -1;
	const c = key !== 'period' ? dir * (va - vb) : dir > 0 ? va.start - vb.start || va.end - vb.end : vb.end - va.end || vb.start - va.start;
	return c || byTitle(a, b);
}

// == Cells, rows, cards and records ==
function langSummary(r) {
	const real = r.real, sel = state.lang;
	const matched = real.filter(l => sel.includes(l));
	if (real.length <= 3) return esc(matched.concat(real.filter(l => !sel.includes(l))).join(', '));
	if (!matched.length) return esc(real.length + ' languages');
	const top = matched.slice(0, 2);
	return `${esc(top.join(', '))} <span class="more-n">+ ${real.length - top.length} more</span>`;
}

const numericPeriod = p => p.kind === 'range' || p.kind === 'year';
function periodCell(r) {
	const p = r.d.period;
	if (!p) return DASH;
	return (numericPeriod(p) ? `<span class="nw">${esc(p.label)}</span>` : esc(p.label)) + coverageBar(r.p);
}

const cut = p => (p.start < MIN ? ' cut-l' : '') + (p.end > MAX ? ' cut-r' : '');
const spanStyle = p => { const l = frac(p.start) * 100; return `left:${l.toFixed(2)}%;width:${Math.max(0, frac(p.end + 1) * 100 - l).toFixed(2)}%`; };
const inScope = p => p && p.end >= MIN && p.start <= MAX;
const coverageBar = p => (inScope(p) ? `<span class="span${cut(p)}" aria-hidden="true"><i style="${spanStyle(p)}"></i></span>` : '');

const numCell = v => (hasNum(v) ? fmt(v) : DASH);
const statusHTML = s => `<span class="st ${esc(s)}">${esc(statusLabel(s))}</span>`;

function mobileMeta(r) {
	const e = r.e, p = r.d.period;
	const line1 = [[langSummary(r), r.real.length > 1]];
	if (p) line1.push([esc(p.label), p.kind === 'century' || p.kind === 'text']);
	line1.push([esc(encLabel(e.encoding))]);
	line1.push([licenseHTML(e)]);
	if (e.data_url) line1.push([filesLink(r, 'files' + ICON.ext, ' class="files"')]);
	const line2 = [[hasNum(e.words) ? plural(e.words, 'word') : 'No word count']];
	if (hasNum(e.texts)) line2.push([plural(e.texts, 'text')]);
	line2.push([statusHTML(e.status)]);
	const join = parts => '<span class="line">' + parts.map(x => `<span class="part${x[1] ? ' free' : ''}">${x[0]}</span>`)
		.join(' <span class="sep" aria-hidden="true">·</span> ') + '</span>';
	return join(line1) + join(line2);
}

function rowFor(r) {
	if (r.tr) return r.tr;
	const e = r.e, tr = document.createElement('tr');
	tr.className = 'row';
	tr.dataset.id = r.id;
	tr.innerHTML = `<th scope="row" class="c-title">${tog(r, ` aria-controls="rec-${esc(r.id)}"`)}<span class="m-meta"></span></th><td class="c-lang"></td>` +
		`<td class="c-period">${periodCell(r)}</td><td class="c-words num">${numCell(e.words)}</td><td class="c-texts num">${numCell(e.texts)}</td>` +
		`<td class="c-enc">${esc(encLabel(e.encoding))}${e.data_url ? filesLink(r, ICON.down, ' class="dl"') : ''}</td>` +
		`<td class="c-status">${statusHTML(e.status)}</td>` +
		`<td class="c-link">${extLink(e.url, ICON.ext, ` class="ext" aria-label="${esc((r.d.archived_copy ? 'Open the archived copy of ' : 'Open the edition ') + e.title)} (opens in a new tab)"`)}</td>`;
	r.tr = tr;
	r.trLang = tr.querySelector('.c-lang');
	r.trMeta = tr.querySelector('.m-meta');
	r.langKey = null;
	return tr;
}

function recRowFor(r) {
	if (!r.rec) {
		r.rec = document.createElement('tr');
		r.rec.className = 'rec';
		r.rec.innerHTML = `<td colspan="8">${recordHTML(r)}</td>`;
	}
	return r.rec;
}

function cardFor(r) {
	if (r.card) return r.card;
	const e = r.e, d = r.d, p = d.period, el = document.createElement('article');
	el.className = 'card';
	el.dataset.id = r.id;
	el.setAttribute('aria-labelledby', 'ct-' + r.id);
	const size = hasNum(e.words) ? plural(e.words, 'word') + (hasNum(e.texts) ? ' · ' + plural(e.texts, 'text') : '')
		: hasNum(e.texts) ? 'No word count · ' + plural(e.texts, 'text') : NOT_RECORDED;
	const visit = d.archived_copy ? ['Archived copy', 'Visit the archived copy: '] : ['Visit', 'Visit the edition: '];
	el.innerHTML = tog(r, ` id="ct-${esc(r.id)}" aria-controls="cpanel-${esc(r.id)}"`) + `<dl class="card-dl"><dt>Languages</dt><dd class="c-langs"></dd><dt>Period</dt><dd>${p ? esc(p.label) + coverageBar(r.p) : NOT_RECORDED}</dd>` +
		`<dt>Size</dt><dd>${size}</dd><dt>Encoding</dt><dd>${esc(encLabel(e.encoding))}</dd>` +
		`<dt>Licence</dt><dd>${licenseHTML(e)}</dd>` +
		(e.doi ? `<dt>DOI</dt><dd>${extLink('https://doi.org/' + e.doi, esc(e.doi))}</dd>` : '') +
		(e.data_url ? `<dt>Files</dt><dd>${filesLink(r, ICON.down + esc(formatsLabel(e)), '')}</dd>` : '') +
		(e.api_url ? `<dt>API</dt><dd>${extLink(e.api_url, 'API documentation')}</dd>` : '') +
		`</dl><div class="card-foot">${statusHTML(e.status)}<span class="host">${esc(d.host || '')}</span>` +
		extLink(e.url, visit[0] + ICON.ext, ` class="visit" aria-label="${esc(visit[1] + e.title)} (opens in a new tab)"`) + '</div>';
	r.card = el;
	r.cardLang = el.querySelector('.c-langs');
	r.langKey = null;
	return el;
}

function panelFor(r) {
	if (r.panel) return r.panel;
	const el = document.createElement('section');
	el.className = 'card-panel';
	el.id = 'cpanel-' + r.id;
	el.dataset.id = r.id;
	el.innerHTML = `<div class="panel-head"><p class="panel-title">${esc(r.e.title)}</p>${sub(r.e)}` +
		`<button type="button" class="panel-close" data-id="${esc(r.id)}" aria-label="Close the record: ${esc(r.e.title)}">${ICON.x}</button></div>` +
		recordHTML(r);
	return (r.panel = el);
}

function yearsActive(ya) {
	if (ya.end === 'ongoing') return `Since ${ya.start} (ongoing)`;
	if (hasNum(ya.end)) return yearsLabel(ya.start, ya.end);
	return 'Started ' + ya.start;
}

// ticks: [value, label, minor]; end labels align inwards.
function stripAxis(ticks, pos) {
	return '<div class="strip-axis" aria-hidden="true">' + ticks.map(t => {
		const x = pos(t[0]), cls = ((x <= 1 ? 'first' : x >= 99 ? 'last' : '') + (t[2] ? ' minor' : '')).trim();
		return `<span${cls ? ` class="${cls}"` : ''} style="left:${x.toFixed(2)}%">${t[1]}</span>`;
	}).join('') + '</div>';
}
const strip = (inner, axis) => `<div class="ctx"><div class="strip" aria-hidden="true"><span class="axis"></span>${inner}</div>${axis}</div>`;

const periodStrip = p => strip(inScope(p) ? `<span class="bar${cut(p)}" style="${spanStyle(p)}"></span>` : '',
	stripAxis([1450, 1500, 1550, 1600, 1650, 1700].map(y => [y, y, y > MIN && y < MAX]), y => frac(y) * 100));

function sizeStrip(words) {
	const max = wordsSorted[wordsSorted.length - 1] || 1e9;
	const L0 = 2, L1 = Math.max(L0 + 1, Math.ceil(Math.log10(Math.max(max, 1)) * 2) / 2);
	const pos = w => clamp((Math.log10(Math.max(w, 100)) - L0) / (L1 - L0), 0, 1) * 100;
	let ticks = '', last = -1;
	wordsSorted.forEach(w => { const x = pos(w).toFixed(2); if (x !== last) { ticks += `<span class="tick" style="left:${x}%"></span>`; last = x; } });
	return strip(ticks + `<span class="me" style="left:${pos(words).toFixed(2)}%"></span>`,
		stripAxis([[100, '100'], [1e4, '10,000', 1], [1e6, '1 million'], [1e8, '100 million', 1]].filter(t => Math.log10(t[0]) <= L1), pos));
}

function rankSentence(words) {
	const n = wordsSorted.length;
	let s;
	if (words >= wordsSorted[n - 1]) s = 'The largest edition in the catalogue';
	else if (words <= wordsSorted[0]) s = 'The smallest edition in the catalogue';
	else {
		let below = 0;
		while (below < n && wordsSorted[below] < words) below++;
		s = `Larger than ${Math.round(below / (n - 1) * 100)}% of the ${plural(n, 'edition')} with a word count`;
	}
	const share = totalWords ? words / totalWords * 100 : 0;
	if (share >= 10) s += ` · ${Math.round(share)}% of recorded collection words`;
	else if (share >= 1) s += ` · ${(Math.round(share * 10) / 10).toFixed(1)}% of recorded collection words`;
	return s;
}

function languagesFull(r) {
	const pseudo = r.labels.filter(l => PSEUDO.has(l)), real = r.labels.filter(l => !PSEUDO.has(l));
	if (!real.length) return esc(r.labels.join(', '));
	if (!pseudo.length) return esc(real.join(', '));
	const q = pseudo.map(l => '“' + l + '”');
	return `${esc(real.join(', '))} <span class="q">— also labelled ${esc(q.length > 1 ? q.slice(0, -1).join(', ') + ' and ' + q[q.length - 1] : q[0])}</span>`;
}

function periodFull(r) {
	const p = r.d.period;
	if (!p) return 'Not recorded';
	const lines = [];
	if (p.note || p.kind === 'century') lines.push(`As recorded: “${esc(p.raw)}”`);
	if (p.kind === 'century') lines.push(`Counted as ${p.start}–${p.end} by the period filter.`);
	if (p.kind === 'text') lines.push('Given in words, so not matched by the period filter.');
	if (p.beyond_scope) lines.push('Extends beyond the catalogue’s 1450–1700 range.');
	return (numericPeriod(p) ? `<span class="nw">${esc(p.label)}</span>` : esc(p.label)) +
		lines.map(l => `<span class="line">${l}</span>`).join('') + (r.p ? periodStrip(r.p) : '');
}

function sizeFull(r) {
	const w = r.e.words, t = r.e.texts;
	if (!hasNum(w)) return hasNum(t) ? plural(t, 'text') + '; no word count' : 'Not recorded';
	return plural(w, 'word') + (hasNum(t) ? ' in ' + plural(t, 'text') : '') + sizeStrip(w) + `<span class="line">${esc(rankSentence(w))}</span>`;
}

function figuresText(r) {
	const d = r.d;
	if (r.e.resource_statistics) {
		const s = r.e.resource_statistics;
		return esc(s.note) + ' ' + extLink(s.url, 'Count audit') + muted('· ' + esc(s.date));
	}
	if (d.figures === 'other') return 'Recorded from another source; not counted in the corpus snapshot.';
	if (d.figures !== 'rq') return 'No word or text count recorded.';
	const snap = (meta.snapshots || {})[d.snapshot];
	const month = (snap && snap.month) || (meta.display && meta.display.snapshot_month) || '';
	if (r.e.count_basis) {
		const recovered = r.e.count_basis === 'rq-retained-rows-and-staging';
		return 'Resource counts include retained duplicates' + (recovered ? ' and additional texts recovered from the saved source harvest' : '') +
			'. They cover harvested texts within 1450–1700; texts excluded before the saved harvest may be missing. ' +
			'<a href="#figures">How the figures are made</a>';
	}
	return `Texts, words, languages and period counted in the corpus snapshot${month ? ' of ' + esc(month) : ''}; ` +
		'they may cover only part of the edition. <a href="#figures">How the figures are made</a>';
}

function licenseHTML(e) {
	const label = e.license === 'Copyright' ? '© Copyright' : (e.license || 'Not stated');
	return e.license_url ? extLink(e.license_url, esc(label)) : esc(label);
}

const dl = rows => '<dl class="rec-dl">' + rows.map(x => `<dt>${x[0]}</dt><dd>${x[1]}</dd>`).join('') + '</dl>';
const muted = s => ` <span class="q">${s}</span>`;

function recordHTML(r) {
	if (r.recHTML) return r.recHTML;
	const e = r.e, d = r.d, arch = d.archived_copy;
	const left = [['Edition', extLink(e.url, esc(d.url_display || e.url) + NEW_TAB) + (arch ? muted('(Wayback Machine)') : '')]];
	if (e.doi) left.push(['DOI', extLink('https://doi.org/' + e.doi, esc(e.doi) + NEW_TAB)]);
	if (e.data_url) left.push(['Files', extLink(e.data_url, esc(d.data_display || e.data_url) + NEW_TAB) + ` <span class="q nw">· ${esc(formatsLabel(e))}</span>`]);
	if (e.api_url) left.push(['API', extLink(e.api_url, 'API documentation' + NEW_TAB)]);
	left.push(['Institution', e.institution ? esc(e.institution) : 'Not recorded'], ['Languages', languagesFull(r)], ['Period', periodFull(r)], ['Size', sizeFull(r)]);
	if (e.region) left.push(['Region', esc(e.region)]);
	if (r.countries.length) left.push(['Countries', esc(r.countryNames.join(', ')) + (r.areas.length ? muted('· ' + esc(r.areas.join(', '))) : '')]);
	if (e.author) left.push(['Author', esc(e.author)]);
	if (e.date) left.push(['Date of the documents', esc(e.date)]);
	if (e.years_active && hasNum(e.years_active.start)) left.push(['Years active', esc(yearsActive(e.years_active))]);
	const right = [
		['Encoding', esc(encLabel(e.encoding)) + (has(ENC, e.encoding) ? muted('— ' + esc(ENC[e.encoding][1])) : '')],
		['Licence', licenseHTML(e) + (e.license_note ? muted('— ' + esc(e.license_note)) : '')],
		['Status', statusHTML(e.status) + (has(STATUS, e.status) ? muted('— ' + esc(STATUS[e.status][1])) : '')]
	];
	if (e.corpus_statistics) right.push(['Renascor Corpus', plural(e.corpus_statistics.words, 'word') +
		' in ' + plural(e.corpus_statistics.texts, 'text') + muted('· after corpus deduplication')]);
	if (e.last_modified) right.push(['Last change', esc(e.last_modified) + muted('· reported by the host')]);
	right.push(['Figures', figuresText(r)],
		['Added', esc(e.date_added || '') + muted('· ' + (e.provenance === 'discovered' ? 'proposed by the automated search' : 'submitted by a contributor'))]);
	let h = `<div class="record" id="rec-${esc(r.id)}" role="region" aria-label="Record: ${esc(e.title)}">` + dl(left) + dl(right);
	if (d.notes_display) h += `<div class="rec-notes"><p class="rec-notes-h">Notes</p><p class="rec-notes-t">${esc(d.notes_display)}</p></div>`;
	const correction = `${REPO}/issues/new?template=correction.yml&title=${encodeURIComponent('[correction] ' + e.title)}&entry=${encodeURIComponent(e.title + ' (' + r.id + '.json)')}`;
	h += '<div class="rec-foot">' + extLink(e.url, (arch ? 'Open the archived copy' : 'Open the edition') + ICON.ext + NEW_TAB, ' class="btn primary"') +
		(e.data_url ? extLink(e.data_url, 'Get the ' + esc(downloadNoun(e)) + ICON.ext + NEW_TAB, ' class="btn"') : '') +
		`<button type="button" class="linkbtn copy-link" data-id="${esc(r.id)}">Copy link</button>` +
		`<a href="${REPO}/blob/main/data/entries/${encodeURIComponent(r.id)}.json">Record file (JSON)</a>` +
		`<a href="${esc(correction)}">Report a correction</a><span class="rec-id">Record <code>${esc(r.id)}</code></span></div></div>`;
	return (r.recHTML = h);
}

// == Rendering ==
function refreshLang(r, key) {
	if (r.langKey === key) return;
	r.langKey = key;
	const s = langSummary(r);
	if (r.trLang) { r.trLang.innerHTML = s; r.trMeta.innerHTML = mobileMeta(r); }
	if (r.cardLang) r.cardLang.innerHTML = s;
}

function markOpen(r, el) {
	const o = open.has(r.id);
	el.classList.toggle('open', o);
	setExp(el.querySelector('.tog'), o);
}

function renderList(table) {
	const frag = document.createDocumentFragment(), key = state.lang.join('\u0001');
	shown.forEach(r => {
		const el = table ? rowFor(r) : cardFor(r);
		refreshLang(r, key);
		markOpen(r, el);
		frag.appendChild(el);
		if (table && open.has(r.id)) frag.appendChild(recRowFor(r));
	});
	(table ? els.viewCards : els.tbody).replaceChildren();
	(table ? els.tbody : els.viewCards).replaceChildren(frag);
	if (!table) placeCardPanels();
}

// An open card's record follows the last card of its grid row.
function placeCardPanels() {
	els.viewCards.querySelectorAll('.card-panel').forEach(p => p.remove());
	const cards = Array.from(els.viewCards.querySelectorAll('.card'));
	const cols = getComputedStyle(els.viewCards).gridTemplateColumns.split(' ').filter(Boolean).length || 1;
	for (let start = 0; start < cards.length; start += cols) {
		const end = Math.min(cards.length, start + cols) - 1;
		let after = cards[end];
		for (let j = start; j <= end; j++) {
			const r = byId[cards[j].dataset.id];
			if (open.has(r.id)) { after.after(panelFor(r)); after = r.panel; }
		}
	}
}

function render() {
	if (!ready) return;
	terms = fold(state.q).split(' ').filter(Boolean);
	shown = records.filter(r => matches(r, null)).sort(compare);
	const view = effectiveView(), empty = !shown.length;
	els.viewTable.hidden = view !== 'table' || empty;
	els.viewCards.hidden = view !== 'cards' || empty;
	renderList(view === 'table');
	renderCount();
	renderEmpty();
	renderChips();
	updateFacets();
	renderTimeline();
	syncControls();
	clearNotice();
	writeURL();
	announce();
}

function renderCount() {
	const N = records.length, n = shown.length;
	if (!n) els.catalogue.textContent = 'No edition matches';
	else if (n === N && !narrowed()) els.catalogue.textContent = plural(N, 'edition');
	else els.catalogue.innerHTML = `${fmt(n)} <span class="of">of ${plural(N, 'edition')}</span>`;
}

const announce = debounce(() => {
	const N = records.length, n = shown.length;
	els.live.textContent = !n ? 'No edition matches.'
		: n === N && !narrowed() ? `Showing all ${plural(N, 'edition')}.`
			: `${fmt(n)} of ${plural(N, 'edition')} ${n === 1 ? 'matches' : 'match'}.`;
}, 600);

function renderEmpty() {
	els.state.innerHTML = shown.length ? '' : '<div class="state"><p class="state-title">No edition matches</p>' +
		'<p class="state-text">Try removing a filter, widening the period or checking the spelling. The catalogue lists ' +
		plural(records.length, 'edition') + ' and may not include the one you are looking for yet.</p>' +
		'<div class="actions"><button type="button" class="linkbtn" data-clear-all>Clear the search and all filters</button>' +
		`<a href="${REPO}/issues/new?template=new-entry.yml">Suggest an edition</a></div></div>`;
}

function renderChips() {
	const chips = state.lang.map(v => ['lang', v, v]);
	if (periodActive()) chips.push(['period', '', yearsLabel(state.from, state.to)]);
	const label = { encoding: encLabel, status: statusLabel, size: v => SIZE_LABEL[v] || v, files: v => FILE_LABEL[v] || v, country: countryName };
	LIST_KEYS.slice(1).forEach(k => state[k].forEach(v => chips.push([k, v, (label[k] || String)(v)])));
	els.chips.innerHTML = chips.map(c => {
		const k = FACET_LABEL[c[0]];
		return `<button type="button" class="chip" data-f="${c[0]}" data-v="${esc(c[1])}" aria-label="Remove filter ${esc(k + ': ' + c[2])}">` +
			`<span class="k">${k}:</span><span class="v">${esc(c[2])}</span>${ICON.x}</button>`;
	}).join('') + (chips.length ? '<button type="button" class="linkbtn" data-clear-filters>Clear all filters</button>' : '');
}

function syncControls() {
	els.sort.value = state.sort;
	const [key, dir] = state.sort.split('-');
	document.querySelectorAll('.reg thead th[data-sort]').forEach(th => {
		if (th.dataset.sort === key) th.setAttribute('aria-sort', dir === 'desc' ? 'descending' : 'ascending');
		else th.removeAttribute('aria-sort');
	});
	els.viewTableBtn.setAttribute('aria-pressed', String(state.view === 'table'));
	els.viewCardsBtn.setAttribute('aria-pressed', String(state.view === 'cards'));
	const n = shown.length;
	const f = facetFilterCount();
	els.filterBadge.hidden = !f;
	els.filterBadge.textContent = f;
	if (f) els.filterToggle.setAttribute('aria-label', `Filters, ${f} active`);
	else els.filterToggle.removeAttribute('aria-label');
	els.sheetDone.textContent = n ? 'Show ' + plural(n, 'edition') : 'No edition matches';
}

// == Records: open, close, permalinks ==
function setOpen(r, isOpen) {
	if (isOpen) open.add(r.id); else open.delete(r.id);
	if (effectiveView() === 'table') {
		const tr = rowFor(r);
		markOpen(r, tr);
		if (!isOpen) { if (r.rec) r.rec.remove(); }
		else if (tr.parentNode && !(r.rec && r.rec.parentNode)) tr.after(recRowFor(r));
	} else {
		markOpen(r, cardFor(r));
		placeCardPanels();
	}
}

function toggleRecord(id) {
	const r = byId[id];
	if (!r) return;
	const isOpen = !open.has(id);
	setOpen(r, isOpen);
	if (isOpen) setHash(id);
	else if (decodeHash() === id) setHash('');
}

function decodeHash() {
	try { return decodeURIComponent(location.hash.slice(1)); } catch { return ''; }
}
function setHash(id) {
	try { history.replaceState(history.state, '', location.pathname + queryString() + (id ? '#' + encodeURIComponent(id) : '')); }
	catch { /* sandboxed */ }
}

function showNotice(text) {
	announce.cancel();
	els.notice.textContent = els.live.textContent = text;
	els.notice.hidden = false;
}
function clearNotice() {
	if (els.notice.hidden) return;
	els.notice.hidden = true;
	els.notice.textContent = '';
}

function openFromHash() {
	const id = decodeHash(), r = byId[id];
	clearNotice();
	if (!id) return;
	if (!r) {
		if (!$(id) && /^[a-z0-9-]+$/.test(id)) showNotice(`The linked record “${id}” is not in the catalogue. It may have been renamed or removed.`);
		return;
	}
	const cleared = !shown.includes(r);
	if (cleared) resetAll();
	if (!open.has(id)) setOpen(r, true);
	if (cleared) showNotice('Filters were cleared to show the linked edition.');
	const el = effectiveView() === 'table' ? r.tr : r.card;
	if (!el) return;
	requestAnimationFrame(() => {
		el.scrollIntoView({ block: 'start' });
		el.classList.remove('flash');
		void el.offsetWidth;
		el.classList.add('flash');
		setTimeout(() => el.classList.remove('flash'), 1700);
	});
}

// == URL state ==
function readURL() {
	const p = new URLSearchParams(location.search), C = meta.countries || {};
	// Kept once, and only if some edition has it.
	const valid = (k, v) => (k !== 'files' || hasFiles) && (k !== 'country' || has(C, v)) && records.some(r => FACET_VALUES[k](r).includes(v));
	LIST_KEYS.forEach(k => { state[k] = p.getAll(k).filter((v, i, all) => all.indexOf(v) === i && valid(k, v)); });
	setQ((p.get('q') || '').slice(0, 200));
	const year = v => (/^\d{3,4}$/.test(v || '') ? clamp(+v, MIN, MAX) : null);
	const a = year(p.get('from')), b = year(p.get('to'));
	const from = a === null ? MIN : a, to = b === null ? MAX : b;
	state.from = Math.min(from, to);
	state.to = Math.max(from, to);
	state.sort = SORTS.includes(p.get('sort')) ? p.get('sort') : 'title-asc';
	let view = p.get('view');
	if (view !== 'cards' && view !== 'table') { try { view = localStorage.getItem(VIEW_KEY); } catch { view = null; } }
	state.view = view === 'cards' ? 'cards' : 'table';
}

function queryString() {
	const p = new URLSearchParams();
	if (state.q) p.set('q', state.q);
	LIST_KEYS.forEach(k => state[k].forEach(v => p.append(k, v)));
	if (state.from !== MIN) p.set('from', state.from);
	if (state.to !== MAX) p.set('to', state.to);
	if (state.sort !== 'title-asc') p.set('sort', state.sort);
	if (state.view === 'cards') p.set('view', 'cards');
	const s = p.toString();
	return s ? '?' + s : '';
}

// Throttled: a drag renders every frame.
let urlTimer = 0, urlLast = 0;
function writeURL(now) {
	clearTimeout(urlTimer);
	urlTimer = 0;
	if (drag && !now) return;
	const t = Date.now();
	if (!now && t - urlLast < 250) { urlTimer = setTimeout(() => writeURL(true), 250 - (t - urlLast)); return; }
	urlLast = t;
	const url = location.pathname + queryString() + location.hash;
	if (url !== location.pathname + location.search + location.hash) {
		try { history.replaceState(history.state, '', url); } catch { /* file:// or sandboxed */ }
	}
}

function resetFacets() { LIST_KEYS.forEach(k => { state[k] = []; }); }
function resetPeriod() { state.from = MIN; state.to = MAX; }
function resetAll() {
	setQ('');
	resetFacets();
	resetPeriod();
	$('lang-find').value = '';
	render();
}

// == Clipboard ==
function copyText(text, done) {
	const fallback = () => {
		const ta = document.createElement('textarea');
		ta.value = text;
		ta.readOnly = true;
		ta.style.cssText = 'position:fixed;opacity:0';
		document.body.appendChild(ta);
		ta.select();
		let ok = false;
		try { ok = document.execCommand('copy'); } catch { /* unsupported */ }
		ta.remove();
		done(ok);
	};
	if (navigator.clipboard) navigator.clipboard.writeText(text).then(() => done(true), fallback);
	else fallback();
}

function flashLabel(btn, text) {
	if (!btn.dataset.label) btn.dataset.label = btn.textContent;
	btn.textContent = text;
	clearTimeout(btn._t);
	btn._t = setTimeout(() => { btn.textContent = btn.dataset.label; }, 1600);
}

// == Filters dialog ==
let sheetReturn = null;
function openSheet() {
	if (wideMQ.matches || els.filtersDialog.open) return;
	els.sheetBody.appendChild(els.facets);
	sheetReturn = null;
	try { els.filtersDialog.showModal(); } catch { els.filtersDialog.setAttribute('open', ''); }
}
function closeSheet(returnTo) {
	sheetReturn = returnTo || null;
	if (els.filtersDialog.open) els.filtersDialog.close();
}
function onSheetClosed() {
	els.facetsSlot.appendChild(els.facets);
	const to = sheetReturn;
	sheetReturn = null;
	if (wideMQ.matches) return;
	if (to !== 'catalogue') { els.filterToggle.focus(); return; }
	els.catalogue.scrollIntoView({ block: 'start' });
	els.catalogue.focus({ preventScroll: true });
}

// == Events ==
function wireEvents() {
	const onSearch = debounce(() => { state.q = els.q.value.trim(); render(); }, 150);
	const clearSearch = () => { onSearch.cancel(); setQ(''); render(); };
	on(els.q, 'input', () => { els.qClear.hidden = !els.q.value; onSearch(); });
	on(els.q, 'keydown', ev => {
		if (ev.key === 'Enter') { ev.preventDefault(); onSearch.cancel(); state.q = els.q.value.trim(); render(); }
		else if (ev.key === 'Escape' && els.q.value) { ev.preventDefault(); clearSearch(); }
	});
	on(els.qClear, 'click', () => { clearSearch(); els.q.focus(); });

	on(els.facets, 'change', ev => {
		const t = ev.target;
		if (!t.matches('input[type="checkbox"][data-facet]')) return;
		const list = state[t.dataset.facet], i = list.indexOf(t.value);
		if (t.checked && i < 0) list.push(t.value);
		if (!t.checked && i >= 0) list.splice(i, 1);
		render();
	});
	on(els.facets, 'click', ev => {
		const t = ev.target, clear = t.closest('[data-clear-facet]'), more = t.closest('.area-more');
		if (clear) {
			const key = clear.dataset.clearFacet;
			state[key] = [];
			if (key === 'area') state.country = [];
			render();
			const first = $('facet-' + key).querySelector('input:not([disabled])');
			if (first) first.focus();
		} else if (t.closest('#lang-more')) {
			langExpanded = !langExpanded;
			const find = $('lang-find');
			if (!langExpanded) find.value = '';
			updateLangVisibility();
			if (langExpanded) find.focus();
		} else if (more) showCountries(more, more.getAttribute('aria-expanded') !== 'true');
		else if (t.closest('#clear-facets')) { resetFacets(); render(); els.q.focus(); }
	});
	on(els.facets, 'input', ev => { if (ev.target.id === 'lang-find') updateLangVisibility(); });

	// Timeline
	const cancelDrag = ev => { if (drag && ev.pointerId === drag.id) endDrag(); };
	Object.entries({ pointerdown: onPlotDown, pointermove: onPlotMove, pointerup: onPlotUp, pointercancel: cancelDrag,
		lostpointercapture: cancelDrag, pointerleave: hideHover }).forEach(([t, f]) => on(TL.plot, t, f));
	on(TL.h0, 'keydown', onHandleKey);
	on(TL.h1, 'keydown', onHandleKey);
	[TL.yFrom, TL.yTo].forEach(inp => {
		const now = () => { applyYearsSoon.cancel(); applyYears(true); };
		on(inp, 'input', () => { inp.dataset.dirty = '1'; applyYearsSoon(); });
		on(inp, 'change', now);
		on(inp, 'blur', now);
		on(inp, 'keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); now(); } });
	});
	TL.presets.forEach(b => on(b, 'click', () => {
		const a = +b.dataset.from, z = +b.dataset.to;
		if (state.from === a && state.to === z) setPeriod(MIN, MAX); else setPeriod(a, z);
	}));
	on(TL.clear, 'click', () => { setPeriod(MIN, MAX); TL.h0.focus(); });

	// Chips and "clear" actions
	on(els.chips, 'click', ev => {
		const chip = ev.target.closest('.chip');
		if (chip) {
			const idx = Array.from(els.chips.querySelectorAll('.chip')).indexOf(chip), f = chip.dataset.f;
			if (f === 'period') resetPeriod();
			else state[f] = state[f].filter(x => x !== chip.dataset.v);
			render();
			const rest = els.chips.querySelectorAll('.chip');
			(rest[Math.min(idx, rest.length - 1)] || els.q).focus();
		} else if (ev.target.closest('[data-clear-filters]')) { resetFacets(); resetPeriod(); render(); els.q.focus(); }
	});
	on(els.state, 'click', ev => { if (ev.target.closest('[data-clear-all]')) { resetAll(); els.q.focus(); } });

	// Table and cards
	on(els.tbody, 'click', ev => {
		const t = ev.target, tr = t.closest('tr.row');
		if (!tr) return;
		if (!t.closest('.tog') && (t.closest('a, button, input, select, summary, label') || String(getSelection()))) return;
		toggleRecord(tr.dataset.id);
	});
	on(els.viewCards, 'click', ev => {
		const close = ev.target.closest('.panel-close'), tog = ev.target.closest('.card .tog');
		if (close) {
			const r = byId[close.dataset.id];
			toggleRecord(close.dataset.id);
			if (r && r.card) r.card.querySelector('.tog').focus();
		} else if (tog) toggleRecord(tog.closest('.card').dataset.id);
	});
	document.querySelectorAll('.reg thead th[data-sort] button').forEach(btn => on(btn, 'click', () => {
		const key = btn.parentNode.dataset.sort, [k, d] = state.sort.split('-');
		state.sort = key + '-' + (k === key ? (d === 'asc' ? 'desc' : 'asc') : firstDir(key));
		render();
	}));
	on(els.sort, 'change', () => { state.sort = els.sort.value; render(); });
	const setView = v => {
		if (state.view === v) return;
		state.view = v;
		try { localStorage.setItem(VIEW_KEY, v); } catch { /* no storage */ }
		render();
	};
	on(els.viewTableBtn, 'click', () => setView('table'));
	on(els.viewCardsBtn, 'click', () => setView('cards'));

	// Filters dialog
	on(els.filterToggle, 'click', openSheet);
	on(els.sheetClose, 'click', () => closeSheet());
	on(els.sheetDone, 'click', () => closeSheet('catalogue'));
	on(els.sheetClear, 'click', () => { resetFacets(); render(); });
	on(els.filtersDialog, 'close', onSheetClosed);

	// Copy buttons, "/"
	on(document, 'click', ev => {
		const copy = ev.target.closest('.copy-link');
		if (copy) {
			copyText(location.origin + location.pathname + '#' + encodeURIComponent(copy.dataset.id), ok => {
				flashLabel(copy, ok ? 'Link copied' : 'Copy failed');
				if (ok) els.live.textContent = 'Link copied to the clipboard.';
			});
		}
	});
	if (els.citeCopy) {
		on(els.citeCopy, 'click', () => copyText(els.citeText.textContent.replace(/\s+/g, ' ').trim(), ok => {
			flashLabel(els.citeCopy, ok ? 'Copied' : 'Copy failed');
			if (ok) els.live.textContent = 'Citation copied to the clipboard.';
		}));
	}
	on(document, 'keydown', ev => {
		const a = document.activeElement;
		if (ev.key !== '/' || ev.metaKey || ev.ctrlKey || ev.altKey || els.filtersDialog.open) return;
		if (a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable)) return;
		ev.preventDefault();
		els.q.focus();
		els.q.select();
	});
	on(window, 'hashchange', openFromHash);
	// History may bring another query; a fragment link keeps newer state.
	on(window, 'popstate', () => {
		if (urlTimer) writeURL(true);
		else if (location.search !== queryString()) { readURL(); render(); }
	});

	// Layout
	on(narrowMQ, 'change', render);
	on(wideMQ, 'change', () => { if (wideMQ.matches && els.filtersDialog.open) closeSheet(); updateStickyH(); });
	const ro = new ResizeObserver(() => { updateStickyH(); fitPlaceholder(); });
	ro.observe(els.searchRow);
	ro.observe(els.q);   // narrower with the Filters badge
	on(window, 'resize', debounce(() => {
		if (effectiveView() === 'cards' && open.size) placeCardPanels();
		updateStickyH();
	}, 150));
}

// The longest placeholder that fits uncut.
const PLACEHOLDERS = [els.q.placeholder, 'Search the catalogue', 'Search'];
let measure = null;
function fitPlaceholder() {
	const q = els.q, cs = getComputedStyle(q);
	const room = q.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
	if (room <= 0) return;
	measure = measure || document.createElement('canvas').getContext('2d');
	measure.font = cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
	q.placeholder = PLACEHOLDERS.find(t => measure.measureText(t).width <= room) || PLACEHOLDERS[2];
}

function updateStickyH() {
	document.documentElement.style.setProperty('--sticky-h', (wideMQ.matches ? 0 : els.searchRow.offsetHeight) + 'px');
}

load();
})();
