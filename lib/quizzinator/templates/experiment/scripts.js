window.addEventListener("DOMContentLoaded", () => {
  displayProjectName();
  renderQuizLinks();
  renderExperimentMeta();
  generateHistograms();
});

function displayProjectName() {
  const titleEl = document.getElementById("dashboard-title");
  const meta = document.quizzinator.meta || {};
  if (meta.name) titleEl.innerHTML = `<b>Project</b>: ${meta.project}/experiments/${meta.name}`;
}

function renderQuizLinks() {
  // Get meta from document
  let meta = document.quizzinator.meta || {};

  // Check if 'from_hints' is true, if yes then return and don't render the quiz links
  if (meta['from_hints'] === true) {
    // hide the container
    document.querySelector('#quiz-links-details').style.display = 'none';
    return;
  }

  let quizIds = Object.keys(document.quizzinator.quizData).map(key => document.quizzinator.quizData[key].number) || [];

  quizIds = quizIds.sort((a, b) => {
    return Number(a) - Number(b);
  });
  const quizLinks = document.getElementById("quiz-links");

  quizIds.forEach(id => {
    const a = document.createElement("a");
    a.href = `quizzes/${id}/index.html`;
    a.textContent = id;
    a.style.marginRight = '0.5rem';
    quizLinks.appendChild(a);
  });
}
function renderExperimentMeta() {
  const expMeta = document.quizzinator.meta || {};
  const metaTbody = document.querySelector("#experiment-meta-table tbody");

  // Define default values in desired order
  const defaultKeysOrder = ["project", "name", "model", "size", "questions", "hints"];

  defaultKeysOrder.forEach((key) => {
    if (key in expMeta) {
      const tr = document.createElement("tr");
      const td1 = document.createElement("td");
      td1.textContent = key;
      const td2 = document.createElement("td");

      if (key === "model" && expMeta.from_hints) {
        td2.textContent = "From Hints";
      } else {
        td2.textContent = Array.isArray(expMeta[key]) ? expMeta[key].join(', ') : String(expMeta[key]);
      }

      tr.append(td1, td2);
      metaTbody.appendChild(tr);
    }
  });

  // Stars, End, and Elapsed time
  if (expMeta.start && expMeta.end) {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td");
    td1.textContent = "time";
    const td2 = document.createElement("td");

    let startDateISO = new Date(expMeta.start * 1000).toISOString(); // convert to milliseconds
    let endDateISO = new Date(expMeta.end * 1000).toISOString();
    let elapsedTime = ((expMeta.end - expMeta.start) / 60).toFixed(1); // Convert seconds to minutes

    let startDate = startDateISO.split(".")[0]; // Remove the fractional part of the second
    let endDate = endDateISO.split(".")[0];

    td2.textContent = `${startDate} to ${endDate} [${elapsedTime} minutes elapsed]`;
    tr.append(td1, td2);
    metaTbody.appendChild(tr);
  }

  // Handle remaining keys
  Object.entries(expMeta).forEach(([key, val]) => {
    if (!defaultKeysOrder.includes(key) && !["from_hints", "start", "end"].includes(key)) {
      const tr = document.createElement("tr");
      const td1 = document.createElement("td");
      td1.textContent = key;
      const td2 = document.createElement("td");
      td2.textContent = Array.isArray(val) ? val.join(', ') : String(val);
      tr.append(td1, td2);
      metaTbody.appendChild(tr);
    }
  });
}
function generateHistograms() {
  const data = document.quizzinator.quizData || [];
  if (!data.length) return;
  const cols = Object.keys(data[0]);
  const container = document.getElementById("charts-container");

  cols.forEach((col, i) => {
    if (!col.startsWith("_")) {
      // Create a new div for every histogram
      const histContainer = document.createElement("div");
      histContainer.id = `histogramContainer-${i}`; // Assign a unique id
      container.appendChild(histContainer); // Append new container to the parent container

      processColumn(data, col, `histogramContainer-${i}`);
    }
  });
}

