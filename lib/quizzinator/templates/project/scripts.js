let sortedExperimentKeys = [];

window.onload = window.onload = function() {
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

function renderHistograms() {
  const exps = Array.from(
    document.querySelectorAll('#experiments-container input:checked')
  ).map(cb => cb.id.substring(2));
  console.log(exps);
  console.log(sortedExperimentKeys);

  const qs = document.quizzinator.questions_selected || [];

  if (exps.length === 0 || qs.length === 0) {
    document.getElementById('content-div').innerHTML =
      '<p>Select at least one experiment and one question.</p>';
    return;
  }

  // build tally matrix
  const matrix = tallyByQuestionAndExperiment(qs, exps);

  // compute sorted labels per question
  const questionLabels = {};
  qs.forEach(q => {
    const labels = new Set();
    exps.forEach(e =>
      Object.keys(matrix[q][e] || {}).forEach(l => labels.add(l))
    );
    questionLabels[q] = Array.from(labels).sort((a, b) => {
      const nA = parseFloat(a), nB = parseFloat(b);
      if (!isNaN(nA) && !isNaN(nB)) return nA - nB;
      return a.localeCompare(b);
    });
  });

  // clear & build table
  const container = document.getElementById('content-div');
  container.innerHTML = '';
  const table = document.createElement('table');
  table.id = 'histogram-table';

  // // header
  // const thead = table.createTHead();
  // const headRow = thead.insertRow();
  // headRow.insertCell().textContent = '';
  // exps.forEach(e => {
  //   const th = document.createElement('th');
  //   th.textContent = stripToNumeric(e);
  //   headRow.appendChild(th);
  // });
  //
  // // body
  // const tbody = table.createTBody();
  // qs.forEach(q => {
  //   const tr = tbody.insertRow();
  //   const th = document.createElement('th');
  //   th.textContent = q;
  //   tr.appendChild(th);
  //
  //   // first, compute the baseline (first experiment) percentages
  //   const labels = questionLabels[q];
  //   const ref = exps.length - 1;
  //   const counts0 = matrix[q][exps[ref]] || {};
  //   const total0  = Object.values(counts0).reduce((s, v) => s + v, 0) || 1;
  //   const data0   = labels.map(l => (counts0[l] || 0) / total0 * 100);
  //
  //   // precompute norm of baseline
  //   const norm0 = Math.sqrt(data0.reduce((sum, x) => sum + x*x, 0)) || 1;
  //
  //   // now render each experiment’s histogram + similarity
  //   exps.forEach((e, idx) => {
  //     const td = tr.insertCell();
  //
  //     // create & size canvas
  //     const canvas = document.createElement('canvas');
  //
  //     canvas.id          = `chart_${q}_${e}`;
  //     canvas.className   = 'histogram-canvas';
  //     canvas.style.width = '100%';
  //     canvas.style.height = '200px';
  //     td.appendChild(canvas);
  //
  //     // compute this experiment’s percentages
  //     const counts = matrix[q][e] || {};
  //     const total  = Object.values(counts).reduce((s, v) => s + v, 0) || 1;
  //     const data   = labels.map(l => (counts[l] || 0) / total * 100);
  //
  //     // draw chart
  //     new Chart(canvas, {
  //       type: 'bar',
  //       data: {
  //         labels,
  //         datasets: [{ data }]
  //       },
  //       options: {
  //        // maintainAspectRatio: false,
  //        aspectRatio: canvas.width / parseInt(canvas.style.height),
  //        scales: {
  //          x: {
  //            ticks: { maxRotation: 0, autoSkip: false }
  //          },
  //          y: {
  //            type:  'linear',
  //            beginAtZero: true,
  //            min: 0,
  //            max:         100,
  //            ticks:       { stepSize: 10 },
  //            title:       { display: true, text: '%' }
  //          }
  //        },
  //
  //
  //         plugins: { legend: { display: false } },
  //         animation: false
  //       }
  //     });
  //
  //     // compute & render similarity (skip idx=0)
  //     if (idx != ref) {
  //       const norm1 = Math.sqrt(data.reduce((sum, x) => sum + x*x, 0)) || 1;
  //       const dot   = data0.reduce((sum, x0, i) => sum + x0*data[i], 0);
  //       const sim   = Math.round((dot / (norm0 * norm1)) * 100);
  //
  //       const div = document.createElement('div');
  //       div.className = 'similarity';
  //       div.textContent = `Similarity: ${sim}%`;
  //       td.appendChild(div);
  //     }
  //   });
  // });

  // header
  const thead = table.createTHead();
  const headRow = thead.insertRow();
  headRow.insertCell().textContent = '';
  qs.forEach(q => {
    const th = document.createElement('th');
    th.textContent = q;
    headRow.appendChild(th);
  });

  // body
  const tbody = table.createTBody();
  exps.forEach((e, idx) => {
    const tr = tbody.insertRow();
    const th = document.createElement('th');
    th.textContent = stripToNumeric(e);
    tr.appendChild(th);

    qs.forEach(q => {
      const td = tr.insertCell();

      const canvas = document.createElement('canvas');
      canvas.id          = `chart_${q}_${e}`;
      canvas.className   = 'histogram-canvas';
      canvas.style.width = '400px'; // '100%';
      canvas.style.height = '200px';
      canvas.width = 400;
      canvas.height = 200;
      td.appendChild(canvas);

      const labels = questionLabels[q];
      const counts = matrix[q][e] || {};
      const total  = Object.values(counts).reduce((s, v) => s + v, 0) || 1;
      const data   = labels.map(l => (counts[l] || 0) / total * 100);

      new Chart(canvas, {
        type: 'bar',
        data: {
          labels,
          datasets: [{ data }]
        },
        options: {
          aspectRatio: canvas.width / parseInt(canvas.style.height),
          scales: {
            x: {
              ticks: { maxRotation: 0, autoSkip: false }
            },
            y: {
              type:  'linear',
              beginAtZero: true,
              min: 0,
              max: 100,
              ticks: { stepSize: 10 },
              title: { display: true, text: '%' }
            }
          },
          plugins: { legend: { display: false } },
          animation: false
        }
      });

      // render similarity (compare to reference)
      const ref = exps.length - 1;
      if (idx !== ref) {
        const counts0 = matrix[q][exps[ref]] || {};
        const total0  = Object.values(counts0).reduce((s, v) => s + v, 0) || 1;
        const data0   = questionLabels[q].map(l => (counts0[l] || 0) / total0 * 100);
        const norm0   = Math.sqrt(data0.reduce((sum, x) => sum + x*x, 0)) || 1;
        const norm1   = Math.sqrt(data.reduce((sum, x) => sum + x*x, 0)) || 1;
        const dot     = data0.reduce((sum, x0, i) => sum + x0 * data[i], 0);
        const sim     = Math.round((dot / (norm0 * norm1)) * 100);

        const div = document.createElement('div');
        div.className = 'similarity';
        div.textContent = `Similarity: ${sim}%`;
        td.appendChild(div);
      }
    });
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
function renderMultiHistograms() {
  const exps = Array.from(
    document.querySelectorAll('#experiments-container input:checked')
  ).map(cb => cb.id.substring(2));
  const allQs = document.quizzinator.questions_selected || [];
  const multiQs = getMultiValueQuestions(allQs, exps);

  const container = document.getElementById('multi-div');
  container.innerHTML = '';
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
      Object.keys(matrix[q][e]).forEach(k => {
        max = Math.max(max, parseInt(k, 10));
      });
    });
    maxBuckets[q] = max;
  });

  // helper: cosine similarity
  function cosine(a, b) {
    const dot  = a.reduce((s, x, i) => s + x*b[i], 0);
    const nA   = Math.sqrt(a.reduce((s,x) => s + x*x, 0)) || 1;
    const nB   = Math.sqrt(b.reduce((s,x) => s + x*x, 0)) || 1;
    return Math.round((dot/(nA*nB)) * 100);
  }

  // build table
  const table = document.createElement('table');
  table.id = 'multi-table';

  // // header
  // const thead = table.createTHead();
  // const hr = thead.insertRow();
  // hr.insertCell().textContent = '';
  // exps.forEach(e => {
  //   const th = document.createElement('th');
  //   th.textContent = stripToNumeric(e);
  //   hr.appendChild(th);
  // });
  //
  // // body
  // const tbody = table.createTBody();
  // multiQs.forEach(q => {
  //   const tr = tbody.insertRow();
  //   const th = document.createElement('th');
  //   th.textContent = q;
  //   tr.appendChild(th);
  //
  //   // baseline: first exp percentages
  //   const maxN0 = maxBuckets[q];
  //   let ref = exps.length - 1;
  //   const counts0 = matrix[q][exps[ref]] || {};
  //   const total0  = Object.values(counts0).reduce((s,v) => s+v, 0) || 1;
  //   const data0   = Array.from({length: maxN0}, (_,i) =>
  //                    ((counts0[i+1]||0)/total0)*100);
  //
  //   exps.forEach((e, idx) => {
  //     const td = tr.insertCell();
  //     // canvas
  //     const c = document.createElement('canvas');
  //     c.className   = 'histogram-canvas';
  //     c.style.width = '100%';
  //     c.style.height= '100px';
  //     td.appendChild(c);
  //
  //     // this exp’s data
  //     const counts  = matrix[q][e] || {};
  //     const total   = Object.values(counts).reduce((s,v) => s+v, 0) || 1;
  //     const data    = Array.from({length: maxBuckets[q]}, (_,i) =>
  //                      ((counts[i+1]||0)/total)*100);
  //
  //     // chart
  //     new Chart(c, {
  //       type: 'bar',
  //       data: {
  //         labels: Array.from({length: maxBuckets[q]}, (_,i) => `${i+1}`),
  //         datasets: [{ data }]
  //       },
  //       options: {
  //         aspectRatio: c.width/c.height,
  //         scales: {
  //           x: { ticks: { maxRotation: 0, autoSkip: false } },
  //           y: { min:0, max:100, ticks:{ stepSize:20 }, title:{display:true,text:'%'} }
  //         },
  //         plugins:{ legend:{display:false} },
  //         animation:false
  //       }
  //     });
  //
  //     // similarity
  //     if (idx!=ref) {
  //       const sim = cosine(data0, data);
  //       const d = document.createElement('div');
  //       d.className   = 'similarity';
  //       d.textContent = `Similarity: ${sim}%`;
  //       td.appendChild(d);
  //     }
  //   });
  // });


  // header
  const thead = table.createTHead();
  const headRow = thead.insertRow();
  headRow.insertCell().textContent = '';
  multiQs.forEach(q => {
    const th = document.createElement('th');
    th.textContent = q;
    headRow.appendChild(th);
  });

  // body
  const tbody = table.createTBody();
  exps.forEach((e, idx) => {
    const tr = tbody.insertRow();
    const th = document.createElement('th');
    th.textContent = stripToNumeric(e);
    tr.appendChild(th);

    multiQs.forEach(q => {
      const td = tr.insertCell();

      const canvas = document.createElement('canvas');
      canvas.className = 'histogram-canvas fixed-size';
      canvas.width     = 400;
      canvas.height    = 200;
      canvas.style.width = '400px';
      canvas.style.height = '200px';
      td.appendChild(canvas);

      const maxN = maxBuckets[q];
      const counts = matrix[q][e] || {};
      const total = Object.values(counts).reduce((s,v)=>s+v,0) || 1;
      const data = Array.from({length: maxN}, (_,i) =>
        ((counts[i+1]||0)/total)*100);

      new Chart(canvas, {
        type: 'bar',
        data: {
          labels: Array.from({length: maxN}, (_,i)=>`${i+1}`),
          datasets: [{ data }]
        },
        options: {
          aspectRatio: canvas.width / canvas.height,
          scales: {
            x: { ticks: { maxRotation: 0, autoSkip: false } },
            y: {
              min: 0,
              max: 100,
              ticks: { stepSize: 20 },
              title: { display: true, text: '%' }
            }
          },
          plugins: { legend: { display: false } },
          animation: false
        }
      });

      // Similarity (if not ref)
      const ref = exps.length - 1;
      if (idx !== ref) {
        const counts0 = matrix[q][exps[ref]] || {};
        const total0 = Object.values(counts0).reduce((s,v)=>s+v,0) || 1;
        const data0 = Array.from({length: maxN}, (_,i)=>
          ((counts0[i+1]||0)/total0)*100);

        const sim = cosine(data0, data);
        const div = document.createElement('div');
        div.className = 'similarity';
        div.textContent = `Similarity: ${sim}%`;
        td.appendChild(div);
      }
    });
  });


  container.appendChild(table);
}


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
