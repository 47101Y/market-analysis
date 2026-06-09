import pandas as pd
from pyecharts.charts import Bar, Pie, Timeline, Page
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from collections import defaultdict
from pyecharts.globals import CurrentConfig
import json
import re
from pathlib import Path


CurrentConfig.ONLINE_HOST = "https://assets.pyecharts.org/assets/v5/"


def build_wide_from_future(future_df):
    """将 new_stock_future_10days.csv 长表转为 wide_stock_data 宽表（原 wide_stock_data.py 逻辑）。"""
    df = future_df.copy()
    df['day_seq'] = df['day_seq'].astype(int)
    df = df.sort_values(['add_date', 'name', 'stock', 'industry', 'day_seq'])

    def _col_suffix(day_seq):
        return str(day_seq) if day_seq != 0 else ''

    df['open_col'] = df['day_seq'].apply(lambda d: f'open{_col_suffix(d)}')
    df['close_col'] = df['day_seq'].apply(lambda d: f'close{_col_suffix(d)}')
    df['pct_col'] = df['day_seq'].apply(lambda d: f'today_pct{_col_suffix(d)}')

    index_cols = ['add_date', 'name', 'stock', 'industry']
    df_open = df.pivot_table(
        index=index_cols, columns='open_col', values='open', aggfunc='first',
    ).reset_index()
    df_close = df.pivot_table(
        index=index_cols, columns='close_col', values='close', aggfunc='first',
    ).reset_index()
    df_pct = df.pivot_table(
        index=index_cols, columns='pct_col', values='today_pct', aggfunc='first',
    ).reset_index()

    df_merged = pd.merge(df_open, df_close, on=index_cols, how='left')
    df_merged = pd.merge(df_merged, df_pct, on=index_cols, how='left')

    dynamic_cols = []
    for i in range(11):
        suffix = str(i) if i != 0 else ''
        dynamic_cols.extend([f'open{suffix}', f'close{suffix}', f'today_pct{suffix}'])
    final_cols = index_cols + [c for c in dynamic_cols if c in df_merged.columns]
    return df_merged[final_cols]


