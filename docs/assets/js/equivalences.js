(function () {
  const tbody = document.getElementById("equiv-body");
  if (!tbody) return;

  const typeEl = document.getElementById("equiv-type-filter");
  const countEl = document.getElementById("equiv-count");
  const byId = Object.fromEntries(PROVERBS.map((p) => [p.id, p]));

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function short(p) {
    if (!p) return "";
    return `${p.id} <span class="tag">${p.lang}</span> — “${escapeHtml(p.text)}”`;
  }

  function populateFilter() {
    const types = [...new Set(EQUIVALENCES.map((e) => e.type))].sort();
    for (const t of types) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      typeEl.appendChild(opt);
    }
  }

  function render() {
    const type = typeEl.value;
    const rows = EQUIVALENCES.filter((e) => !type || e.type === type);
    countEl.textContent = `${rows.length} of ${EQUIVALENCES.length} equivalence links`;

    tbody.innerHTML = rows
      .map(
        (e) => `
      <tr>
        <td>${short(byId[e.a])}</td>
        <td>${short(byId[e.b])}</td>
        <td><span class="tag">${escapeHtml(e.type)}</span></td>
        <td>${escapeHtml(e.note)}</td>
      </tr>`
      )
      .join("");
  }

  populateFilter();
  render();
  typeEl.addEventListener("change", render);
})();
