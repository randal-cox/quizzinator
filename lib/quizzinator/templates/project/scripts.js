// Similarity helper functions
// -------------------- shared similarity + skew helpers --------------------

function normalizeToProb(vec) {
  const sum = vec.reduce((a, b) => a + b, 0);
  if (!sum) return vec.map(() => 0);
  return vec.map(v => v / sum);
}

// Cosine similarity (0..100), assumes vectors aligned
function cosinePercent(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na  += a[i] * a[i];
    nb  += b[i] * b[i];
  }
  if (!na || !nb) return 0;
  return Math.round(100 * (dot / (Math.sqrt(na) * Math.sqrt(nb))));
}

// Total-variation similarity (0..100): 100 means identical, 0 means maximally different
function totalVariationSimilarityPercent(a, b) {
  const p = normalizeToProb(a);
  const q = normalizeToProb(b);
  let l1 = 0;
  for (let i = 0; i < p.length; i++) l1 += Math.abs(p[i] - q[i]);
  const tv = 0.5 * l1;         // 0..1
  return Math.round(100 * (1 - tv));
}

// Skewness over ordered numeric labels; ignores non-numeric labels (e.g. "MISSING")
function skewnessFromOrdered(labels, values) {
  const xs = [];
  const ws = [];
  for (let i = 0; i < labels.length; i++) {
    const x = Number(labels[i]);
    if (!Number.isNaN(x)) {
      xs.push(x);
      ws.push(values[i]);
    }
  }
  if (xs.length < 2) return null;

  const p = normalizeToProb(ws);
  const mu = p.reduce((acc, pi, i) => acc + pi * xs[i], 0);
  const var_ = p.reduce((acc, pi, i) => {
    const d = xs[i] - mu;
    return acc + pi * d * d;
  }, 0);
  const sd = Math.sqrt(var_);
  if (!sd) return 0;

  const m3 = p.reduce((acc, pi, i) => {
    const d = xs[i] - mu;
    return acc + pi * d * d * d;
  }, 0);

  return m3 / (sd * sd * sd);
}

function fmtSkew(v) {
  if (v == null) return "NA";
  return (Math.round(v * 100) / 100).toFixed(2);
}


// ------------------------------------------------------
// Code to change order of display

// Pick Humans as reference if present; otherwise last selected.
function pickReferenceExp(exps) {
  if (!exps || !exps.length) return null;
  const humans = exps.find(e => String(e).toLowerCase() === "humans");
  return humans || exps[exps.length - 1];
}

// Render order: reference first, then everyone else in their original order.
function orderExpsRefFirst(exps, refExp) {
  if (!refExp) return exps.slice();
  return [refExp, ...exps.filter(e => e !== refExp)];
}

// For skew: ignore non-numeric labels (e.g. MISSING) rather than nuking skew entirely.
function skewnessIgnoringNonNumeric(labels, values) {
  const xs = [];
  const vs = [];
  for (let i = 0; i < labels.length; i++) {
    const n = Number(labels[i]);
    if (!Number.isNaN(n)) {
      xs.push(n);
      vs.push(values[i]);
    }
  }
  if (!xs.length) return null;

  // Compute skew on ordered numeric domain xs with weights proportional to vs.
  const p = normalizeToProb(vs);
  const mu = p.reduce((acc, pi, i) => acc + pi * xs[i], 0);
  const var_ = p.reduce((acc, pi, i) => {
    const d = xs[i] - mu;
    return acc + pi * d * d;
  }, 0);
  const sd = Math.sqrt(var_);
  if (!sd) return 0;

  const m3 = p.reduce((acc, pi, i) => {
    const d = xs[i] - mu;
    return acc + pi * d * d * d;
  }, 0);

  return m3 / (sd * sd * sd);
}

// ------------------------------------------------------



// global list of experiments
let sortedExperimentKeys = [];



















window.onload = function() {
  // ────────────────────────────────────────────────
  // 1) At startup, make sure our storage object exists
  // ────────────────────────────────────────────────
  document.quizzinator = document.quizzinator || {};
  document.quizzinator.questions_selected = [];
  main();
}