_MONEY_WATCHLIST_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>新增板块3/5/10/20日成交额汇总</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    * { box-sizing: border-box; }
    html, body {
      margin: 0; padding: 0;
      background: #111; color: #fff;
      font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.5; overflow-x: hidden;
    }
    .page { padding: 16px 20px 32px; max-width: 1500px; margin: 0 auto; }
    .section-intro {
      padding: 15px 20px; color: #8b9cb3;
      background: #1a1a1a; border-radius: 10px;
      margin-bottom: 14px; line-height: 1.7; font-size: 14px;
    }
    .section-intro h2 { margin: 0 0 8px; color: #ffd666; font-size: 20px; }
    .toolbar {
      display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
      margin-bottom: 14px;
    }
    label { color: #8b9cb3; font-size: 14px; }
    select, input {
      background: #333; border: 1px solid #444; color: #fff;
      padding: 8px 10px; border-radius: 6px; font-size: 14px;
    }
    .filter-btns { display: flex; gap: 8px; flex-wrap: wrap; }
    .filter-btns button {
      background: #333; color: #fff; border: none;
      border-radius: 8px; padding: 10px 16px; cursor: pointer; font-size: 14px;
    }
    .filter-btns button:hover { background: #555; }
    .filter-btns button.active {
      background: rgba(255, 214, 102, 0.15);
      box-shadow: inset 0 0 0 1px #ffd666; color: #ffd666;
    }
    .stats {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 10px; margin-bottom: 14px;
    }
    .stat {
      background: #1f1f1f; border: 1px solid #333;
      border-radius: 8px; padding: 10px 14px;
    }
    .stat label { display: block; color: #8b9cb3; font-size: 12px; }
    .stat span { font-size: 17px; font-weight: 600; color: #fff; }
    .card {
      background: #1f1f1f; border: 1px solid #333;
      border-radius: 10px; padding: 16px; margin-bottom: 14px;
    }
    .card h2 { margin: 0 0 10px; font-size: 16px; color: #ffd666; font-weight: 600; }
    .hint { font-size: 13px; color: #8b9cb3; margin: 0 0 10px; }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 960px) { .grid2 { grid-template-columns: 1fr; } }
    .chart-box { height: 280px; position: relative; }
    .chart-empty {
      position: absolute; inset: 0; display: none;
      align-items: center; justify-content: center;
      color: #8b9cb3; font-size: 15px; text-align: center;
      padding: 20px; background: rgba(17, 17, 17, 0.85);
    }
    .table-wrap {
      max-height: 55vh; overflow: auto;
      border-radius: 8px; border: 1px solid #333;
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 8px 10px; border-bottom: 1px solid #333; text-align: right; }
    th {
      background: #333; color: #8b9cb3; font-weight: 500;
      position: sticky; top: 0; z-index: 2;
    }
    th.left, td.left { text-align: left; }
    tr:hover { background: rgba(255, 214, 102, 0.06); }
    tr.sel { background: rgba(255, 214, 102, 0.12); }
    .detail-card {
      border: 1px solid #333; border-radius: 10px; overflow: hidden;
    }
    .detail-head {
      padding: 12px 14px; border-bottom: 1px solid #333;
      display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;
      background: #1a1a1a;
    }
    .detail-name { font-weight: 600; color: #ffd666; }
    .detail-code { color: #8b9cb3; font-family: Consolas, monospace; font-size: 13px; }
    .badge {
      font-size: 12px; padding: 2px 8px; border-radius: 4px;
      background: rgba(255, 214, 102, 0.15); color: #ffd666;
    }
    .empty { text-align: center; padding: 24px; color: #8b9cb3; }
  </style>
</head>
<body>
<div class="page">
  <div class="section-intro">
    <h2 id="pageTitle">新增板块3/5/10/20日成交额汇总</h2>
    <p id="pageSub" class="hint" style="margin:0;color:#8b9cb3;"></p>
  </div>

  <div class="toolbar">
    <label>信号日 T <select id="dateSelect"></select></label>
    <label>搜索 <input id="searchInput" placeholder="代码 / 名称" style="min-width:140px"/></label>
    <div class="filter-btns" id="winBtns">
      <button type="button" class="active" data-win="1">1日汇总</button>
      <button type="button" data-win="3">3日汇总</button>
      <button type="button" data-win="5">5日汇总</button>
      <button type="button" data-win="10">10日汇总</button>
      <button type="button" data-win="20">20日汇总</button>
    </div>
  </div>

  <div class="stats" id="stats"></div>

  <div class="grid2">
    <div class="card">
      <h2>当日汇总对比（亿元）</h2>
      <p class="hint">所选信号日各新进股的 N 日成交额合计</p>
      <div class="chart-box">
        <canvas id="barChart"></canvas>
        <div class="chart-empty" id="barChartEmpty"></div>
      </div>
    </div>
    <div class="card">
      <h2>当日合计走势（亿元）</h2>
      <p class="hint">当日全部新进股逐日成交额之和（T=第0日）</p>
      <div class="chart-box"><canvas id="lineChart"></canvas></div>
    </div>
  </div>

  <div class="card">
    <h2>汇总表 · 点击行查看逐日明细</h2>
    <p class="hint">单位：亿元。1日=T日成交额；sum_Nd = 从 T 日起连续 N 个交易日成交额之和（含 T 日）</p>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="left">名称</th>
            <th class="left">代码</th>
            <th>T日</th>
            <th>3日</th>
            <th>5日</th>
            <th>10日</th>
            <th>20日</th>
            <th>可追踪</th>
          </tr>
        </thead>
        <tbody id="summaryBody"></tbody>
      </table>
    </div>
  </div>

  <div class="card" id="detailCard" style="display:none">
    <h2 id="detailTitle">逐日明细</h2>
    <div id="detailContent"></div>
  </div>
</div>

<script>
const DATA = __PAYLOAD__;
const meta = DATA.meta || {};
const byDate = DATA.byDate || {};
const dates = DATA.dates || [];

document.getElementById("pageTitle").textContent =
  meta.title || "新增板块3/5/10/20日成交额汇总";
document.getElementById("pageSub").textContent =
  "信号日 " + (meta.signal_days || dates.length) + " 个 · 新进条目 "
  + (meta.total_entries || 0) + " 条 · 汇总窗口 "
  + (meta.roll_windows || [1, 3, 5, 10, 20]).join("/") + " 交易日 · 数据 "
  + (meta.backtest_start || "") + " ~ " + (meta.last_signal_date || "");

const dateSelect = document.getElementById("dateSelect");
const searchInput = document.getElementById("searchInput");
const summaryBody = document.getElementById("summaryBody");
const statsEl = document.getElementById("stats");
const detailCard = document.getElementById("detailCard");
const detailTitle = document.getElementById("detailTitle");
const detailContent = document.getElementById("detailContent");

let activeWin = 1;
let selectedCode = null;
let barChart = null;
let lineChart = null;

function fmt(v) {
  if (v == null || v === "" || Number.isNaN(v)) return "暂无";
  return Number(v).toFixed(2);
}

function observedDays(stock) {
  const last = meta.last_signal_date || "";
  const daily = stock.daily || [];
  if (!daily.length) return stock.track_days || 0;
  if (!last) return daily.length;
  let n = 0;
  for (let i = 0; i < daily.length; i++) {
    if (daily[i].date > last) break;
    n++;
  }
  return n;
}

function canComputeWin(stock, win) {
  if (win === 1) return stock.money_t_yi != null && stock.money_t_yi !== "";
  const key = yiKey(win);
  return observedDays(stock) >= win && stock[key] != null;
}

function fmtWin(stock, win) {
  if (!canComputeWin(stock, win)) return "暂无";
  if (win === 1) return fmt(stock.money_t_yi);
  return fmt(stock[yiKey(win)]);
}

function yiKey(win) {
  if (win === 1) return "money_t_yi";
  return "sum_" + win + "d_yi";
}

function currentStocks() {
  const d = dateSelect.value;
  const block = byDate[d] || { stocks: [] };
  const q = (searchInput.value || "").trim().toLowerCase();
  return (block.stocks || []).filter(function (s) {
    if (!q) return true;
    return (s.code || "").toLowerCase().indexOf(q) >= 0
      || (s.name || "").toLowerCase().indexOf(q) >= 0;
  });
}

function fillDates() {
  dateSelect.innerHTML = "";
  dates.forEach(function (d) {
    const n = (byDate[d] && byDate[d].stocks) ? byDate[d].stocks.length : 0;
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = n ? (d + "（" + n + " 只）") : (d + "（无新进）");
    dateSelect.appendChild(opt);
  });
  if (dates.length) dateSelect.value = dates[dates.length - 1];
}

function renderStats(stocks) {
  const cnt = stocks.length;
  const avgT = cnt ? stocks.reduce(function (a, s) { return a + (s.money_t_yi || 0); }, 0) / cnt : 0;
  const key = yiKey(activeWin);
  const valid = stocks.filter(function (s) { return canComputeWin(s, activeWin); });
  let avgSumText, totalSumText;
  if (activeWin > 1 && valid.length === 0) {
    avgSumText = "暂无";
    totalSumText = "暂无";
  } else {
    const avgSum = valid.length
      ? valid.reduce(function (a, s) { return a + s[key]; }, 0) / valid.length
      : 0;
    const totalSum = valid.reduce(function (a, s) { return a + s[key]; }, 0);
    avgSumText = fmt(avgSum) + " 亿";
    totalSumText = fmt(totalSum) + " 亿";
  }
  const rows = [
    ["当日新进", cnt + " 只"],
    ["T日成交额均值", fmt(avgT) + " 亿"],
    [activeWin + "日汇总均值", avgSumText],
    [activeWin + "日汇总合计", totalSumText],
    ["可算" + activeWin + "日", valid.length + " 只"],
  ];
  statsEl.innerHTML = rows.map(function (pair) {
    return '<div class="stat"><label>' + pair[0] + '</label><span>' + pair[1] + '</span></div>';
  }).join("");
}

function renderSummary(stocks) {
  summaryBody.innerHTML = stocks.map(function (s) {
    const sel = s.code === selectedCode ? "sel" : "";
    return '<tr class="' + sel + '" data-code="' + s.code + '">'
      + '<td class="left">' + (s.name || "—") + '</td>'
      + '<td class="left">' + s.code + '</td>'
      + '<td>' + fmt(s.money_t_yi) + '</td>'
      + '<td>' + fmtWin(s, 3) + '</td>'
      + '<td>' + fmtWin(s, 5) + '</td>'
      + '<td>' + fmtWin(s, 10) + '</td>'
      + '<td>' + fmtWin(s, 20) + '</td>'
      + '<td>' + observedDays(s) + ' 日</td></tr>';
  }).join("") || '<tr><td colspan="8" class="empty">无数据</td></tr>';

  summaryBody.querySelectorAll("tr[data-code]").forEach(function (tr) {
    tr.addEventListener("click", function () {
      selectedCode = tr.dataset.code;
      renderSummary(stocks);
      renderDetail(stocks.find(function (x) { return x.code === selectedCode; }));
    });
  });
}

function renderDetail(stock) {
  if (!stock || !stock.daily || !stock.daily.length) {
    detailCard.style.display = "none";
    return;
  }
  detailCard.style.display = "block";
  detailTitle.textContent = "【" + stock.name + "】" + stock.code + " · 逐日成交额（亿元）";
  const rows = stock.daily.map(function (d) {
    return '<tr><td class="left">第 ' + d.day + ' 日</td><td class="left">' + d.date
      + '</td><td>' + fmt(d.money_yi) + '</td></tr>';
  }).join("");
  detailContent.innerHTML =
    '<div class="detail-card"><div class="detail-head">'
    + '<span class="detail-name">' + stock.name + '</span>'
    + '<span class="detail-code">' + stock.code + '</span>'
    + '<span class="badge">T=' + stock.entry_date + '</span></div>'
    + '<table><thead><tr><th class="left">序</th><th class="left">日期</th><th>成交额(亿)</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table></div>';
}

function aggregateDailySum(stocks) {
  const last = meta.last_signal_date || "";
  const map = {};
  stocks.forEach(function (s) {
    (s.daily || []).forEach(function (d) {
      if (last && d.date > last) return;
      map[d.day] = (map[d.day] || 0) + (d.money_yi || 0);
    });
  });
  return Object.keys(map).sort(function (a, b) { return a - b; }).map(function (k) {
    return { day: +k, sum: map[k] };
  });
}

function chartScales() {
  return {
    x: { ticks: { color: "#8b9cb3", maxRotation: 45 }, grid: { color: "#2a2a2a" } },
    y: {
      ticks: { color: "#8b9cb3" },
      grid: { color: "#2a2a2a" },
      title: { display: true, text: "亿元", color: "#8b9cb3" },
    },
  };
}

function renderCharts(stocks) {
  const key = yiKey(activeWin);
  const valid = stocks.filter(function (s) { return canComputeWin(s, activeWin); });
  const barEmpty = document.getElementById("barChartEmpty");
  const chartStocks = activeWin === 1 ? stocks : valid;

  if (activeWin > 1 && valid.length === 0) {
    if (barChart) { barChart.destroy(); barChart = null; }
    barEmpty.style.display = "flex";
    barEmpty.textContent = "当前日期还没有 " + activeWin + " 日汇总";
  } else {
    barEmpty.style.display = "none";
    const labels = chartStocks.map(function (s) { return (s.name || s.code).slice(0, 8); });
    const vals = chartStocks.map(function (s) { return s[key]; });
    if (barChart) barChart.destroy();
    barChart = new Chart(document.getElementById("barChart"), {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: activeWin + "日汇总(亿)",
          data: vals,
          backgroundColor: "rgba(255, 214, 102, 0.55)",
          borderColor: "#ffd666",
          borderWidth: 1,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: chartScales(),
      },
    });
  }

  const agg = aggregateDailySum(stocks);
  if (lineChart) lineChart.destroy();
  lineChart = new Chart(document.getElementById("lineChart"), {
    type: "line",
    data: {
      labels: agg.map(function (x) { return "第" + x.day + "日"; }),
      datasets: [{
        label: "当日全部新进合计(亿)",
        data: agg.map(function (x) { return x.sum; }),
        borderColor: "#52c41a",
        backgroundColor: "rgba(82, 196, 26, 0.12)",
        fill: true,
        tension: 0.25,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: chartScales(),
    },
  });
}

function render() {
  const stocks = currentStocks();
  selectedCode = null;
  detailCard.style.display = "none";
  renderStats(stocks);
  renderSummary(stocks);
  renderCharts(stocks);
}

document.getElementById("winBtns").addEventListener("click", function (e) {
  const btn = e.target.closest("button[data-win]");
  if (!btn) return;
  document.querySelectorAll("#winBtns button").forEach(function (b) { b.classList.remove("active"); });
  btn.classList.add("active");
  activeWin = +btn.dataset.win;
  render();
});

dateSelect.addEventListener("change", render);
searchInput.addEventListener("input", render);

fillDates();
render();
</script>
</body>
</html>
"""

ROOT = Path(__file__).resolve().parent
MONEY_WATCHLIST_OUT = ROOT / 'money_watchlist.html'
MONEY_AVG_WATCHLIST_OUT = ROOT / 'money_avg_watchlist.html'

_MONEY_AVG_WATCHLIST_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>新增板块3/5/10/20日日均成交额汇总</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: #111; color: #fff;
      font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif; }
    .page { padding: 16px 20px 32px; max-width: 1500px; margin: 0 auto; }
    .section-intro { padding: 15px 20px; color: #8b9cb3; background: #1a1a1a;
      border-radius: 10px; margin-bottom: 14px; line-height: 1.7; font-size: 14px; }
    .section-intro h2 { margin: 0 0 8px; color: #ffd666; font-size: 20px; }
    .card { background: #1f1f1f; border: 1px solid #333; border-radius: 10px;
      padding: 16px; margin-bottom: 14px; }
    .card h2 { margin: 0 0 8px; font-size: 16px; color: #ffd666; }
    .hint { font-size: 13px; color: #8b9cb3; margin: 0 0 12px; }
    .chart-box { height: 420px; position: relative; }
    .legend-note { font-size: 12px; color: #8b9cb3; margin-top: 8px; }
  </style>
</head>
<body>
<div class="page">
  <div class="section-intro">
    <h2 id="pageTitle">新增板块3/5/10/20日日均成交额汇总</h2>
    <p id="pageSub" class="hint" style="margin:0;"></p>
  </div>
  <div class="card">
    <h2>各信号日新进股 · 向前回溯日均成交额（亿元）</h2>
    <p class="hint">每条折线 = 当日全部新进股在该窗口下的<strong>算术平均日均成交额</strong>。
      avg_Nd = 从 T 往前 N 个交易日（含 T）成交额之和 ÷ N。与「向后合计」模块不同，本图向前看，最新日也可算满 3/5/10/20 日。</p>
    <div class="chart-box"><canvas id="avgLineChart"></canvas></div>
    <p class="legend-note">悬停可看当日新进只数；不足 N 个交易日历史则为空点。</p>
  </div>
</div>
<script>
const DATA = __PAYLOAD__;
const meta = DATA.meta || {};
const dates = DATA.dates || [];
const avgLines = DATA.avg_lines || {};
const newCounts = DATA.new_counts || [];
const windows = (meta.roll_windows || [3, 5, 10, 20]).map(String);

document.getElementById("pageTitle").textContent = meta.title || "新增板块3/5/10/20日日均成交额汇总";
document.getElementById("pageSub").textContent =
  "信号日 " + (meta.signal_days || dates.length) + " 个 · 新进条目 "
  + (meta.total_entries || 0) + " 条 · 窗口 "
  + windows.join("/") + " 交易日 · "
  + (meta.backtest_start || "") + " ~ " + (meta.last_signal_date || "");

const COLORS = { "3": "#ffd666", "5": "#52c41a", "10": "#1890ff", "20": "#eb2f96" };
const datasets = windows.map(function (w) {
  return {
    label: w + "日日均(亿)",
    data: (avgLines[w] || []).map(function (v) { return v == null ? null : Number(v); }),
    borderColor: COLORS[w] || "#aaa",
    backgroundColor: (COLORS[w] || "#aaa") + "33",
    tension: 0.25,
    spanGaps: false,
    pointRadius: 3,
    pointHoverRadius: 5,
  };
});

new Chart(document.getElementById("avgLineChart"), {
  type: "line",
  data: { labels: dates, datasets: datasets },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { labels: { color: "#ccc" } },
      tooltip: {
        callbacks: {
          afterTitle: function (items) {
            if (!items.length) return "";
            var i = items[0].dataIndex;
            var n = newCounts[i];
            return n != null ? "当日新进 " + n + " 只" : "";
          },
        },
      },
    },
    scales: {
      x: { ticks: { color: "#8b9cb3", maxRotation: 45 }, grid: { color: "#2a2a2a" } },
      y: {
        ticks: { color: "#8b9cb3" },
        grid: { color: "#2a2a2a" },
        title: { display: true, text: "亿元", color: "#8b9cb3" },
      },
    },
  },
});
</script>
</body>
</html>
"""


def _find_money_data_file(name):
    for base in (ROOT, Path(r'C:\Users\Lyonvv\Desktop\top50_watchlist')):
        p = base / name
        if p.exists():
            return p
    return None


def _opt_money_col(r, col):
    v = getattr(r, col, None)
    if v is None or (isinstance(v, float) and str(v) == 'nan'):
        return None
    return float(v)


def _fmt_yi_from_money(money):
    if money is None:
        return None
    return round(float(money) / 1e8, 2)


def _sanitize_money_watchlist_payload(payload):
    """修正不足 N 交易日时的汇总字段，避免未来占位日导致 sum_Nd 虚高。"""
    meta = payload.setdefault('meta', {})
    last = meta.get('last_signal_date') or ''
    windows = meta.get('roll_windows') or [1, 3, 5, 10, 20]

    def _fix_stock(stock):
        daily = stock.get('daily') or []
        if last and daily:
            daily = [d for d in daily if str(d.get('date', '')) <= last]
            stock['daily'] = daily
        track = len(daily) if daily else int(stock.get('track_days') or 0)
        stock['track_days'] = track
        monies = [float(d.get('money') or 0) for d in daily]
        for w in windows:
            if w == 1:
                continue
            if track < w:
                stock[f'sum_{w}d'] = None
                stock[f'sum_{w}d_yi'] = None
            else:
                s = sum(monies[:w])
                stock[f'sum_{w}d'] = round(s, 2)
                stock[f'sum_{w}d_yi'] = _fmt_yi_from_money(s)
        return {k: v for k, v in stock.items() if k != 'daily'}

    by_date = payload.get('byDate') or {}
    entries = []
    for block in by_date.values():
        fixed = []
        for stock in block.get('stocks') or []:
            entries.append(_fix_stock(stock))
            fixed.append(stock)
        block['stocks'] = fixed
    payload['entries'] = entries
    return payload


def load_money_watchlist_payload():
    json_path = _find_money_data_file('top50_money_watchlist.json')
    if json_path:
        payload = json.loads(json_path.read_text(encoding='utf-8'))
        payload.setdefault('meta', {}).setdefault('title', '新增板块3/5/10/20日成交额汇总')
        return _sanitize_money_watchlist_payload(payload)

    csv_path = _find_money_data_file('top50_money_watchlist.csv')
    if not csv_path:
        raise FileNotFoundError(
            '找不到 top50_money_watchlist.json / .csv，请从聚宽下载后放到 python_files 目录'
        )

    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    dates = sorted(df['entry_date'].astype(str).unique().tolist())
    by_date = {}
    entries = []
    for d in dates:
        g = df[df['entry_date'].astype(str) == d]
        stocks = []
        for r in g.itertuples():
            item = {
                'code': r.code,
                'name': r.name,
                'entry_date': str(d),
                'money_t': float(r.money_t),
                'money_t_yi': float(getattr(r, 'money_t_yi', r.money_t / 1e8)),
                'sum_1d_yi': _opt_money_col(r, 'sum_1d_yi'),
                'sum_3d_yi': _opt_money_col(r, 'sum_3d_yi'),
                'sum_5d_yi': _opt_money_col(r, 'sum_5d_yi'),
                'sum_10d_yi': _opt_money_col(r, 'sum_10d_yi'),
                'sum_20d_yi': _opt_money_col(r, 'sum_20d_yi'),
                'track_days': int(getattr(r, 'track_days', 0) or 0),
                'daily': [],
            }
            stocks.append(item)
            entries.append({k: v for k, v in item.items() if k != 'daily'})
        by_date[str(d)] = {'entry_date': str(d), 'count': len(stocks), 'stocks': stocks}

    payload = {
        'meta': {
            'title': '新增板块3/5/10/20日成交额汇总',
            'total_entries': len(entries),
            'signal_days': len(dates),
            'roll_windows': [1, 3, 5, 10, 20],
        },
        'dates': dates,
        'byDate': by_date,
        'entries': entries,
    }
    return _sanitize_money_watchlist_payload(payload)


def build_money_watchlist_page():
    payload = load_money_watchlist_payload()
    html = _MONEY_WATCHLIST_TEMPLATE.replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False))
    MONEY_WATCHLIST_OUT.write_text(html, encoding='utf-8')
    return MONEY_WATCHLIST_OUT


def load_money_avg_watchlist_payload():
    json_path = _find_money_data_file('top50_money_avg_watchlist.json')
    if not json_path:
        raise FileNotFoundError(
            '找不到 top50_money_avg_watchlist.json，请先在聚宽运行 top50_daily_pipeline_jq.py 并下载到 python_files'
        )
    payload = json.loads(json_path.read_text(encoding='utf-8'))
    payload.setdefault('meta', {}).setdefault('title', '新增板块3/5/10/20日日均成交额汇总')
    return payload


def build_money_avg_watchlist_page():
    payload = load_money_avg_watchlist_payload()
    html = _MONEY_AVG_WATCHLIST_TEMPLATE.replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False))
    MONEY_AVG_WATCHLIST_OUT.write_text(html, encoding='utf-8')
    return MONEY_AVG_WATCHLIST_OUT


def _ensure_index_tab_button(index_html, page_file, button_label):
    if page_file in index_html:
        return index_html
    anchor = "changePage('money_watchlist.html')"
    insert_btn = (
        f"    <button onclick=\"changePage('{page_file}')\">{button_label}</button>"
    )
    pos = index_html.find(anchor)
    if pos < 0:
        return index_html
    end = index_html.find('</button>', pos)
    if end < 0:
        return index_html
    return index_html[: end + 9] + '\n' + insert_btn + index_html[end + 9 :]


# =========================
# 读取数据
# =========================

new_df = pd.read_csv('每日成交额TOP50新增股票.csv')
new_df['date'] = pd.to_datetime(new_df['date']).dt.strftime('%Y-%m-%d')
weak_df = pd.read_csv('weak_to_strong.csv')
strong_df = pd.read_csv('strong_stocks.csv')
weak_df['date'] = pd.to_datetime(weak_df['日期']).dt.strftime('%Y-%m-%d')
strong_df['date'] = pd.to_datetime(strong_df['日期']).dt.strftime('%Y-%m-%d')
future_df = pd.read_csv('new_stock_future_10days.csv', encoding='utf-8-sig')
future_df['trade_date'] = pd.to_datetime(future_df['trade_date']).dt.strftime('%Y-%m-%d')
future_df['add_date'] = pd.to_datetime(future_df['add_date']).dt.strftime('%Y-%m-%d')

# 由 new_stock_future_10days 直接生成宽表（无需再跑 wide_stock_data.py）
df = build_wide_from_future(future_df)

# 读取阈值文件
threshold_df = pd.read_csv('top50_daily_threshold.csv')

# 关键步骤：强制将 date 列转为 datetime，再强制转为标准字符串格式 YYYY-MM-DD
threshold_df['date'] = pd.to_datetime(threshold_df['date']).dt.strftime('%Y-%m-%d')

# 重新构建字典，此时 Key 一定是 '2026-03-23' 这种纯字符串格式
threshold_dict = dict(zip(threshold_df['date'], threshold_df['amount_50th']))

threshold_json = json.dumps(threshold_dict)


# =========================
# 未来10日走势数据
# =========================


future_dict = {}

for _, row in df.iterrows():

    date = str(row['add_date'])
    stock = row['stock']

    if date not in future_dict:
        future_dict[date] = {}

    future_list = []

    base_open = row['open1']

    future_list.append({
            "day": 0,
            "open": row['open'],
            "close": row['close'],
            "pct": row['today_pct'],
            "cum_pct": (row['close'] - row['open']) / row['open']
        })

    for i in range(1, 11):

        future_list.append({
            "day": i,
            "open": row[f'open{i}'],
            "close": row[f'close{i}'],
            "pct": row[f'today_pct{i}'],
            "cum_pct": (row[f'close{i}'] - base_open) / base_open
        })

    future_dict[date][stock] = future_list


# =========================
# 弱转强详情字典
# =========================

# weak_detail = defaultdict(list)

# for _, row in weak_df.iterrows():
#     date = row['日期']
#     stock_info = f"""
#                     股票代码：{row['股票代码']}
#                     名称：{row['名称']}
#                     行业：{row['行业']}
#                     成交金额（亿）：{row['成交金额（亿）']}

#                     T日收盘价：{row['T日收盘价']}
#                     T-1日收盘价：{row['T-1日收盘价']}

#                     T日涨跌幅：{row['T日涨跌幅']}
#                     T+1日涨跌幅：{row['T+1日涨跌幅']}
#                     T+2日涨跌幅：{row['T+2日涨跌幅']}
#     """
#     weak_detail[date].append(stock_info)


# =========================
# 强者恒强详情字典
# =========================

# strong_detail = defaultdict(list)

# for _, row in strong_df.iterrows():
#     date = row['日期']
#     stock_info = f"""
#                     股票代码：{row['股票代码']}
#                     名称：{row['名称']}
#                     行业：{row['行业']}
#                     成交金额（亿）：{row['成交金额（亿）']}

#                     T日收盘价：{row['T日收盘价']}
#                     T-1日收盘价：{row['T-1日收盘价']}

#                     T日涨跌幅：{row['T日涨跌幅']}
#                     T+1日涨跌幅：{row['T+1日涨跌幅']}
#                     T+2日涨跌幅：{row['T+2日涨跌幅']}
#     """
#     strong_detail[date].append(stock_info)


# =========================
# 新增股票详情字典
# =========================

METRIC_COL_MAP = {
    'net_amount_main': ['net_amount_main', '主力净流入（万）'],
    'net_pct_main': ['net_pct_main', '主力占比（%）'],
    'turnover_ratio': ['turnover_ratio', '换手率（%）'],
}


def stock_metrics_payload(row):
    payload = {}
    for key, cols in METRIC_COL_MAP.items():
        val = None
        for col in cols:
            if col not in row.index:
                continue
            try:
                if pd.notna(row[col]):
                    val = round(float(row[col]), 2)
                    break
            except (TypeError, ValueError):
                continue
        payload[key] = val
    return payload


new_detail = defaultdict(list)

for _, row in new_df.iterrows():
    date = row['date']
    item = {
        'stock': row['stock'],
        'name': row['name'],
    }
    item.update(stock_metrics_payload(row))
    new_detail[date].append(item)


weak_detail = defaultdict(list)
for _, row in weak_df.iterrows():
    item = {
        'stock': row['股票代码'],
        'name': row['名称'],
    }
    item.update(stock_metrics_payload(row))
    weak_detail[row['date']].append(item)

strong_detail = defaultdict(list)
for _, row in strong_df.iterrows():
    item = {
        'stock': row['股票代码'],
        'name': row['名称'],
    }
    item.update(stock_metrics_payload(row))
    strong_detail[row['date']].append(item)


# =========================
# 第五部分：最新日期累计增幅为正（过去10个入选日）
# =========================

# 统计最近 N 个有数据的入选日（含再早 1 日，例如最新 5/25 时纳入 5/11）
LOOKBACK_DAYS = 11
MAX_DISPLAY_DAY = 10


def _price_valid(val):
    if val is None:
        return False
    try:
        return not pd.isna(val)
    except TypeError:
        return True


def trim_future_rows(future_list, max_day):
    """保留第0日~第max_day日有数据的天数，遇空行停止。"""
    rows = []
    for r in future_list:
        if r['day'] > max_day:
            break
        if not _price_valid(r.get('open')) or not _price_valid(r.get('close')):
            break
        rows.append(r)
    return rows


latest_trade_date = future_df['trade_date'].max()
selection_dates = sorted(new_df['date'].unique())
min_selection_date = selection_dates[0]
wide_index = df.set_index(['add_date', 'stock'])

# (add_date, stock) -> { trade_date: row }
future_by_stock = defaultdict(dict)
for _, row in future_df.iterrows():
    future_by_stock[(row['add_date'], row['stock'])][row['trade_date']] = row

# 可切换的截止交易日：从最早有入选数据日到最新交易日
all_cutoff_dates = sorted(
    d for d in future_df['trade_date'].unique() if min_selection_date <= d <= latest_trade_date
)


def compute_positive_snapshot(as_of_date):
    """截至 as_of_date 收盘，过去 LOOKBACK_DAYS 个入选日中累计为正的股票。"""
    lookback_dates = [d for d in selection_dates if d <= as_of_date][-LOOKBACK_DAYS:]
    sections = []

    for add_date in lookback_dates:
        stocks = []
        for _, stock_row in new_df[new_df['date'] == add_date].iterrows():
            stock = stock_row['stock']
            key = (add_date, stock)
            if key not in wide_index.index:
                continue

            wide_row = wide_index.loc[key]
            if isinstance(wide_row, pd.DataFrame):
                wide_row = wide_row.iloc[0]

            t1_open = wide_row['open1']
            if pd.isna(t1_open) or t1_open == 0:
                continue

            asof_row = future_by_stock.get((add_date, stock), {}).get(as_of_date)
            if asof_row is None:
                continue

            day_seq = int(asof_row['day_seq'])
            if day_seq < 1:
                continue

            close = float(asof_row['close'])
            cum_pct = (close - t1_open) / t1_open
            if cum_pct <= 0:
                continue

            future_list = future_dict.get(add_date, {}).get(stock, [])
            display_max = min(day_seq, MAX_DISPLAY_DAY)
            stocks.append({
                'name': stock_row['name'],
                'stock': stock,
                'cum_pct': float(cum_pct),
                'future': [
                    {
                        'day': int(fd['day']),
                        'open': float(fd['open']),
                        'close': float(fd['close']),
                        'cum_pct': float(fd['cum_pct']),
                    }
                    for fd in trim_future_rows(future_list, display_max)
                ],
            })

        if stocks:
            stocks.sort(key=lambda x: -x['cum_pct'])
            sections.append({
                'date': add_date,
                'threshold': float(threshold_dict.get(add_date, 0) or 0),
                'stocks': stocks,
            })

    return {
        'as_of_date': as_of_date,
        'lookback_dates': lookback_dates,
        'sections': sections,
        'total': sum(len(s['stocks']) for s in sections),
    }


print('正在生成各截止日快照…')
positive_snapshots = {}
for cutoff in all_cutoff_dates:
    positive_snapshots[cutoff] = compute_positive_snapshot(cutoff)

# 兼容旧逻辑：最新日快照
latest_snapshot = positive_snapshots[latest_trade_date]
positive_cum_rows = []
for section in latest_snapshot['sections']:
    for s in section['stocks']:
        positive_cum_rows.append({
            'add_date': section['date'],
            'stock': s['stock'],
            'name': s['name'],
            'cum_pct': s['cum_pct'],
            'future_days': s['future'],
        })


def build_positive_cum_payload(snapshots, cutoff_dates, latest_date):
    return {
        'latest_date': latest_date,
        'lookback_days': LOOKBACK_DAYS,
        'cutoff_dates': cutoff_dates,
        'default_cutoff': latest_date,
        'snapshots': snapshots,
        # 兼容旧版前端字段
        'lookback_dates': snapshots[latest_date]['lookback_dates'],
        'sections': snapshots[latest_date]['sections'],
    }


def render_stock_card_html(name, stock, future_days, summary_pct=None):
    rows_html = []
    for row in future_days:
        cls = 'pct-up' if row['cum_pct'] > 0 else 'pct-down'
        pct_str = f"{row['cum_pct'] * 100:.2f}%"
        rows_html.append(f"""
            <tr>
                <td>{row['day']}</td>
                <td>{row['open']}</td>
                <td>{row['close']}</td>
                <td class="{cls}">{pct_str}</td>
            </tr>""")

    summary_html = ''
    if summary_pct is not None:
        scls = 'summary-up' if summary_pct > 0 else 'summary-down'
        summary_html = (
            f'<p class="stock-summary {scls}">'
            f'截至最新日自T+1累计：{summary_pct * 100:.2f}%</p>'
        )

    return f"""
    <div class="stock-card-wrap">
        <div class="stock-card">
            <h3 class="stock-title">{name}（{stock}）</h3>
            {summary_html}
            <table class="stock-table">
                <thead><tr>
                    <th>第N日</th><th>开盘价</th><th>收盘价</th><th>自T+1日涨跌幅</th>
                </tr></thead>
                <tbody>{''.join(rows_html)}</tbody>
            </table>
        </div>
    </div>"""


def render_positive_cum_html(rows, latest_date, lookback_dates, thresholds):
    date_summary = ', '.join(lookback_dates)
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['add_date']].append(r)

    sections_html = []
    for add_date in lookback_dates:
        stocks = grouped.get(add_date, [])
        if not stocks:
            continue
        threshold = thresholds.get(add_date, 0)
        cards = ''.join(
            render_stock_card_html(s['name'], s['stock'], s['future_days'], s['cum_pct'])
            for s in stocks
        )
        sections_html.append(f"""
        <div class="date-block">
            <div class="date-header">
                <h3>{add_date} 第50名成交额：{threshold} 亿元</h3>
                <p>本日累计为正 {len(stocks)} 只（统计至 {latest_date}）</p>
            </div>
            <div class="card-row">{cards}</div>
        </div>""")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>最新日期累计增幅为正</title>
    <style>
        body {{ margin:0; padding:20px; background:#111; color:#fff; font-family:Arial,sans-serif; }}
        h2 {{ color:#ffd666; margin:0 0 10px; }}
        .meta {{ color:#8b9cb3; font-size:14px; line-height:1.7; margin-bottom:20px; }}
        .date-header {{ width:100%; padding:15px; background:#1f1f1f; border-radius:10px; margin-bottom:16px; }}
        .date-header h3 {{ margin:0 0 6px; font-size:17px; }}
        .date-header p {{ margin:0; color:#8b9cb3; font-size:13px; }}
        .card-row {{ display:flex; flex-wrap:wrap; justify-content:center; gap:20px; margin-bottom:30px; }}
        .stock-card-wrap {{ width:460px; flex-shrink:0; }}
        .stock-card {{ background:#1f1f1f; border-radius:10px; padding:15px; }}
        .stock-title {{ text-align:center; color:#ffd666; margin:0 0 8px; font-size:16px; }}
        .stock-summary {{ text-align:center; margin:0 0 12px; font-size:13px; }}
        .summary-up {{ color:#ff4d4f; }} .summary-down {{ color:#52c41a; }}
        .stock-table {{ width:100%; border-collapse:collapse; text-align:center; font-size:13px; }}
        .stock-table th, .stock-table td {{ padding:6px; border:1px solid #444; }}
        .stock-table th {{ background:#333; }}
        .pct-up {{ color:#ff4d4f; font-weight:bold; }}
        .pct-down {{ color:#52c41a; font-weight:bold; }}
        .empty-hint {{ text-align:center; color:#999; padding:40px; }}
    </style>
</head>
<body>
    <h2>最新日期累计增幅为正</h2>
    <div class="meta">
        统计截至：<b>{latest_date}</b><br>
        入选日范围（最近 {len(lookback_dates)} 个交易日）：{date_summary}<br>
        规则：从 <b>T+1 开盘价</b> 持有至 <b>{latest_date}</b> 收盘价累计涨幅 &gt; 0。<br>
        每只股票展示 <b>T 日至 T+10 日</b> 走势（无数据的天数自动隐藏）。
    </div>
    {''.join(sections_html) if sections_html else '<p class="empty-hint">暂无符合条件的股票</p>'}
</body>
</html>"""
    return html


positive_cum_payload = build_positive_cum_payload(
    positive_snapshots,
    all_cutoff_dates,
    latest_trade_date,
)

with open('positive_cum.html', 'w', encoding='utf-8') as f:
    f.write(render_positive_cum_html(
        positive_cum_rows,
        latest_trade_date,
        latest_snapshot['lookback_dates'],
        threshold_dict,
    ))


# =========================
# 第一部分：每日统计柱状图
# =========================

new_count = new_df.groupby('date').size().reset_index(name='新增')
weak_count = weak_df.groupby('date').size().reset_index(name='弱转强')
strong_count = strong_df.groupby('date').size().reset_index(name='强者恒强')

all_dates = sorted(list(set(new_count['date'].tolist() + weak_count['date'].tolist() + strong_count['date'].tolist())))
result = pd.DataFrame({'date': all_dates})
result = result.merge(new_count, on='date', how='left')
result = result.merge(weak_count, on='date', how='left')
result = result.merge(strong_count, on='date', how='left')
result = result.fillna(0)

bar = (
    Bar(init_opts=opts.InitOpts(
        width="100%",
        height="780px",
        theme=ThemeType.DARK
    ))
    .add_xaxis(result['date'].tolist())
    .add_yaxis('新增', result['新增'].tolist())
    .add_yaxis('弱转强', result['弱转强'].tolist())
    .add_yaxis('强者恒强', result['强者恒强'].tolist())
    .set_global_opts(
        title_opts=opts.TitleOpts(
            title='每日成交额TOP50统计',
            subtitle='本模块统计每日进入两市成交额TOP50的新增个股数量,并筛选出T+1日、T+2日仍留存的股票,\n然后分为两类:T日增跌幅<0,T+1日>0(弱转强) 以及T日增跌幅>0,T+1日>0的股票(强者恒强)',
            pos_top='1%',
            item_gap=6,
            subtitle_textstyle_opts=opts.TextStyleOpts(
                font_size=11,
                line_height=16,
                color="#aaaaaa",
                font_weight="normal",
            ),
        ),
        tooltip_opts=opts.TooltipOpts(trigger='axis'),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        yaxis_opts=opts.AxisOpts(name='数量（只）'),
        datazoom_opts=[opts.DataZoomOpts()],
        legend_opts=opts.LegendOpts(
            pos_top='13%',
            pos_left='center',
            item_gap=16,
        ),
    )
)

# 点击事件
# 点击事件
# 点击事件（终极无错版）
bar.add_js_funcs("""

window.myChart = chart_""" + bar.chart_id + """;

// 固定绘图区 + 右侧提示（与图表同帧渲染，避免 iframe 轮询延迟）
(function() {
    var hintText = ' 点击新增/弱转强/强者恒强柱体，查看未来走势';
    chart_""" + bar.chart_id + """.setOption({
        grid: {
            top: '20%',
            left: '3%',
            right: '10%',
            bottom: '14%',
            containLabel: true
        },
        graphic: [{
            type: 'text',
            right: '6.5%',
            top: '30%',
            silent: true,
            z: 100,
            style: {
                text: hintText.split('').join('\\n'),
                fontSize: 16,
                fontWeight: 'bold',
                fill: '#ffffff',
                opacity: 0.8,
                textAlign: 'center',
                lineHeight: 20
            }
        }]
    });
})();

var futureData = """ + json.dumps(future_dict, ensure_ascii=False) + """;
var newData = """ + json.dumps(dict(new_detail), ensure_ascii=False) + """;
var weakData = """ + json.dumps(dict(weak_detail), ensure_ascii=False) + """;
var strongData = """ + json.dumps(dict(strong_detail), ensure_ascii=False) + """;
var thresholdData = """ + threshold_json + """;
var seriesStockMap = {
    '新增': newData,
    '弱转强': weakData,
    '强者恒强': strongData
};
var seriesHint = {
    '新增': '当日全部新进 Top50',
    '弱转强': 'T日跌、T+1涨，且 T+1/T+2 仍留 Top50',
    '强者恒强': 'T日涨、T+1涨，且 T+1/T+2 仍留 Top50'
};

chart_""" + bar.chart_id + """.on('click', function(params) {

    var seriesNames = ['新增', '弱转强', '强者恒强'];
    var seriesName = params.seriesName;
    if (!seriesName && params.seriesIndex != null) {
        seriesName = seriesNames[params.seriesIndex];
    }
    var dataMap = seriesStockMap[seriesName];
    if(!dataMap) {
        return;
    }

    var date = params.name;
    if (!date && params.dataIndex != null) {
        date = chart_""" + bar.chart_id + """.getOption().xAxis[0].data[params.dataIndex];
    }
    var stocks = dataMap[date];

    if(!stocks || !stocks.length) {
        return;
    }

    var area = parent.document.getElementById('futureChartArea');
    area.innerHTML = "";
    area.style.display = 'flex';

    var threshold = thresholdData[date] || 0;
    var extra = seriesHint[seriesName] || '';
    area.insertAdjacentHTML('beforeend', parent.buildDateHeaderHtml(date, threshold, extra));

    var cardRow = parent.document.createElement('div');
    cardRow.className = 'card-row';
    area.appendChild(cardRow);

    stocks.forEach(function(item) {

        var future = futureData[String(date)] && futureData[String(date)][String(item.stock)];

        if(!future) {
            return;
        }

        var trimmed = parent.trimFutureRows(future, parent.MAX_DISPLAY_DAY || 10);
        var wrap = parent.document.createElement('div');
        wrap.className = 'stock-card-wrap';
        wrap.innerHTML = parent.buildStockCardHtml(item.name, item.stock, trimmed, undefined, undefined, item);
        cardRow.appendChild(wrap);

    });

    if (area.scrollIntoView) {
        area.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

});
""")


# =========================
# 第二部分：行业热力图（申万二级；类别多，汇总图只展示 Top N）
# =========================

INDUSTRY_LEVEL_LABEL = '申万二级行业'
HEAT_TOP_N = 30

industry_count = new_df['industry'].value_counts().reset_index()
industry_count.columns = ['industry', 'count']
industry_count = industry_count.head(HEAT_TOP_N)
heat_height = max(760, min(1200, 420 + len(industry_count) * 18))

heat_bar = (
    Bar(init_opts=opts.InitOpts(
        width="100%",
        height=f"{heat_height}px",
        theme=ThemeType.DARK
    ))
    .add_xaxis(industry_count['industry'].tolist())
    .add_yaxis('行业出现次数', industry_count['count'].tolist(), category_gap='40%')
    .set_global_opts(
        title_opts=opts.TitleOpts(title=f'{INDUSTRY_LEVEL_LABEL}热力分布（Top {HEAT_TOP_N}）'),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45, font_size=10)),
        visualmap_opts=opts.VisualMapOpts(max_=int(industry_count['count'].max()),
                                        pos_right="5%", 
                                        pos_top="middle")
    )
)


# =========================
# 第三部分：行业轮动图（按日统计二级行业）
# =========================

rotation_group = new_df.groupby(['date', 'industry']).size().reset_index(name='count')
timeline = Timeline(init_opts=opts.InitOpts(        width="100%",
                                                    height="760px",
                                                    theme=ThemeType.DARK))


for d in sorted(rotation_group['date'].unique()):
    temp = rotation_group[rotation_group['date'] == d].sort_values(by='count', ascending=False)
    bar_day = (
        Bar()
        .add_xaxis(temp['industry'].tolist())
        .add_yaxis('数量', temp['count'].tolist())
        .set_global_opts(
            title_opts=opts.TitleOpts(title=f'{d} {INDUSTRY_LEVEL_LABEL}轮动'),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45, font_size=10)),
            visualmap_opts=opts.VisualMapOpts(max_=int(temp['count'].max()),
                                            pos_right="5%",   # 离右边 5%，往左挪，靠近主图
                                            pos_top="middle"  # 垂直居中，和主图对齐
                                              )
        )
    )
    timeline.add(bar_day, time_point=d)

timeline.add_schema(play_interval=1400, is_auto_play=True, is_loop_play=False)


# =========================
# 输出三个图表
# =========================

bar.render("bar.html")
heat_bar.render("heat.html")
timeline.render("timeline_v2.html")

try:
    money_path = build_money_watchlist_page()
    print(f"  -> {money_path.name} 已生成（第6板块 iframe）")
except Exception as e:
    print(f"  ⚠ 成交额汇总页未生成: {e}")

try:
    money_avg_path = build_money_avg_watchlist_page()
    print(f"  -> {money_avg_path.name} 已生成（第7板块 iframe）")
except Exception as e:
    print(f"  ⚠ 日均成交额页未生成: {e}")

print("Dashboard 生成完成！")
print(f"最新交易日: {latest_trade_date}，累计为正: {latest_snapshot['total']} 只")
print(f"  -> 日期存档: {all_cutoff_dates[0]} ~ {all_cutoff_dates[-1]} 共 {len(all_cutoff_dates)} 个交易日")
print(f"  -> 入选日窗口: 最近 {LOOKBACK_DAYS} 天")
print("  -> positive_cum 数据已写入 index.html（内嵌脚本）")
print("  -> positive_cum.html 已更新（独立页，可选）")

# 将累计为正快照内嵌进 index.html，不再单独生成 positive_cum_data.js
cache_ver = f"{latest_trade_date}-d{LOOKBACK_DAYS}-snap{len(all_cutoff_dates)}"
positive_cum_script = (
    '<script id="positive-cum-data">\n'
    'window.positiveCumData = '
    + json.dumps(positive_cum_payload, ensure_ascii=False)
    + ';\n</script>'
)
with open("index.html", "r", encoding="utf-8") as f:
    index_html = f.read()

if "<!--POSITIVE_CUM_DATA_START-->" in index_html:
    index_html = re.sub(
        r"<!--POSITIVE_CUM_DATA_START-->.*?<!--POSITIVE_CUM_DATA_END-->",
        "<!--POSITIVE_CUM_DATA_START-->\n"
        + positive_cum_script
        + "\n<!--POSITIVE_CUM_DATA_END-->",
        index_html,
        count=1,
        flags=re.DOTALL,
    )
else:
    # 兼容旧版：移除 external js，插入内嵌块
    index_html = re.sub(
        r'<script src="positive_cum_data\.js[^"]*"></script>\s*',
        "",
        index_html,
    )
    index_html = index_html.replace(
        "<script>\nvar MAX_DISPLAY_DAY",
        positive_cum_script + "\n<script>\nvar MAX_DISPLAY_DAY",
        1,
    )

index_html = _ensure_index_tab_button(
    index_html,
    'money_avg_watchlist.html',
    '新增板块3/5/10/20日日均成交额汇总',
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(index_html)
print(f"  -> index.html 已更新（数据版本 {cache_ver}）")
            