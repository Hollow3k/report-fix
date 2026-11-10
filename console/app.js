/* Report → Fix faculty console.
   Loads precomputed triage results (window.CONSOLE_DATA), renders the queue
   grouped by question in urgency order, and records faculty decisions in a
   per-case audit trail (in-browser for this demo build). */

(function () {
  const DATA = window.CONSOLE_DATA;
  const casesById = {};
  DATA.cases.forEach((c) => { casesById[c.reportId] = c; });

  const byQuestion = {};
  DATA.cases.forEach((c) => {
    (byQuestion[c.questionId] = byQuestion[c.questionId] || []).push(c);
  });

  const state = {}; // reportId -> {status, audit: [{at, action, note}]}
  DATA.cases.forEach((c) => {
    state[c.reportId] = {
      status: "pending",
      audit: [{
        at: "pipeline",
        action: "triaged",
        note: `${c.verdict}${c.repair ? " / " + c.repair : ""} · routed ${c.route.replace("_", " ")}`,
      }],
    };
  });

  let currentReport = null;
  let filter = "all";

  /* ---------- HTML sanitization ----------
     Question, solution and diff panes must render stored HTML + MathML, so
     escaping is not an option there. sanitizeHtml is an allowlist filter:
     it keeps the formatting tags the bank uses and the MathML vocabulary,
     drops executable/embed content (script, iframe, object, embed, svg,
     forms, media, ...) with its contents, unwraps any other unknown tag,
     removes every on* event-handler attribute, srcdoc, unsafe URL schemes
     (javascript:, vbscript:, data:, file:) in link-bearing attributes, and
     style values containing expression/url/import/binding constructs.
     Exposed on window so the live build can be verified directly. */
  const SANITIZE_DROP = new Set([
    "script", "style", "iframe", "object", "embed", "link", "meta", "base",
    "form", "input", "button", "textarea", "select", "option", "svg",
    "template", "frame", "frameset", "applet", "audio", "video", "source",
    "track", "canvas", "noscript", "maction", "annotation-xml",
  ]);
  const SANITIZE_ALLOW = new Set([
    // inline + block formatting the bank uses
    "h1", "h2", "h3", "h4", "p", "br", "hr", "b", "i", "em", "strong", "u",
    "s", "sub", "sup", "span", "div", "ol", "ul", "li", "blockquote",
    "code", "pre", "table", "thead", "tbody", "tr", "td", "th", "caption",
    // MathML vocabulary (no maction / annotation-xml - interactive/embed)
    "math", "mstyle", "mrow", "mi", "mo", "mn", "ms", "mtext", "mspace",
    "mfrac", "msqrt", "mroot", "msub", "msup", "msubsup", "munder",
    "mover", "munderover", "mtable", "mtr", "mtd", "mpadded", "mphantom",
    "menclose", "semantics", "annotation",
  ]);
  const SANITIZE_CSS_BAD = /expression|url\s*\(|javascript|vbscript|behavior|-moz-binding|@import/i;
  const SANITIZE_BAD_SCHEME = /^\s*(javascript|vbscript|data|file)\s*:/i;
  const SANITIZE_URL_ATTR = /^(href|src|xlink:href|formaction|action|poster|background|data)$/;

  function sanitizeHtml(html) {
    const doc = new DOMParser().parseFromString(String(html), "text/html");
    const root = document.createElement("div");
    const build = (src, dst) => {
      for (const node of [...src.childNodes]) {
        if (node.nodeType === 3) {
          dst.appendChild(document.createTextNode(node.nodeValue));
          continue;
        }
        if (node.nodeType !== 1) continue; // comments etc. dropped
        const tag = node.tagName.toLowerCase();
        if (SANITIZE_DROP.has(tag)) continue; // drop with contents
        if (!SANITIZE_ALLOW.has(tag)) { build(node, dst); continue; } // unwrap
        const el = document.createElement(tag);
        for (const attr of [...node.attributes]) {
          const name = attr.name.toLowerCase();
          const val = attr.value;
          if (name.startsWith("on") || name === "srcdoc") continue;
          if (name === "style") {
            if (!SANITIZE_CSS_BAD.test(val)) el.setAttribute("style", val);
            continue;
          }
          if (SANITIZE_URL_ATTR.test(name) && SANITIZE_BAD_SCHEME.test(val)) continue;
          el.setAttribute(attr.name, val);
        }
        build(node, el);
        dst.appendChild(el);
      }
    };
    build(doc.body, root);
    return root.innerHTML;
  }
  window.sanitizeHtml = sanitizeHtml; // exposed for live verification

  const $ = (id) => document.getElementById(id);

  /* ---------- header stats ---------- */
  function renderStats() {
    const counts = { faculty_review: 0, auto_apply: 0, no_change: 0 };
    DATA.cases.forEach((c) => counts[c.route]++);
    $("stats").innerHTML = `
      <div class="stat"><b>${counts.faculty_review}</b><span>need your review</span></div>
      <div class="stat" title="Triage route from the engine. This demo loads precomputed results and writes nothing to a production bank."><b>${counts.auto_apply}</b><span>auto-applied</span></div>
      <div class="stat"><b>${counts.no_change}</b><span>no change</span></div>`;
  }

  /* ---------- queue ---------- */
  function renderQueue() {
    const list = $("queueList");
    list.innerHTML = "";
    DATA.queueOrder.forEach((qid) => {
      const members = byQuestion[qid];
      if (filter !== "all" && !members.some((m) => m.route === filter)) return;
      const lead = members.find((m) => m.route === "faculty_review") || members[0];
      const done = members.every((m) => state[m.reportId].status !== "pending");
      const item = document.createElement("button");
      item.className = "queue-item" + (done ? " done" : "") +
        (members.some((m) => m.reportId === currentReport) ? " selected" : "");
      item.innerHTML = `
        <div class="qi-top">
          <span class="qi-chapter">${esc(lead.chapter)}</span>
          <span class="qi-count">${members.length} report${members.length > 1 ? "s" : ""}</span>
        </div>
        <div class="qi-sub">${esc(lead.subject)} · ${lead.questionType}</div>
        <div class="qi-chips">
          <span class="chip verdict-${lead.verdict}">${lead.verdict.replace("_", " ")}</span>
          <span class="chip route-${lead.route}">${lead.route.replace("_", " ")}</span>
        </div>`;
      item.onclick = () => selectReport(lead.reportId);
      list.appendChild(item);
    });
  }

  /* ---------- case view ---------- */
  function selectReport(rid) {
    currentReport = rid;
    const c = casesById[rid];
    $("emptyState").classList.add("hidden");
    $("caseView").classList.remove("hidden");

    const siblings = byQuestion[c.questionId];
    $("caseMeta").innerHTML = `
      <span><b>${esc(c.chapter)}</b></span>
      <span>${esc(c.subject)}</span>
      <span>${c.questionType}</span>
      <span>${c.level || "—"}</span>
      <span title="question id">${c.questionId.slice(-6)}</span>`;
    $("reportStrip").innerHTML = siblings.map((m) =>
      `<span class="rep ${m.reportId === rid ? "active" : ""}" data-rid="${m.reportId}">
        ${m.reportId}</span>`).join("") + ` · same question`;
    $("reportStrip").querySelectorAll(".rep").forEach((el) => {
      el.onclick = () => selectReport(el.dataset.rid);
    });

    $("questionBody").innerHTML = sanitizeHtml(c.questionHtml);
    const ans = Array.isArray(c.storedAnswer) ? c.storedAnswer.join(", ") : c.storedAnswer;
    $("storedAnswer").innerHTML = `Stored answer key: <b>${esc(String(ans))}</b>`;

    $("verdictChip").textContent = c.verdict.replace(/_/g, " ");
    $("verdictChip").className = "chip verdict-chip verdict-" + c.verdict;
    const rc = $("repairChip");
    if (c.repair) {
      rc.textContent = c.repair.replace(/_/g, " ");
      rc.title = c.repairLabel || "";
      rc.classList.remove("hidden");
    } else rc.classList.add("hidden");
    $("routeChip").textContent = c.route.replace(/_/g, " ");
    $("routeChip").className = "chip route-chip route-" + c.route;
    $("confidence").innerHTML = `confidence <b>${(c.confidence * 100).toFixed(0)}%</b>`;
    $("evidence").textContent = c.evidence;
    $("doubleProof").classList.toggle("hidden", !c.doubleProof);

    const dc = $("diffCard");
    if (c.diff) {
      dc.classList.remove("hidden");
      $("diffField").textContent = "· " + c.diff.field;
      renderDiffContent($("diffBefore"), c.diff.field, c.diff.before);
      renderDiffContent($("diffAfter"), c.diff.field, c.diff.after);
      document.querySelector("#diffCard .diff-pane.after h4").innerHTML =
        "After" + (c.diff.facultyEdited ? ' <span class="edited-badge">edited by faculty</span>' : "");
    } else if (c.repair) {
      dc.classList.remove("hidden");
      $("diffField").textContent = "";
      $("diffBefore").innerHTML = `<p>No safe automatic edit exists for this repair.</p>`;
      $("diffAfter").innerHTML = `<p>Needs a human: ${esc(c.repairLabel || c.repair)}</p>`;
      document.querySelector("#diffCard .diff-pane.after h4").textContent = "After";
    } else {
      dc.classList.add("hidden");
    }

    $("studentReply").textContent = c.studentReply;
    $("solutionBody").innerHTML = c.solutionHtml ? sanitizeHtml(c.solutionHtml) : "<em>No stored solution.</em>";

    const eh = $("errorHistoryCard");
    if (c.errorHistory && c.errorHistory.length) {
      eh.classList.remove("hidden");
      $("errorHistory").innerHTML = c.errorHistory.map((h) =>
        `<li><b>${esc(h.type)}</b> by ${esc(h.actor)} · ${esc(h.at)}<br>${esc(h.note)}</li>`).join("");
    } else eh.classList.add("hidden");

    renderActions(c);
    renderAudit(c);
    renderQueue();
    document.querySelector(".case").scrollTop = 0;
  }

  function renderDiffContent(el, field, value) {
    if (field === "question" || field === "solution") {
      el.innerHTML = sanitizeHtml(value); // stored HTML + MathML, sanitized
    } else {
      el.textContent = value;
    }
  }

  /* ---------- actions & audit ---------- */
  function renderActions(c) {
    const st = state[c.reportId];
    const decided = st.status !== "pending";
    $("btnApprove").disabled = decided;
    $("btnEdit").disabled = decided;
    $("btnReject").disabled = decided;
    $("actionStatus").textContent = decided ? `Decision recorded: ${st.status}` : "";

    $("btnApprove").onclick = () => decide(c, "approved");
    $("btnReject").onclick = () => decide(c, "rejected");
    $("btnEdit").onclick = () => openEdit(c);
  }

  function decide(c, action, note) {
    const st = state[c.reportId];
    st.status = action;
    st.audit.push({
      at: new Date().toLocaleString("en-IN", { hour12: false }),
      action,
      note: note || defaultNote(c, action),
    });
    renderActions(c);
    renderAudit(c);
    renderQueue();
  }

  function defaultNote(c, action) {
    if (action === "approved") {
      return c.route === "auto_apply"
        ? "faculty confirmed the auto-applied change"
        : c.route === "faculty_review"
          ? "faculty accepted the suggestion / verdict"
          : "faculty confirmed no change was needed";
    }
    if (action === "rejected") return "faculty disagreed with the triage; case stays open";
    return "";
  }

  function openEdit(c) {
    const modal = $("editModal");
    modal.classList.remove("hidden");
    $("editHint").textContent = c.diff
      ? `Editing the proposed "${c.diff.field}" replacement - the only field this repair may touch. Saving updates the After pane and records both versions in the audit trail.`
      : "No automatic edit exists for this case. Record the change you would make; applying it stays with faculty - authored content is never auto-written.";
    $("editArea").value = c.diff ? String(c.diff.after) : (c.edit ? JSON.stringify(c.edit, null, 2) : "");
    $("editSave").onclick = () => {
      const v = $("editArea").value.trim();
      if (c.diff) {
        if (!v) {
          $("editHint").textContent = "Replacement can not be empty for an auto-appliable fix - reject the case instead if the proposal is wrong.";
          return;
        }
        modal.classList.add("hidden");
        const orig = String(c.diff.after);
        if (v === orig) {
          decide(c, "approved", "faculty reviewed the proposed replacement unchanged");
          return;
        }
        c.diff.after = v;
        c.diff.facultyEdited = true;
        renderDiffContent($("diffAfter"), c.diff.field, c.diff.after);
        document.querySelector("#diffCard .diff-pane.after h4").innerHTML =
          'After <span class="edited-badge">edited by faculty</span>';
        const snip = (s) => (s.length > 100 ? s.slice(0, 100) + "…" : s);
        decide(c, "edited", `faculty changed ${c.diff.field}: "${snip(orig)}" -> "${snip(v)}"`);
      } else {
        modal.classList.add("hidden");
        decide(c, "edited", v.length > 220 ? v.slice(0, 220) + "…" : `faculty note (no auto-edit exists; applying stays with faculty): ${v}`);
      }
    };
    $("editCancel").onclick = () => modal.classList.add("hidden");
  }

  function renderAudit(c) {
    $("auditTrail").innerHTML = state[c.reportId].audit.map((a) =>
      `<li><span class="at-time">${esc(a.at)}</span>
        <span class="at-action ${a.action}">${esc(a.action)}</span>
        <span>${esc(a.note)}</span></li>`).join("");
  }

  /* ---------- filters & keys ---------- */
  $("filters").addEventListener("click", (e) => {
    if (!e.target.dataset.filter) return;
    filter = e.target.dataset.filter;
    document.querySelectorAll(".filter").forEach((b) => b.classList.toggle("active", b === e.target));
    renderQueue();
  });

  document.addEventListener("keydown", (e) => {
    if (!currentReport || e.target.tagName === "TEXTAREA") return;
    const c = casesById[currentReport];
    if (state[c.reportId].status !== "pending") return;
    if (e.key === "a" || e.key === "A") decide(c, "approved");
    if (e.key === "r" || e.key === "R") decide(c, "rejected");
    if (e.key === "e" || e.key === "E") openEdit(c);
  });

  function esc(s) {
    return String(s).replace(/[&<>"]/g, (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  }

  renderStats();
  renderQueue();
  // deep link: #R011 opens that case; otherwise open the most urgent one
  const openFromHash = () => {
    const id = location.hash.replace("#", "");
    if (id && casesById[id]) {
      selectReport(id);
      return true;
    }
    return false;
  };
  if (!openFromHash() && DATA.queueOrder.length) {
    const first = byQuestion[DATA.queueOrder[0]];
    selectReport((first.find((m) => m.route === "faculty_review") || first[0]).reportId);
  }
  // follow in-place hash changes (a link opened while the console is already up)
  window.addEventListener("hashchange", openFromHash);
})();