// ────────────────────────────────────────────────
// 3) “Experiments” wiring is unchanged:
//    clicking any of these re-runs update_comparisons()
// ────────────────────────────────────────────────
/**
 * Called on page load.
 *  1) Builds `sortedExperimentKeys` by grouping “echo_<Type>_<Num>B” keys,
 *     numeric‐only keys (e.g. “7B” or “1.5B_p2”), and any “others”,
 *     then appends all “Humans…” keys at the very end.
 *  2) Renders the checkboxes in that exact order (with an <hr> before “Humans”).
 */
// -------------------------------------------------------------
// Global array holding the fully sorted list of experiment keys.
function main() {
  const allKeys = Object.keys(document.quizzinator.data);

  // 1) Anything starting with “humans” (case‐insensitive) goes to the bottom:
  const humanKeys = allKeys.filter(k => k.toLowerCase().startsWith('humans'));
  const numericKeys = allKeys.filter(k => !k.toLowerCase().startsWith('humans'));

  // 2) Split numericKeys into "<Type>_<Num>B" entries vs. everything else:
  const typeNumPattern = /^([^_]+)_(\d+(?:\.\d+)?)B$/i;
  const leadingFloat   = /^(\d+(?:\.\d+)?)[bB]/;

  const typeNumKeys = numericKeys.filter(k => typeNumPattern.test(k));
  const others      = numericKeys.filter(k => !typeNumPattern.test(k));

  // 2a) Sort typeNumKeys by Type first (alphabetically), then by numeric suffix:
  typeNumKeys.sort((a, b) => {
    const mA = a.match(typeNumPattern);
    const mB = b.match(typeNumPattern);
    const typeA = mA[1].toLowerCase();
    const typeB = mB[1].toLowerCase();
    if (typeA !== typeB) {
      return typeA.localeCompare(typeB);
    }
    return parseFloat(mA[2]) - parseFloat(mB[2]);
  });

  // 2b) Of “others”, pick out those starting with a float (e.g. “1.5B”):
  const numericOnlyKeys = others.filter(k => leadingFloat.test(k));
  const otherKeys       = others.filter(k => !leadingFloat.test(k));

  // 2c) Sort numericOnlyKeys by that leading float, tiebreak alphabetically:
  numericOnlyKeys.sort((a, b) => {
    const numA = parseFloat(a.match(leadingFloat)[1]);
    const numB = parseFloat(b.match(leadingFloat)[1]);
    if (numA !== numB) {
      return numA - numB;
    }
    return a.localeCompare(b);
  });

  // 2d) Sort any remaining otherKeys purely alphabetically:
  otherKeys.sort((a, b) => a.localeCompare(b));

  // 2e) Build a single array: [ typeNumKeys…, numericOnlyKeys…, otherKeys… ]
  const sortedNumericKeys = typeNumKeys.concat(numericOnlyKeys, otherKeys);

  // 3) Sort humanKeys alphabetically (so “Humans” < “Humans_66” < etc.)
  humanKeys.sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));

  // 4) Final ordering: numeric‐group first, then all “Humans…” at the end
  sortedExperimentKeys = sortedNumericKeys.concat(humanKeys);

  // 5) Decide where to draw the <hr> (i.e. right after the last numeric key):
  const hrAfter = sortedNumericKeys.length
    ? sortedNumericKeys[sortedNumericKeys.length - 1]
    : null;

  // 6) Render checkboxes in #experiments-container in sortedExperimentKeys order:
  const expContainer = document.getElementById('experiments-container');
  createCheckboxes(sortedExperimentKeys, expContainer, {
    onChange: (_k, _c) => update_comparisons(),
    hrAfter
  });

//   // DEBUG: auto-select experiments for debugging
//   const DEBUG_AUTOSELECT_EXPS = true;
//   const DEBUG_EXPS = new Set(["Gender_1.5B", "Gender_7B", "Humans"]);
//
//   createCheckboxes(expNames, expContainer, {
//     isChecked: (exp) => DEBUG_AUTOSELECT_EXPS && DEBUG_EXPS.has(exp),
//     onChange: (exp, checked) => { /* existing handler */ }
//   });

  // DEBUG ONLY: preselect a few experiments for easier iteration
  const debugSelect = ['Gender_1.5B', 'Gender_7B', 'Humans'];

  debugSelect.forEach(k => {
    const cb = document.getElementById('id' + k);
    if (cb) cb.checked = true;
  });

  // kick one render pass (without selecting common questions)
  update_comparisons();
  renderHistograms();
  renderMultiHistograms();
  renderRawData();

}



