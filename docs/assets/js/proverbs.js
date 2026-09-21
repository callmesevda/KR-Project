(function () {
  const tbody = document.getElementById("proverb-body");
  const searchEl = document.getElementById("search");
  const langEl = document.getElementById("lang-filter");
  const lessonEl = document.getElementById("lesson-filter");
  const countEl = document.getElementById("result-count");

  const LANG_NAMES = { en: "English", fa: "Farsi", ita: "Italian", alb: "Albanian" };

  function populateFilters() {
    const langs = [...new Set(PROVERBS.map((p) => p.lang))].sort();
    const lessons = [...new Set(PROVERBS.map((p) => p.lesson))].sort();
    for (const l of langs) {
      const opt = document.createElement("option");
      opt.value = l;
      opt.textContent = LANG_NAMES[l] || l;
      langEl.appendChild(opt);
    }
    for (const l of lessons) {
      const opt = document.createElement("option");
      opt.value = l;
      opt.textContent = l;
      lessonEl.appendChild(opt);
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function render() {
    const q = searchEl.value.trim().toLowerCase();
    const lang = langEl.value;
    const lesson = lessonEl.value;

    const rows = PROVERBS.filter((p) => {
      if (lang && p.lang !== lang) return false;
      if (lesson && p.lesson !== lesson) return false;
      if (q) {
        const hay = `${p.text} ${p.translation} ${p.situation} ${p.domain}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    countEl.textContent = `${rows.length} of ${PROVERBS.length} proverbs`;

    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7">No proverbs match these filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows
      .map(
        (p) => `
      <tr>
        <td><code>${escapeHtml(p.id)}</code></td>
        <td><span class="tag">${escapeHtml(LANG_NAMES[p.lang] || p.lang)}</span></td>
        <td lang="${escapeHtml(p.lang)}">${escapeHtml(p.text)}</td>
        <td>${escapeHtml(p.translation)}</td>
        <td>${escapeHtml(p.domain)}</td>
        <td>${escapeHtml(p.lesson)}</td>
        <td>${escapeHtml(p.situation)}</td>
      </tr>`
      )
      .join("");
  }

  populateFilters();
  render();
  searchEl.addEventListener("input", render);
  langEl.addEventListener("change", render);
  lessonEl.addEventListener("change", render);
})();