function processColumn(data, col, histContainerId) {
  // skip the number column
  if (col == 'number') return;

  // computeAll will return all (frequencies) and status of non-numeric data
  const [all, hasIllegals] = computeAll(data, col);

  if (!hasIllegals) {
    // calculate frequencies
    const frequencies = all.reduce((accum, val) => {
      accum[val] = (accum[val] || 0) + 1;
      return accum;
    } , {});

    // compute total count
    const totalCount = Object.values(frequencies).reduce((accum, val) => accum + val, 0);

    // calculate percentages
    const percentages = {};
    for (let [key, value] of Object.entries(frequencies)) {
      percentages[key] = (value / totalCount) * 100;
    }

    console.log(["col", col])

    // Use percentages to generate histogram
    createHistogram(col, histContainerId, percentages, all.length, document.quizzinator.hints);
  }
}

function computeAllArray(v) {
  let arrayValues = Array.isArray(v) ? v : false;
  let resultValues = [];

  try {
    arrayValues = arrayValues || JSON.parse(v.replace(/'/g, "\""));
  } catch(err) {
    return false; // Return false immediately if an error is thrown
  }

  if (Array.isArray(arrayValues)) {
    arrayValues.forEach(x => {
      let xSplit = x.trim().split(',');
      xSplit.forEach(y => {
        y = y.trim();
        y.split('-').forEach(z => {
          z = z.trim();
          if (/^\d+$/.test(z)) { // if it is numeric
            resultValues.push(z);
          } else {
            return false; // If a value is non-numeric, return false
          }
        });
      });
    });
  } else {
    return false; // If arrayValues is not an array, return false
  }

  return resultValues; // Return the processed array values
}
function computeAll(data, col) {
  let all = [], hasIllegalValues = false;
  let values = data.map(r => (r[col] || "").trim()); // Collect column values

  values.forEach(v => {
    if (/^\d+$/.test(v)) {
      all.push(v);
      return; // If the value is a single number, proceed to the next
    }

    if (v.includes('to')) {
      let range = v.split('to').map(Number);
      all.push(v);
      return; // If the value is a range, proceed to the next
    }

    let processedArray = computeAllArray(v);

    if(!processedArray) {
      hasIllegalValues = true;
    } else {
      all.push(...processedArray);
    }
  });

  // Log the source and target for a specific column
  if (col == 'PuPjump') {
    console.log('Column values: ', values);
    console.log('All: ', all);
  }

  return [ all, hasIllegalValues ];
}
function createHistogram(col, canvasId, data, totalRecords, hints = {}) {
  const histContainer = document.getElementById(canvasId);

  const hoverText = document.quizzinator.qtext || {};
  const text = hoverText[col] || hoverText[0];
  histContainer.innerHTML = text ?
    `<h2 title="${text}">${col}</h2>` :
    `<h2>${col}</h2>`;

  // create a canvas element inside histContainer, and provide it with a context '2d'
  const canvas = document.createElement('canvas');
  histContainer.appendChild(canvas);

  const ctx = canvas.getContext('2d');

  const myChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(data),
      datasets: [{
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
        data: Object.values(data)
      }]
    },
    options: {
      layout: {
        padding: {
          right: 10 // need so the right border of the grid is visible
        }
      },
      scales: {
        y: {
          suggestedMin: 0,
          grid: {
            drawBorder: true,
          }
        },
        x: {
          grid: {
            drawBorder: true,
          }
        }
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            title: function(tooltipItem) {
              var label = tooltipItem[0].label;
              var hint = hints[col][label];

              // If hint exists and is a number, round it to 1 decimal place
              if (hint && !isNaN(hint)) hint = parseFloat(hint).toFixed(1);

              return hint || (label + " = default");
            },
            label: function(context) {
              const percentage = context.parsed.y.toFixed(1);
              const commifiedTotalRecords = totalRecords.toLocaleString();
              return `${percentage}% of ${commifiedTotalRecords}`;  // Display as "42.3% [of 1,000]" for example
            }
          }
        }
      },
    }
  });
}