function utils_save_div(divId, outputFilename) {
  let divElement = document.getElementById(divId);

  if (!divElement) {
    console.error(`Div with id "${divId}" not found.`);
    return;
  }

  html2canvas(divElement).then(canvas => {
    const imgData = canvas.toDataURL('image/png');  // can also try 'image/jpeg'

    const downloadLink = document.createElement("a");
    downloadLink.href = imgData;
    downloadLink.download = `${outputFilename}_${new Date().toISOString()}.png`;  // .jpg for jpeg
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
  });
}
function utils_save_div_to_svg(divId, outputFilename) {
  var svgContent = document.getElementById(divId).outerHTML; // get svg content

  var blob = new Blob([svgContent], {type: 'image/svg+xml'});  // create a file blob of svg content
  var url = URL.createObjectURL(blob);  // create a blob url of that blob

  // Create download link and click it
  var a = document.createElement('a');
  a.download = outputFilename;
  a.href = url;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  URL.revokeObjectURL(url); // free up storage--no longer needed.
}

// ────────────────────────────────────────────────
// 4) Questions wiring now persists into
//    document.quizzinator.checkboxes and restores on redraw
// ────────────────────────────────────────────────
function update_comparisons() {
  const checkedExps = Array.from(
    document.querySelectorAll('#experiments-container input[type=checkbox]:checked')
  ).map(cb => cb.id.substring(2));

  refreshCommonQuestionsBasedOnExperiments(checkedExps);
}

function refreshCommonQuestionsBasedOnExperiments(experiments) {
  const updatedQuestions = getCommonQuestionsBasedOnExperiments(experiments);
  const qContainer = document.getElementById('questions-list');
  qContainer.innerHTML = '';

  createCheckboxes(updatedQuestions, qContainer, {
    // initialize from our persisted map
    isChecked: questionKey => !!(
      document.quizzinator &&
      document.quizzinator.checkboxes &&
      document.quizzinator.checkboxes[questionKey]
    ),
    // write back into the map whenever a question toggles
    onChange: (questionKey, checked) => {
      // ensure the storage object is there
      document.quizzinator = document.quizzinator || {};
      document.quizzinator.checkboxes = document.quizzinator.checkboxes || {};
      document.quizzinator.checkboxes[questionKey] = checked;
      // keep your “selectedQuestions” array in sync if needed:
      getSelectedQuestions();
    }
  });
}

// ────────────────────────────────────────────────
// 2) Generalized createCheckboxes:
//    - takes an optional `onChange` callback
//    - takes an optional `isChecked` function
// ────────────────────────────────────────────────
/**
 * @param {string[]} items
 * @param {HTMLElement} container
 * @param {{
 *   onChange?: (item: string, checked: boolean) => void,
 *   isChecked?: (item: string) => boolean,
 *   hrAfter?: string
 * }} [opts]
 */
function createCheckboxes(items, container, opts = {}) {
  const { onChange, isChecked, hrAfter } = opts;

  items.forEach(item => {
    const checkbox = document.createElement('input');
    checkbox.type  = 'checkbox';
    checkbox.id    = 'id' + item;
    checkbox.value = item;

    if (typeof isChecked === 'function') {
      checkbox.checked = !!isChecked(item);
    }
    if (typeof onChange === 'function') {
      checkbox.addEventListener('change', e => onChange(item, e.target.checked));
    }

    const label = document.createElement('label');
    label.htmlFor = checkbox.id;
    label.textContent = item;

    container.append(checkbox, label, document.createElement('br'));

    // Insert <hr> after the specified item
    if (hrAfter != null && item === hrAfter) {
      container.appendChild(document.createElement('hr'));
    }
  });
}

