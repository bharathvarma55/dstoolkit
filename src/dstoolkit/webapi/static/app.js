(() => {
  "use strict";

  const state = {
    sessionId: null,
    columns: [],
    columnInfo: [], // [{name, numeric}]
  };

  const $ = (id) => document.getElementById(id);

  // ---------- step navigation ----------

  function unlockStep(name) {
    document.querySelector(`.step[data-step="${name}"]`).disabled = false;
  }

  function goToStep(name) {
    document.querySelectorAll(".step").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.step === name);
    });
    document.querySelectorAll(".panel").forEach((panel) => {
      panel.classList.toggle("active", panel.id === `panel-${name}`);
    });
  }

  document.querySelectorAll(".step").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!btn.disabled) goToStep(btn.dataset.step);
    });
  });

  // ---------- shared helpers ----------

  function showError(elId, message) {
    $(elId).textContent = message || "";
  }

  async function api(path, options = {}) {
    const res = await fetch(path, options);
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch {
        /* ignore non-JSON error body */
      }
      throw new Error(detail);
    }
    return res.json();
  }

  function renderTable(containerId, preview) {
    const { columns, rows } = preview;
    const table = document.createElement("table");

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    columns.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((value) => {
        const td = document.createElement("td");
        if (value === null || value === undefined) {
          td.textContent = "null";
          td.className = "null";
        } else {
          td.textContent = String(value);
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    const container = $(containerId);
    container.innerHTML = "";
    container.appendChild(table);
  }

  function renderBadges(elId, preview) {
    $(elId).innerHTML = `
      <span class="badge">${preview.row_count} rows</span>
      <span class="badge">${preview.col_count} columns</span>
    `;
  }

  function applyPreview(preview, { tableId, badgesId }) {
    state.columns = preview.columns;
    renderTable(tableId, preview);
    renderBadges(badgesId, preview);
  }

  async function refreshColumnInfo() {
    const data = await api(`/api/sessions/${state.sessionId}/columns`);
    state.columnInfo = data.columns;
  }

  // ---------- step 1: upload ----------

  const dropzone = $("dropzone");
  const fileInput = $("file-input");

  $("browse-btn").addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("click", (e) => {
    if (e.target.id !== "browse-btn") fileInput.click();
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) uploadFile(fileInput.files[0]);
  });

  async function uploadFile(file) {
    showError("upload-error", "");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const data = await api("/api/sessions/upload", { method: "POST", body: formData });
      state.sessionId = data.session_id;
      applyPreview(data.preview, { tableId: "upload-table", badgesId: "upload-badges" });
      await refreshColumnInfo();
      $("upload-preview-card").hidden = false;
      unlockStep("clean");
    } catch (err) {
      showError("upload-error", err.message);
    }
  }

  $("to-clean-btn").addEventListener("click", () => goToStep("clean"));

  // ---------- step 2: clean ----------

  $("opt-missing").addEventListener("change", (e) => {
    $("constant-field").hidden = e.target.value !== "constant";
  });

  $("run-clean-btn").addEventListener("click", async () => {
    showError("clean-error", "");
    if (!state.sessionId) {
      showError("clean-error", "Upload a file first.");
      return;
    }
    const missingStrategy = $("opt-missing").value;
    const body = {
      dedupe: $("opt-dedupe").checked,
      missing_value_strategy: missingStrategy,
      string_normalize: $("opt-normalize").checked,
      outlier_strategy: $("opt-outlier").value,
    };
    if (missingStrategy === "constant") {
      body.missing_value_constant = $("opt-constant").value;
    }
    try {
      const data = await api(`/api/sessions/${state.sessionId}/clean`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const logEl = $("clean-log");
      logEl.innerHTML = data.cleaning_log.length
        ? data.cleaning_log.map((line) => `<div class="line">${escapeHtml(line)}</div>`).join("")
        : `<div class="line">No changes were needed.</div>`;
      $("clean-log-card").hidden = false;
      applyPreview(data.preview, { tableId: "clean-table", badgesId: "clean-badges" });
      await refreshColumnInfo();
      $("clean-preview-card").hidden = false;
      unlockStep("validate");
    } catch (err) {
      showError("clean-error", err.message);
    }
  });

  $("to-validate-btn").addEventListener("click", () => goToStep("validate"));

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------- step 3: validate ----------

  const RULE_TYPES = {
    not_null: { label: "Not null", params: ["max_null_rate"] },
    unique: { label: "Unique", params: [] },
    dtype: { label: "Data type", params: ["expected"] },
    range: { label: "Range", params: ["min", "max"] },
    allowed_values: { label: "Allowed values", params: ["values"] },
    regex: { label: "Regex match", params: ["pattern"] },
  };

  function ruleParamField(ruleType, param) {
    if (param === "expected") {
      return `
        <select data-param="expected">
          <option value="numeric">numeric</option>
          <option value="string">string</option>
          <option value="datetime">datetime</option>
          <option value="bool">bool</option>
        </select>`;
    }
    if (param === "max_null_rate") {
      return `<input type="number" data-param="max_null_rate" placeholder="max null rate (0-1)" min="0" max="1" step="0.05" value="0">`;
    }
    if (param === "min" || param === "max") {
      return `<input type="number" data-param="${param}" placeholder="${param}">`;
    }
    if (param === "values") {
      return `<input type="text" data-param="values" placeholder="comma-separated allowed values">`;
    }
    if (param === "pattern") {
      return `<input type="text" data-param="pattern" placeholder="regex pattern">`;
    }
    return "";
  }

  function addRuleRow() {
    const row = document.createElement("div");
    row.className = "rule-row";

    const typeOptions = Object.entries(RULE_TYPES)
      .map(([value, { label }]) => `<option value="${value}">${label}</option>`)
      .join("");
    const columnOptions = state.columns.map((c) => `<option value="${c}">${c}</option>`).join("");

    row.innerHTML = `
      <select data-role="type">${typeOptions}</select>
      <select data-role="column">${columnOptions}</select>
      <span class="params"></span>
      <button type="button" class="remove-rule" title="Remove rule">&times;</button>
    `;

    const typeSelect = row.querySelector('[data-role="type"]');
    const paramsSpan = row.querySelector(".params");

    function renderParams() {
      const spec = RULE_TYPES[typeSelect.value];
      paramsSpan.innerHTML = spec.params.map((p) => ruleParamField(typeSelect.value, p)).join("");
    }
    typeSelect.addEventListener("change", renderParams);
    renderParams();

    row.querySelector(".remove-rule").addEventListener("click", () => row.remove());

    $("rules-list").appendChild(row);
  }

  $("add-rule-btn").addEventListener("click", addRuleRow);

  function collectRules() {
    return Array.from(document.querySelectorAll("#rules-list .rule-row")).map((row) => {
      const type = row.querySelector('[data-role="type"]').value;
      const column = row.querySelector('[data-role="column"]').value;
      const params = {};
      row.querySelectorAll("[data-param]").forEach((input) => {
        const key = input.dataset.param;
        let value = input.value;
        if (value === "") return;
        if (key === "min" || key === "max" || key === "max_null_rate") {
          params[key] = Number(value);
        } else if (key === "values") {
          params.values = value.split(",").map((v) => v.trim()).filter(Boolean);
        } else {
          params[key] = value;
        }
      });
      return { type, column, params };
    });
  }

  $("run-validate-btn").addEventListener("click", async () => {
    showError("validate-error", "");
    if (!state.sessionId) {
      showError("validate-error", "Upload a file first.");
      return;
    }
    const rules = collectRules();
    try {
      const data = await api(`/api/sessions/${state.sessionId}/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rules }),
      });
      renderValidationResults(data);
      $("validate-results-card").hidden = false;
      unlockStep("report");
    } catch (err) {
      showError("validate-error", err.message);
    }
  });

  function renderValidationResults(data) {
    const summary = $("validate-summary");
    if (data.passed) {
      summary.innerHTML = `<span class="badge pass">ALL ${data.rules_evaluated} RULE(S) PASSED</span>`;
    } else {
      summary.innerHTML = `<span class="badge fail">${data.issues.length} ISSUE(S) FOUND</span>`;
    }

    const container = $("validate-table");
    if (!data.issues.length) {
      container.innerHTML = `<p class="muted" style="padding:16px;">No issues found.</p>`;
      return;
    }
    const table = document.createElement("table");
    table.innerHTML = `
      <thead><tr><th>Rule</th><th>Column</th><th>Message</th><th>Rows</th></tr></thead>
      <tbody>
        ${data.issues
          .map(
            (issue) => `
          <tr>
            <td>${escapeHtml(issue.rule)}</td>
            <td>${escapeHtml(issue.column)}</td>
            <td>${escapeHtml(issue.message)}</td>
            <td>${issue.affected_rows}</td>
          </tr>`
          )
          .join("")}
      </tbody>
    `;
    container.innerHTML = "";
    container.appendChild(table);
  }

  $("to-report-btn").addEventListener("click", () => goToStep("report"));

  // ---------- step 4: report ----------

  const CHART_TYPES = {
    histogram: { label: "Histogram", roles: ["column"], numericOnly: true },
    bar: { label: "Bar chart", roles: ["column"], numericOnly: false },
    box: { label: "Box plot", roles: ["column"], numericOnly: true },
    scatter: { label: "Scatter plot", roles: ["x", "y"], numericOnly: true },
    line: { label: "Line chart", roles: ["column"], numericOnly: true },
    pie: { label: "Pie chart", roles: ["column"], numericOnly: false },
    correlation: { label: "Correlation heatmap", roles: [], numericOnly: false },
    missingness: { label: "Missing values", roles: [], numericOnly: false },
  };

  function columnOptionsHtml(numericOnly) {
    const cols = numericOnly ? state.columnInfo.filter((c) => c.numeric) : state.columnInfo;
    if (!cols.length) return `<option value="">(no eligible columns)</option>`;
    return cols.map((c) => `<option value="${c.name}">${c.name}</option>`).join("");
  }

  function addChartRow(defaultType = "missingness") {
    const row = document.createElement("div");
    row.className = "rule-row";

    const typeOptions = Object.entries(CHART_TYPES)
      .map(
        ([value, { label }]) =>
          `<option value="${value}" ${value === defaultType ? "selected" : ""}>${label}</option>`
      )
      .join("");

    row.innerHTML = `
      <select data-role="type">${typeOptions}</select>
      <span class="cols"></span>
      <button type="button" class="remove-rule" title="Remove chart">&times;</button>
    `;

    const typeSelect = row.querySelector('[data-role="type"]');
    const colsSpan = row.querySelector(".cols");

    function renderCols() {
      const spec = CHART_TYPES[typeSelect.value];
      colsSpan.innerHTML = spec.roles
        .map((role) => `<select data-role="${role}">${columnOptionsHtml(spec.numericOnly)}</select>`)
        .join("");
    }
    typeSelect.addEventListener("change", renderCols);
    renderCols();

    row.querySelector(".remove-rule").addEventListener("click", () => row.remove());

    $("charts-list").appendChild(row);
  }

  $("add-chart-btn").addEventListener("click", () => addChartRow("histogram"));

  function collectCharts() {
    return Array.from(document.querySelectorAll("#charts-list .rule-row")).map((row) => {
      const type = row.querySelector('[data-role="type"]').value;
      const spec = CHART_TYPES[type];
      const params = {};
      spec.roles.forEach((role) => {
        const select = row.querySelector(`[data-role="${role}"]`);
        if (select && select.value) params[role] = select.value;
      });
      return { type, params };
    });
  }

  $("generate-report-btn").addEventListener("click", async () => {
    showError("report-error", "");
    if (!state.sessionId) {
      showError("report-error", "Upload a file first.");
      return;
    }
    try {
      await api(`/api/sessions/${state.sessionId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: $("report-title").value || "Data Science Report",
          charts: collectCharts(),
        }),
      });
      const base = `/api/sessions/${state.sessionId}/report`;
      $("report-frame").src = `${base}/html`;
      $("download-html-btn").href = `${base}/html?download=true`;
      $("download-pdf-btn").href = `${base}/pdf?download=true`;
      $("report-preview-card").hidden = false;
    } catch (err) {
      showError("report-error", err.message);
    }
  });

  // seed one empty row in each builder so the validate/report steps aren't blank
  addRuleRow();
  addChartRow("missingness");
})();
