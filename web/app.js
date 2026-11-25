const state = { data: null, year: "2026", query: "", month: "", unit: "", energy: "", showZero: false };
const energyOrder = ["电力", "汽油", "柴油", "天然气", "热力", "生活热水", "自来水", "中水", "冷量"];
const $ = (selector) => document.querySelector(selector);
const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
const num = (value) => value === null || value === undefined || value === "" ? "—" : Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
const category = (value) => String(value || "").split(/[（(]/)[0].trim();
const monthColors = ["#dce8ff", "#ffe5cb", "#c9f1fb", "#fff0bd", "#c9f3e8", "#ffe1df", "#eee3ff", "#d8f4d8", "#ffdfef", "#e8f4a5", "#eeeeee", "#dce8ff"];
const unitColors = ["#dce8ff", "#ffe5cb", "#c9f1fb", "#dff1c9", "#eee3ff", "#ffdfef"];
const energyColors = {"电力":"#dce8ff", "汽油":"#ffe5cb", "柴油":"#ffe5cb", "天然气":"#fff0bd", "热力":"#c9f3ec", "生活热水":"#d9f4d4", "自来水":"#eee3ff", "中水":"#ffdfef", "冷量":"#d7f1fb"};
const monthStyle = (month) => { const index = Math.max(0, Number.parseInt(String(month).match(/\d+/)?.[0] || "1", 10) - 1) % monthColors.length; return `--tag-bg:${monthColors[index]}`; };
const unitStyle = (unit) => { const order = state.unit_order || []; const index = order.indexOf(unit); return `--tag-bg:${unitColors[(index < 0 ? 0 : index) % unitColors.length]}`; };
const energyStyle = (value) => `--tag-bg:${energyColors[category(value)] || "#e9efea"}`;

function statusBadge(check) {
  if (!check || check.status === "unavailable") return '<span class="badge na">无数据</span>';
  return `<span class="badge ${check.status === "一致" ? "ok" : "bad"}">${safe(check.status)}</span>`;
}
function pair(computed, check) {
  return `<div class="pair"><span class="computed">${num(computed)}</span><span class="divider">/</span><span class="reported">${num(check?.reported)}</span></div>`;
}
function sumValues(rows, key) {
  const computedValues = rows.map((row) => row._computed?.[key]).filter((value) => Number.isFinite(value));
  const reportedValues = rows.map((row) => row._checks?.[key]?.reported).filter((value) => Number.isFinite(value));
  return pair(computedValues.length ? computedValues.reduce((total, value) => total + value, 0) : null,
    { reported: reportedValues.length ? reportedValues.reduce((total, value) => total + value, 0) : null });
}
function updateFilters() {
  const allRows = Object.values(state.data.sheets || {}).flat();
  const monthSelect = $("#month-filter"), unitSelect = $("#unit-filter"), energySelect = $("#energy-filter");
  const selectedMonth = state.month, selectedUnit = state.unit, selectedEnergy = state.energy;
  const months = [...new Set(allRows.map((row) => row["月份"]).filter(Boolean))];
  const units = [...new Set(allRows.map((row) => row["三级单位"]).filter(Boolean))];
  const types = [...new Set(allRows.map((row) => row["能源类型"]).filter(Boolean))];
  months.sort((a, b) => Number.parseInt(String(a).match(/\d+/)?.[0] || "999", 10) - Number.parseInt(String(b).match(/\d+/)?.[0] || "999", 10));
  const unitOrder = state.unit_order || [];
  units.sort((a, b) => unitOrder.indexOf(a) - unitOrder.indexOf(b));
  const configuredOrder = state.data.energy_type_order || energyOrder;
  types.sort((a, b) => configuredOrder.indexOf(category(a)) - configuredOrder.indexOf(category(b)));
  monthSelect.innerHTML = '<option value="">全部</option>' + months.map((value) => `<option value="${safe(value)}">${safe(value)}</option>`).join("");
  unitSelect.innerHTML = '<option value="">全部单位</option>' + units.map((value) => `<option value="${safe(value)}">${safe(value)}</option>`).join("");
  energySelect.innerHTML = '<option value="">全部能源</option>' + types.map((value) => `<option value="${safe(value)}">${safe(value)}</option>`).join("");
  monthSelect.value = months.includes(selectedMonth) ? selectedMonth : "";
  unitSelect.value = units.includes(selectedUnit) ? selectedUnit : "";
  energySelect.value = types.includes(selectedEnergy) ? selectedEnergy : "";
}
function sortRows(rows) {
  const units = [...new Set(rows.map((row) => row["三级单位"] || "未填写"))];
  const unitOrder = state.data.unit_order?.length ? state.data.unit_order : units;
  const unitIndex = (unit) => { const index = unitOrder.indexOf(unit); return index < 0 ? unitOrder.length + units.indexOf(unit) : index; };
  return [...rows].sort((a, b) => unitIndex(a["三级单位"] || "未填写") - unitIndex(b["三级单位"] || "未填写") ||
    (energyOrder.indexOf(category(a["能源类型"])) < 0 ? 999 : energyOrder.indexOf(category(a["能源类型"]))) - (energyOrder.indexOf(category(b["能源类型"])) < 0 ? 999 : energyOrder.indexOf(category(b["能源类型"]))) || Number(a._row) - Number(b._row));
}
function render() {
  if (!state.data) return;
  const all = state.data.sheets[state.year] || [];
  const query = state.query.trim().toLowerCase();
  const visible = all.filter((row) => {
    const coal = row._computed || {};
    const zeroCoal = Number(coal.coal_self) === 0 && Number(coal.coal_total) === 0;
    return (state.showZero || !zeroCoal) && (!state.month || row["月份"] === state.month) && (!state.unit || row["三级单位"] === state.unit) &&
      (!state.energy || row["能源类型"] === state.energy) &&
      (!query || `${row["三级单位"] || ""} ${row["能源类型"] || ""} ${row["月份"] || ""}`.toLowerCase().includes(query));
  });
  const monthMap = new Map();
  visible.forEach((row) => { const month = row["月份"] || "未注明月份"; if (!monthMap.has(month)) monthMap.set(month, []); monthMap.get(month).push(row); });
  let html = "";
  const months = [...monthMap.entries()].sort((a, b) => {
    const monthNumber = (value) => Number.parseInt(String(value).match(/\d+/)?.[0] || "999", 10);
    return monthNumber(a[0]) - monthNumber(b[0]);
  });
  for (const [month, rows] of months) {
    html += `<tr class="month-row"><td colspan="11"><span class="month-pill color-tag" style="${monthStyle(month)}">${safe(month)}</span><span class="month-count">${rows.length} 条记录</span></td></tr>`;
    sortRows(rows).forEach((row, index) => {
      const c = row._computed || {}, k = row._checks || {};
      const checks = [k.coal_self, k.coal_total, k.co2_self, k.co2_total];
      const issues = checks.filter((item) => item && item.status === "不一致").length;
      const status = issues ? `<span class="badge bad">${issues} 项待核</span>` : checks.every((item) => item?.status === "一致") ? '<span class="badge ok">全部一致</span>' : '<span class="badge na">部分无数据</span>';
      const unit = row["三级单位"] || "未填写";
      html += `<tr><td class="row-number">${index + 1}</td><td><span class="month-pill color-tag" style="${monthStyle(month)}">${safe(month)}</span></td><td><span class="unit-pill color-tag" style="${unitStyle(unit)}" title="${safe(unit)}">${safe(unit)}</span></td><td><span class="energy-pill color-tag" style="${energyStyle(row["能源类型"])}">${safe(row["能源类型"])}</span></td><td class="num">${num(row["自用实物量"])}</td><td class="num">${num(row["总实物量"])}</td><td>${pair(c.coal_self, k.coal_self)}</td><td>${pair(c.coal_total, k.coal_total)}</td><td>${pair(c.co2_self, k.co2_self)}</td><td>${pair(c.co2_total, k.co2_total)}</td><td><div class="check-group">${status}</div></td></tr>`;
    });
    html += `<tr class="month-summary"><td colspan="4">${safe(month)} 汇总 <small>（当前显示 ${rows.length} 条）</small></td><td class="num">—</td><td class="num">—</td><td>${sumValues(rows, "coal_self")}</td><td>${sumValues(rows, "coal_total")}</td><td>${sumValues(rows, "co2_self")}</td><td>${sumValues(rows, "co2_total")}</td><td></td></tr>`;
  }
  $("#rows").innerHTML = html;
  $("#empty").hidden = visible.length > 0;
  $("#record-count").textContent = visible.length.toLocaleString("zh-CN");
  $("#issue-count").textContent = visible.filter((row) => Object.values(row._checks || {}).some((item) => item.status === "不一致")).length.toLocaleString("zh-CN");
  $("#tolerance").textContent = `${(state.data.tolerance_relative * 100).toLocaleString("zh-CN")}％`;
  $("#footer-count").textContent = `${visible.length} 条记录`;
}
async function load() {
  const status = $("#status"); status.classList.remove("error"); status.textContent = "正在读取工作簿并核算…";
  try {
    const response = await fetch("/api/results", { cache: "no-store" });
    if (!response.ok) throw new Error((await response.text()).replace(/<[^>]*>/g, " ").trim());
    state.data = await response.json();
    if (state.data.energy_type_order?.length) energyOrder.splice(0, energyOrder.length, ...state.data.energy_type_order);
    state.unit_order = state.data.unit_order || [];
    updateFilters();
    status.textContent = `已载入 ${state.data.source_name || "工作簿"} · ${state.data.tolerance_relative * 100}% 相对误差阈值`;
    render();
  } catch (error) { status.classList.add("error"); status.textContent = `读取失败：${error.message}`; }
}
document.querySelectorAll(".sheet-tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".sheet-tab").forEach((item) => { item.classList.toggle("active", item === tab); item.setAttribute("aria-selected", item === tab ? "true" : "false"); });
  state.year = tab.dataset.year; render();
}));
$("#search").addEventListener("input", (event) => { state.query = event.target.value; render(); });
$("#month-filter").addEventListener("change", (event) => { state.month = event.target.value; render(); });
$("#unit-filter").addEventListener("change", (event) => { state.unit = event.target.value; render(); });
$("#energy-filter").addEventListener("change", (event) => { state.energy = event.target.value; render(); });
$("#show-zero").addEventListener("change", (event) => { state.showZero = event.target.checked; render(); });
$("#refresh").addEventListener("click", load);
load();