// ────────────────────────────────────────────────
// 5) getSelectedQuestions simply reads the DOM
//    and updates your questions_selected array
// ────────────────────────────────────────────────
function getSelectedQuestions() {
  const checked = Array.from(
    document.querySelectorAll('#questions-container input[type=checkbox]:checked')
  ).map(cb => cb.id.substring(2));
  return document.quizzinator.questions_selected = checked;
}
function getCommonQuestionsBasedOnExperiments(selectedExperiments) {
  if (selectedExperiments.length === 0) return [];

  function getQuestionKeysFor(experiment) {
    const keys = new Set();
    const responses = document.quizzinator.data[experiment].responses || [];
    responses.forEach(response => {
      if (response && typeof response === "object") {
        Object.keys(response).forEach(k => {
          // filter out unwanted keys right away
          if (!k.startsWith('_') && k !== 'number') {
            keys.add(k);
          }
        });
      }
    });
    return keys;
  }

  // initialize intersection with first experiment’s filtered keys
  let commonKeys = getQuestionKeysFor(selectedExperiments[0]);

  // intersect with each subsequent experiment’s filtered keys
  for (let i = 1; i < selectedExperiments.length; i++) {
    const expKeys = getQuestionKeysFor(selectedExperiments[i]);
    for (const key of Array.from(commonKeys)) {
      if (!expKeys.has(key)) {
        commonKeys.delete(key);
      }
    }
  }

  return Array.from(commonKeys);
}
/**
 * 1) Turn any “raw” response into an array of strings.
 */
