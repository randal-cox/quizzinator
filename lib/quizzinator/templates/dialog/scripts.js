window.addEventListener("DOMContentLoaded", () => {
  const dialog    = document.quizzinator.dialog || [];
  const meta      = document.quizzinator.meta || {};
  const tbodyMeta = document.querySelector("#quiz-meta-table tbody");
  const tbodyDia  = document.querySelector("#quizzinator_dialog tbody");
  const modelName = meta.model || "unknown model";

  // Inject Run Details
  if (meta) {
    const current = meta.index;
    const total   = meta.size;
    let started;
    try {
      const dt  = new Date(meta.start);
      const z   = n => String(n).padStart(2, '0');
      started = `${dt.getFullYear()}-${z(dt.getMonth()+1)}-${z(dt.getDate())}`
              + ` ${z(dt.getHours())}:${z(dt.getMinutes())}:${z(dt.getSeconds())}`;
    } catch { started = meta.start; }
    const mins = Math.floor(meta.duration/60);
    const secs = Math.floor(meta.duration%60);
    const dur  = `${mins}m ${secs}s`;

    [["Quiz", `${current} of ${total}`],
     ["Started", started],
     ["Duration", dur],
     ["Model", meta.model]
    ].forEach(([label, value]) => {
      const tr = document.createElement("tr");
      const td1 = document.createElement("td"); td1.textContent = label;
      const td2 = document.createElement("td"); td2.textContent = value;
      tr.append(td1, td2);
      tbodyMeta.appendChild(tr);
    });
  }

  // Compute final answers
  const finalAns = {};
  dialog.forEach(e => {
    const num = e.answer?.number;
    const ans = e.answer?.answer;
    if (num != null && ans != null) finalAns[num] = String(ans);
  });

  // Determine distinct questions and order
  const questionNumbers = [...new Set(
    dialog.map(e => e.answer?.number).filter(n => n != null)
  )];
  const totalQuestions = questionNumbers.length;

  // Render Dialog
  let lastQ = null;
  dialog.forEach(entry => {
    const qnum = entry.answer?.number ?? 0;
    let qname  = (entry.answer?.name || "").replace(/^_/, '');
    const displayIdx = questionNumbers.indexOf(qnum) + 1;
    const tr   = document.createElement("tr");
    tr.className = (displayIdx % 2 === 0) ? "even" : "odd";

    // Question column
    const tdQ = document.createElement("td");
    if (qnum !== lastQ) {
      const h1 = document.createElement("h1"); h1.textContent = qname;
      const div = document.createElement("div"); div.textContent = `Question ${displayIdx} of ${totalQuestions}`;
      tdQ.append(h1, div);
      const fa = finalAns[qnum];
      if (fa != null) {
        const p = document.createElement("p");
        const strong = document.createElement("strong"); strong.textContent = "Answer: ";
        const preview = fa.length>20?fa.slice(0,20)+"…":fa;
        p.append(strong, document.createTextNode(preview));
        if (fa.length>20) { p.classList.add("tooltip"); p.dataset.tooltip = fa; }
        tdQ.appendChild(p);
      }
      lastQ = qnum;
    }
    tr.appendChild(tdQ);

    // Speaker column
    const tdS = document.createElement("td");
    const icon = document.createElement("i"); icon.classList.add("tooltip");
    if (entry.role === "user") {
      icon.classList.add("fa-solid","fa-chalkboard-user");
      icon.dataset.tooltip = "Quizzinator administering the quiz";
    } else {
      icon.classList.add("fa-solid","fa-robot");
      icon.dataset.tooltip = `AI running ${modelName}`;
    }
    tdS.appendChild(icon);
    tr.appendChild(tdS);

    // Content column
    const tdC = document.createElement("td");
    if (entry.role==="llm" && entry.think) {
      const thinkIcon = document.createElement("i");
      thinkIcon.className = "fa-solid fa-comment tooltip";
      thinkIcon.dataset.tooltip = entry.think;
      tdC.appendChild(thinkIcon);
    }
    (entry.content||"")
      .split(/\r?\n\s*\r?\n/)
      .forEach(para => {
        const p = document.createElement("p");
        p.textContent = para.replace(/\r?\n/, " ");
        tdC.appendChild(p);
      });

    tr.appendChild(tdC);
    tbodyDia.appendChild(tr);
  });
});