function parseAnswer(raw) {
  if (Array.isArray(raw)) return raw.map(String);
  if (raw == null) return [];
  let s = String(raw).trim();
  // strip wrapping [ ... ] if present
  if (/^\[.*\]$/.test(s)) {
    s = s.slice(1, -1);
  }
  // now split on commas or dashes between numbers
  // (commas are primary)
  return s
    .split(/\s*[,;-]\s*/)
    .map(x => x.replace(/^['"]|['"]$/g, '').trim())
    .filter(x => x !== '');
}

/**
 * 2) For each question + experiment, build a counts map {value→count}
 */
function tallyByQuestionAndExperiment(questions, experiments) {
  const matrix = {};
  experiments.forEach(exp => {
    const responses = document.quizzinator.data[exp].responses || [];
    questions.forEach(q => {
      matrix[q] = matrix[q] || {};
      matrix[q][exp] = matrix[q][exp] || {};
      responses.forEach(resp => {
        const answers = parseAnswer(resp[q]);
        answers.forEach(ans => {
          matrix[q][exp][ans] = (matrix[q][exp][ans] || 0) + 1;
        });
      });
    });
  });
  return matrix;
}

/**
 * Given a string, returns the substring starting at the first digit encountered.
 * If no digit exists, returns the original string.
 *
 * Examples:
 *   stripToNumeric("echo_Gender_1.5B_p2")  // "1.5B_p2"
 *   stripToNumeric("7B")                   // "7B"
 *   stripToNumeric("Humans_66")            // "66"
 *   stripToNumeric("NoDigitsHere")         // "NoDigitsHere"
 */
function stripToNumeric(str) {
  // Find the index of the first digit character
  const firstDigitIdx = str.search(/\d/);
  if (firstDigitIdx === -1) {
    // No digits found → return original
    return str;
  }
  // Slice from the first digit through the end
  return str.slice(firstDigitIdx);
}


/**
 * 3) Render the table + canvases and kick off Chart.js
 */
/**
 * Single-answer style histograms (labels come from observed categories).
 * Expects globals already in your file:
 *   - tallyByQuestionAndExperiment(questions, exps)
 *   - cosineSimilarityPercent(a,b)   (or whatever name you currently use)
 *   - totalVariationSimilarityPercent(a,b)
 *   - fmtSkew()
 */
/**
 * Multi-answer style histograms (forces labels 1..maxN).
 * This is the “always show the full option range” renderer.
 */

function renderHistograms() {
  // selected experiments (ids like ex_Gender_7B -> "Gender_7B")
  const expsRaw = Array.from(
    document.querySelectorAll('#experiments-container input:checked')
  ).map(cb => cb.id.substring(2));

  // selected questions (from the Common Questions list)
  const questions = Array.from(
    document.querySelectorAll('#questions-list input:checked')
  ).map(cb => cb.value);

  const container = document.getElementById('content-div');
  container.innerHTML = '';

  if (expsRaw.length === 0 || questions.length === 0) {
    container.innerHTML = '<p>(Select experiments and questions to render histograms.)</p>';
    return;
  }

  // Choose reference experiment: Humans if present, otherwise last selected
  const refExp = expsRaw.find(e => /human/i.test(e)) ?? expsRaw[expsRaw.length - 1];

  // Display order: reference first (Humans first), then the rest in original order
  const exps = [refExp, ...expsRaw.filter(e => e !== refExp)];

  // Tally per-question counts per experiment
  const matrix = tallyByQuestionAndExperiment(questions, exps);

  // Build label set per question (sorted numeric if possible)
  const questionLabels = {};
  questions.forEach(q => {
    const labelsSet = new Set();
    exps.forEach(exp => {
      const counts = matrix[q]?.[exp] || {};
      Object.keys(counts).forEach(k => labelsSet.add(k));
    });
    let labels = Array.from(labelsSet);

    // numeric-ish sort (keep non-numeric at the end)
    const numeric = labels.every(x => !Number.isNaN(Number(x)));
    if (numeric) labels.sort((a, b) => Number(a) - Number(b));
    else labels.sort();

    questionLabels[q] = labels;
  });

  // Table: rows = experiments, cols = questions
  const table = document.createElement('table');
  table.className = 'hist-table';

  const header = document.createElement('tr');
  header.appendChild(document.createElement('th')); // blank corner
  questions.forEach(q => {
    const th = document.createElement('th');
    th.textContent = q;
    header.appendChild(th);
  });
  table.appendChild(header);

  exps.forEach((exp, idx) => {
    const tr = document.createElement('tr');
    if (exp === refExp) tr.classList.add('ref-row');
    console.log(exp, refExp);

    const rowHdr = document.createElement('th');
    rowHdr.classList.add('row-label');

    const labelSpan = document.createElement('span');
    labelSpan.className = 'row-label-text';
    labelSpan.textContent = exp.split('_').pop(); // "7B", "1.5B", "Humans", etc.

    rowHdr.appendChild(labelSpan);
    tr.appendChild(rowHdr);


    questions.forEach(q => {
      const td = document.createElement('td');

      const labels = questionLabels[q];

      // percent vector for this experiment
      const counts = matrix[q]?.[exp] || {};
      const total = Object.values(counts).reduce((s, v) => s + v, 0) || 1;
      const data = labels.map(l => (counts[l] || 0) / total * 100);

      // canvas
      const canvas = document.createElement('canvas');
      canvas.style.width  = '300px';
      canvas.style.height = '200px';
      // td.appendChild(canvas);

      const wrap = document.createElement('div');
      wrap.className = 'chart-wrap';   // CSS controls size
      wrap.appendChild(canvas);
      td.appendChild(wrap);


      new Chart(canvas, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: '#bdbdbd',
            borderColor: '#000000',
            borderWidth: 1
          }]
        },
        options: {
          aspectRatio: canvas.width / parseInt(canvas.style.height),

          responsive: true,
          maintainAspectRatio: false,

          plugins: { legend: { display: false } },
          animation: false,
          scales: {
            x: {
              ticks: { maxRotation: 0, autoSkip: false, color: '#000' },
              grid: { color: '#e0e0e0' },
              title: { display: false }
            },
            y: {
              beginAtZero: true,
              min: 0,
              max: 100,
              ticks: { stepSize: 10, color: '#000' },
              grid: { color: '#e0e0e0' },
              title: { display: true, text: '%' }
            }
          }
        }
      });

      // ---- Metrics line (reference first; comparisons vs reference) ----
      const refCounts = matrix[q]?.[refExp] || {};
      const refTotal  = Object.values(refCounts).reduce((s, v) => s + v, 0) || 1;
      const refData   = labels.map(l => (refCounts[l] || 0) / refTotal * 100);

      const skewRef = skewnessFromOrdered(labels, refData);
      const skew    = skewnessFromOrdered(labels, data);

      const div = document.createElement('div');
      div.className = 'similarity';

      if (exp === refExp) {
        div.textContent = `S ${fmtSkew(skewRef)}`;
      } else {
        const dSkew = (skew != null && skewRef != null) ? (skew - skewRef) : null;
        const cs    = cosinePercent(refData, data);
        const tvs   = totalVariationSimilarityPercent(refData, data);

        div.textContent =
          `S ${fmtSkew(skew)} (Δ ${fmtSkew(dSkew)}) | CS ${Math.round(cs)} | TVS ${Math.round(tvs)}`;
      }

      td.appendChild(div);
      tr.appendChild(td);
    });

    table.appendChild(tr);
  });

  container.appendChild(table);
}


function renderMultiHistograms() {
  const expsRaw = Array.from(
    document.querySelectorAll('#experiments-container input:checked')
  ).map(cb => cb.id.substring(2));

  const allQs = Array.from(
    document.querySelectorAll('#questions-list input:checked')
  ).map(cb => cb.value);

  const container = document.getElementById('multi-div');
  container.innerHTML = '';

  if (expsRaw.length === 0 || allQs.length === 0) {
    container.innerHTML = '<p>(Select experiments and questions to render histograms.)</p>';
    return;
  }

  // Reference experiment = Humans if present, else last
  const refExp = expsRaw.find(e => /human/i.test(e)) ?? expsRaw[expsRaw.length - 1];
  const exps   = [refExp, ...expsRaw.filter(e => e !== refExp)];

  // Only questions that ever have >1 answers
  const multiQs = getMultiValueQuestions(allQs, exps);

  if (multiQs.length === 0) {
    container.innerHTML = '<p>No questions with multiple answers.</p>';
    return;
  }

  // build multiplicity matrix and determine max “# answers” bucket
  const matrix = tallyMultiplicity(multiQs, exps);

  const maxBuckets = {};
  multiQs.forEach(q => {
    let max = 1;
    exps.forEach(e => {
      Object.keys(matrix[q]?.[e] || {}).forEach(k => {
        max = Math.max(max, parseInt(k, 10));
      });
    });
    maxBuckets[q] = max;
  });

  const table = document.createElement('table');
  table.className = 'hist-table';

  // header row
  const hdr = document.createElement('tr');
  hdr.appendChild(document.createElement('th'));
  multiQs.forEach(q => {
    const th = document.createElement('th');
    th.textContent = q;
    hdr.appendChild(th);
  });
  table.appendChild(hdr);

  exps.forEach(exp => {
    const tr = document.createElement('tr');
    if (exp === refExp) tr.classList.add('ref-row');

    const th = document.createElement('th');
    th.classList.add('row-label');

    const labelSpan = document.createElement('span');
    labelSpan.className = 'row-label-text';
    labelSpan.textContent = exp.split('_').pop(); // "7B", "1.5B", "Humans", etc.

    th.appendChild(labelSpan);
    tr.appendChild(th);

    multiQs.forEach(q => {
      const td = document.createElement('td');

      const maxN = maxBuckets[q];
      const labels = Array.from({ length: maxN }, (_, i) => `${i + 1}`);

      // build percent vector for this exp
      const counts = matrix[q]?.[exp] || {};
      const total  = Object.values(counts).reduce((s, v) => s + v, 0) || 1;
      const data   = labels.map(l => ((counts[Number(l)] || 0) / total) * 100);

      const canvas = document.createElement('canvas');
      canvas.style.width  = '300px';
      canvas.style.height = '200px';
      // td.appendChild(canvas);
      const wrap = document.createElement('div');
      wrap.className = 'chart-wrap';   // CSS controls size
      wrap.appendChild(canvas);
      td.appendChild(wrap);


      new Chart(canvas, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: '#bdbdbd',
            borderColor: '#000000',
            borderWidth: 1
          }]
        },
        options: {
          aspectRatio: canvas.width / parseInt(canvas.style.height),

          responsive: true,
          maintainAspectRatio: false,

          plugins: { legend: { display: false } },
          animation: false,
          scales: {
            x: {
              ticks: { maxRotation: 0, autoSkip: false, color: '#000' },
              grid: { color: '#e0e0e0' },
              title: { display: false }
            },
            y: {
              beginAtZero: true,
              min: 0,
              max: 100,
              ticks: { stepSize: 20, color: '#000' },
              grid: { color: '#e0e0e0' },
              title: { display: true, text: '%' }
            }
          }
        }
      });

      // ---- Metrics line: compare to reference (ref row shows only skew) ----
      const refCounts = matrix[q]?.[refExp] || {};
      const refTotal  = Object.values(refCounts).reduce((s, v) => s + v, 0) || 1;
      const refData   = labels.map(l => ((refCounts[Number(l)] || 0) / refTotal) * 100);

      const skewRef = skewnessFromOrdered(labels, refData);
      const skew    = skewnessFromOrdered(labels, data);

      const div = document.createElement('div');
      div.className = 'similarity';

      if (exp === refExp) {
        div.textContent = `S ${fmtSkew(skewRef)}`;
      } else {
        const dSkew = (skew != null && skewRef != null) ? (skew - skewRef) : null;
        const cs    = cosinePercent(refData, data);
        const tvs   = totalVariationSimilarityPercent(refData, data);

        div.textContent =
          `S ${fmtSkew(skew)} (Δ ${fmtSkew(dSkew)}) | CS ${Math.round(cs)} | TVS ${Math.round(tvs)}`;
      }

      td.appendChild(div);
      tr.appendChild(td);
    });

    table.appendChild(tr);
  });

  container.appendChild(table);
}


/**
 * 1) Determine which questions ever have >1 answers
 */
function getMultiValueQuestions(questions, experiments) {
  return questions.filter(q => {
    return experiments.some(exp => {
      return document.quizzinator.data[exp].responses.some(resp => {
        return parseAnswer(resp[q]).length > 1;
      });
    });
  });
}

/**
 * 2) Tally “# of answers per response” counts
 *    matrix[q][exp] = { 1: count1, 2: count2, … }
 */
function tallyMultiplicity(questions, experiments) {
  const matrix = {};
  experiments.forEach(exp => {
    const responses = document.quizzinator.data[exp].responses || [];
    questions.forEach(q => {
      matrix[q] = matrix[q] || {};
      matrix[q][exp] = matrix[q][exp] || {};
      responses.forEach(resp => {
        const n = parseAnswer(resp[q]).length;
        matrix[q][exp][n] = (matrix[q][exp][n] || 0) + 1;
      });
    });
  });
  return matrix;
}

/**
 * 3) Render the multi‐value histograms into #multi-div
 */




// ────────────────────────────────────────────────
// 6) Hook‐it‐up: re‐render histograms on any change
// ────────────────────────────────────────────────
document
  .getElementById('experiments-container')
  .addEventListener('change', () => {
    renderHistograms();
    renderMultiHistograms();
    renderRawData();
  });

document
  .getElementById('questions-list')
  .addEventListener('change', () => {
    renderHistograms()
    renderMultiHistograms();
    renderRawData();
  });

// 4) Hook it up to run whenever experiments or questions change
document
  .getElementById('questions-list')
  .addEventListener('change', renderMultiHistograms);

// optional initial draw
// renderMultiHistograms();

function renderRawData() {
  const container = document.getElementById('raw-data-container');
  container.innerHTML = '';

  const exps = Array.from(
    document.querySelectorAll('#experiments-container input:checked')
  ).map(cb => cb.id.substring(2));
  const qs = document.quizzinator.questions_selected || [];

  if (exps.length === 0 || qs.length === 0) {
    container.innerHTML = '<p>Select at least one experiment and one question to view raw data.</p>';
    return;
  }

  exps.forEach(exp => {
    const responses = document.quizzinator.data[exp].responses || [];

    // Build CSV header
    const header = ['number'].concat(qs);
    const rows = [header.map(csvEscape).join(',')];

    // Add each row
    responses.forEach(resp => {
      const row = [resp.number || ''].concat(
        qs.map(q => csvEscape((parseAnswer(resp[q] || '')).join(',')))
      );
      rows.push(row.join(','));
    });

    const csvText = rows.join('\n');
    const section = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = exp;

    const pre = document.createElement('pre');
    pre.textContent = csvText;

    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'Copy';
    copyBtn.className = 'copy-btn';
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(csvText)
        .then(() => copyBtn.textContent = 'Copied!')
        .catch(() => copyBtn.textContent = 'Failed to copy');
      setTimeout(() => (copyBtn.textContent = 'Copy'), 2000);
    });

    section.appendChild(summary);
    section.appendChild(copyBtn);
    section.appendChild(pre);
    container.appendChild(section);
  });
}

function csvEscape(value) {
  const needsQuotes = /[",\n]/.test(value);
  const escaped = String(value).replace(/"/g, '""');
  return needsQuotes ? `"${escaped}"` : escaped;
}
