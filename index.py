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


_MONEY_WATCHLIST_TEMPLATE = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n  <meta charset="UTF-8"/>\n  <meta name="viewport" content="width=device-width, initial-scale=1"/>\n  <title>板块资金 3/5/10/20 日成交额汇总</title>\n  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>\n  <style>\n    * { box-sizing: border-box; }\n    html, body {\n      margin: 0; padding: 0;\n      background: #111; color: #fff;\n      font-family: Arial, "PingFang SC", "Microsoft YaHei", sans-serif;\n      line-height: 1.5; overflow-x: hidden;\n    }\n    .page { padding: 16px 20px 32px; max-width: 1500px; margin: 0 auto; }\n    .section-intro {\n      padding: 15px 20px; color: #8b9cb3;\n      background: #1a1a1a; border-radius: 10px;\n      margin-bottom: 14px; line-height: 1.7; font-size: 14px;\n    }\n    .section-intro h2 { margin: 0 0 8px; color: #ffd666; font-size: 20px; }\n    .toolbar {\n      display: flex; flex-wrap: wrap; gap: 12px; align-items: center;\n      margin-bottom: 14px;\n    }\n    label { color: #8b9cb3; font-size: 14px; }\n    select, input {\n      background: #333; border: 1px solid #444; color: #fff;\n      padding: 8px 10px; border-radius: 6px; font-size: 14px;\n    }\n    .filter-btns { display: flex; gap: 8px; flex-wrap: wrap; }\n    .filter-btns button {\n      background: #333; color: #fff; border: none;\n      border-radius: 8px; padding: 10px 16px; cursor: pointer; font-size: 14px;\n    }\n    .filter-btns button:hover { background: #555; }\n    .filter-btns button.active {\n      background: rgba(255, 214, 102, 0.15);\n      box-shadow: inset 0 0 0 1px #ffd666; color: #ffd666;\n    }\n    .stats {\n      display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));\n      gap: 10px; margin-bottom: 14px;\n    }\n    .stat {\n      background: #1f1f1f; border: 1px solid #333;\n      border-radius: 8px; padding: 10px 14px;\n    }\n    .stat label { display: block; color: #8b9cb3; font-size: 12px; }\n    .stat span { font-size: 17px; font-weight: 600; color: #fff; }\n    .card {\n      background: #1f1f1f; border: 1px solid #333;\n      border-radius: 10px; padding: 16px; margin-bottom: 14px;\n    }\n    .card h2 { margin: 0 0 10px; font-size: 16px; color: #ffd666; font-weight: 600; }\n    .hint { font-size: 13px; color: #8b9cb3; margin: 0 0 10px; }\n    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }\n    @media (max-width: 960px) { .grid2 { grid-template-columns: 1fr; } }\n    .chart-box { height: 280px; position: relative; }\n    .table-wrap {\n      max-height: 55vh; overflow: auto;\n      border-radius: 8px; border: 1px solid #333;\n    }\n    table { width: 100%; border-collapse: collapse; font-size: 13px; }\n    th, td { padding: 8px 10px; border-bottom: 1px solid #333; text-align: right; }\n    th {\n      background: #333; color: #8b9cb3; font-weight: 500;\n      position: sticky; top: 0; z-index: 2;\n    }\n    th.left, td.left { text-align: left; }\n    tr:hover { background: rgba(255, 214, 102, 0.06); }\n    tr.sel { background: rgba(255, 214, 102, 0.12); }\n    .detail-card {\n      border: 1px solid #333; border-radius: 10px; overflow: hidden;\n    }\n    .detail-head {\n      padding: 12px 14px; border-bottom: 1px solid #333;\n      display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;\n      background: #1a1a1a;\n    }\n    .detail-name { font-weight: 600; color: #ffd666; }\n    .detail-code { color: #8b9cb3; font-family: Consolas, monospace; font-size: 13px; }\n    .badge {\n      font-size: 12px; padding: 2px 8px; border-radius: 4px;\n      background: rgba(255, 214, 102, 0.15); color: #ffd666;\n    }\n    .empty { text-align: center; padding: 24px; color: #8b9cb3; }\n  </style>\n</head>\n<body>\n<div class="page">\n  <div class="section-intro">\n    <h2 id="pageTitle">板块资金 3/5/10/20 日成交额汇总</h2>\n    <p id="pageSub" class="hint" style="margin:0;color:#8b9cb3;"></p>\n  </div>\n\n  <div class="toolbar">\n    <label>信号日 T <select id="dateSelect"></select></label>\n    <label>搜索 <input id="searchInput" placeholder="代码 / 名称" style="min-width:140px"/></label>\n    <div class="filter-btns" id="winBtns">\n      <button type="button" class="active" data-win="3">3日汇总</button>\n      <button type="button" data-win="5">5日汇总</button>\n      <button type="button" data-win="10">10日汇总</button>\n      <button type="button" data-win="20">20日汇总</button>\n    </div>\n  </div>\n\n  <div class="stats" id="stats"></div>\n\n  <div class="grid2">\n    <div class="card">\n      <h2>当日汇总对比（亿元）</h2>\n      <p class="hint">所选信号日各新进股的 N 日成交额合计</p>\n      <div class="chart-box"><canvas id="barChart"></canvas></div>\n    </div>\n    <div class="card">\n      <h2>当日合计走势（亿元）</h2>\n      <p class="hint">当日全部新进股逐日成交额之和（T=第0日）</p>\n      <div class="chart-box"><canvas id="lineChart"></canvas></div>\n    </div>\n  </div>\n\n  <div class="card">\n    <h2>汇总表 · 点击行查看逐日明细</h2>\n    <p class="hint">单位：亿元。sum_Nd = 从 T 日起连续 N 个交易日成交额之和（含 T 日）</p>\n    <div class="table-wrap">\n      <table>\n        <thead>\n          <tr>\n            <th class="left">名称</th>\n            <th class="left">代码</th>\n            <th>T日</th>\n            <th>3日</th>\n            <th>5日</th>\n            <th>10日</th>\n            <th>20日</th>\n            <th>可追踪</th>\n          </tr>\n        </thead>\n        <tbody id="summaryBody"></tbody>\n      </table>\n    </div>\n  </div>\n\n  <div class="card" id="detailCard" style="display:none">\n    <h2 id="detailTitle">逐日明细</h2>\n    <div id="detailContent"></div>\n  </div>\n</div>\n\n<script>\nconst DATA = __PAYLOAD__;\nconst meta = DATA.meta || {};\nconst byDate = DATA.byDate || {};\nconst dates = DATA.dates || [];\n\ndocument.getElementById("pageTitle").textContent =\n  meta.title || "板块资金 3/5/10/20 日成交额汇总";\ndocument.getElementById("pageSub").textContent =\n  "信号日 " + (meta.signal_days || dates.length) + " 个 · 新进条目 "\n  + (meta.total_entries || 0) + " 条 · 汇总窗口 "\n  + (meta.roll_windows || [3, 5, 10, 20]).join("/") + " 交易日 · 数据 "\n  + (meta.backtest_start || "") + " ~ " + (meta.last_signal_date || "");\n\nconst dateSelect = document.getElementById("dateSelect");\nconst searchInput = document.getElementById("searchInput");\nconst summaryBody = document.getElementById("summaryBody");\nconst statsEl = document.getElementById("stats");\nconst detailCard = document.getElementById("detailCard");\nconst detailTitle = document.getElementById("detailTitle");\nconst detailContent = document.getElementById("detailContent");\n\nlet activeWin = 3;\nlet selectedCode = null;\nlet barChart = null;\nlet lineChart = null;\n\nfunction fmt(v) {\n  if (v == null || v === "" || Number.isNaN(v)) return "—";\n  return Number(v).toFixed(2);\n}\n\nfunction yiKey(win) { return "sum_" + win + "d_yi"; }\n\nfunction currentStocks() {\n  const d = dateSelect.value;\n  const block = byDate[d] || { stocks: [] };\n  const q = (searchInput.value || "").trim().toLowerCase();\n  return (block.stocks || []).filter(function (s) {\n    if (!q) return true;\n    return (s.code || "").toLowerCase().indexOf(q) >= 0\n      || (s.name || "").toLowerCase().indexOf(q) >= 0;\n  });\n}\n\nfunction fillDates() {\n  dateSelect.innerHTML = "";\n  dates.forEach(function (d) {\n    const n = (byDate[d] && byDate[d].stocks) ? byDate[d].stocks.length : 0;\n    const opt = document.createElement("option");\n    opt.value = d;\n    opt.textContent = n ? (d + "（" + n + " 只）") : (d + "（无新进）");\n    dateSelect.appendChild(opt);\n  });\n  if (dates.length) dateSelect.value = dates[dates.length - 1];\n}\n\nfunction renderStats(stocks) {\n  const cnt = stocks.length;\n  const avgT = cnt ? stocks.reduce(function (a, s) { return a + (s.money_t_yi || 0); }, 0) / cnt : 0;\n  const key = yiKey(activeWin);\n  const valid = stocks.filter(function (s) { return s[key] != null; });\n  const avgSum = valid.length ? valid.reduce(function (a, s) { return a + s[key]; }, 0) / valid.length : 0;\n  const totalSum = valid.reduce(function (a, s) { return a + s[key]; }, 0);\n  const rows = [\n    ["当日新进", cnt + " 只"],\n    ["T日成交额均值", fmt(avgT) + " 亿"],\n    [activeWin + "日汇总均值", fmt(avgSum) + " 亿"],\n    [activeWin + "日汇总合计", fmt(totalSum) + " 亿"],\n    ["可算" + activeWin + "日", valid.length + " 只"],\n  ];\n  statsEl.innerHTML = rows.map(function (pair) {\n    return \'<div class="stat"><label>\' + pair[0] + \'</label><span>\' + pair[1] + \'</span></div>\';\n  }).join("");\n}\n\nfunction renderSummary(stocks) {\n  summaryBody.innerHTML = stocks.map(function (s) {\n    const sel = s.code === selectedCode ? "sel" : "";\n    return \'<tr class="\' + sel + \'" data-code="\' + s.code + \'">\'\n      + \'<td class="left">\' + (s.name || "—") + \'</td>\'\n      + \'<td class="left">\' + s.code + \'</td>\'\n      + \'<td>\' + fmt(s.money_t_yi) + \'</td>\'\n      + \'<td>\' + fmt(s.sum_3d_yi) + \'</td>\'\n      + \'<td>\' + fmt(s.sum_5d_yi) + \'</td>\'\n      + \'<td>\' + fmt(s.sum_10d_yi) + \'</td>\'\n      + \'<td>\' + fmt(s.sum_20d_yi) + \'</td>\'\n      + \'<td>\' + (s.track_days || 0) + \' 日</td></tr>\';\n  }).join("") || \'<tr><td colspan="8" class="empty">无数据</td></tr>\';\n\n  summaryBody.querySelectorAll("tr[data-code]").forEach(function (tr) {\n    tr.addEventListener("click", function () {\n      selectedCode = tr.dataset.code;\n      renderSummary(stocks);\n      renderDetail(stocks.find(function (x) { return x.code === selectedCode; }));\n    });\n  });\n}\n\nfunction renderDetail(stock) {\n  if (!stock || !stock.daily || !stock.daily.length) {\n    detailCard.style.display = "none";\n    return;\n  }\n  detailCard.style.display = "block";\n  detailTitle.textContent = "【" + stock.name + "】" + stock.code + " · 逐日成交额（亿元）";\n  const rows = stock.daily.map(function (d) {\n    return \'<tr><td class="left">第 \' + d.day + \' 日</td><td class="left">\' + d.date\n      + \'</td><td>\' + fmt(d.money_yi) + \'</td></tr>\';\n  }).join("");\n  detailContent.innerHTML =\n    \'<div class="detail-card"><div class="detail-head">\'\n    + \'<span class="detail-name">\' + stock.name + \'</span>\'\n    + \'<span class="detail-code">\' + stock.code + \'</span>\'\n    + \'<span class="badge">T=\' + stock.entry_date + \'</span></div>\'\n    + \'<table><thead><tr><th class="left">序</th><th class="left">日期</th><th>成交额(亿)</th></tr></thead>\'\n    + \'<tbody>\' + rows + \'</tbody></table></div>\';\n}\n\nfunction aggregateDailySum(stocks) {\n  const map = {};\n  stocks.forEach(function (s) {\n    (s.daily || []).forEach(function (d) {\n      map[d.day] = (map[d.day] || 0) + (d.money_yi || 0);\n    });\n  });\n  return Object.keys(map).sort(function (a, b) { return a - b; }).map(function (k) {\n    return { day: +k, sum: map[k] };\n  });\n}\n\nfunction chartScales() {\n  return {\n    x: { ticks: { color: "#8b9cb3", maxRotation: 45 }, grid: { color: "#2a2a2a" } },\n    y: {\n      ticks: { color: "#8b9cb3" },\n      grid: { color: "#2a2a2a" },\n      title: { display: true, text: "亿元", color: "#8b9cb3" },\n    },\n  };\n}\n\nfunction renderCharts(stocks) {\n  const key = yiKey(activeWin);\n  const labels = stocks.map(function (s) { return (s.name || s.code).slice(0, 8); });\n  const vals = stocks.map(function (s) { return s[key] != null ? s[key] : 0; });\n\n  if (barChart) barChart.destroy();\n  barChart = new Chart(document.getElementById("barChart"), {\n    type: "bar",\n    data: {\n      labels: labels,\n      datasets: [{\n        label: activeWin + "日汇总(亿)",\n        data: vals,\n        backgroundColor: "rgba(255, 214, 102, 0.55)",\n        borderColor: "#ffd666",\n        borderWidth: 1,\n      }],\n    },\n    options: {\n      responsive: true, maintainAspectRatio: false,\n      plugins: { legend: { display: false } },\n      scales: chartScales(),\n    },\n  });\n\n  const agg = aggregateDailySum(stocks);\n  if (lineChart) lineChart.destroy();\n  lineChart = new Chart(document.getElementById("lineChart"), {\n    type: "line",\n    data: {\n      labels: agg.map(function (x) { return "第" + x.day + "日"; }),\n      datasets: [{\n        label: "当日全部新进合计(亿)",\n        data: agg.map(function (x) { return x.sum; }),\n        borderColor: "#52c41a",\n        backgroundColor: "rgba(82, 196, 26, 0.12)",\n        fill: true,\n        tension: 0.25,\n      }],\n    },\n    options: {\n      responsive: true, maintainAspectRatio: false,\n      plugins: { legend: { display: false } },\n      scales: chartScales(),\n    },\n  });\n}\n\nfunction render() {\n  const stocks = currentStocks();\n  selectedCode = null;\n  detailCard.style.display = "none";\n  renderStats(stocks);\n  renderSummary(stocks);\n  renderCharts(stocks);\n}\n\ndocument.getElementById("winBtns").addEventListener("click", function (e) {\n  const btn = e.target.closest("button[data-win]");\n  if (!btn) return;\n  document.querySelectorAll("#winBtns button").forEach(function (b) { b.classList.remove("active"); });\n  btn.classList.add("active");\n  activeWin = +btn.dataset.win;\n  render();\n});\n\ndateSelect.addEventListener("change", render);\nsearchInput.addEventListener("input", render);\n\nfillDates();\nrender();\n</script>\n</body>\n</html>\n'


ROOT = Path(__file__).resolve().parent
MONEY_WATCHLIST_OUT = ROOT / 'money_watchlist.html'


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


def load_money_watchlist_payload():
    json_path = _find_money_data_file('top50_money_watchlist.json')
    if json_path:
        payload = json.loads(json_path.read_text(encoding='utf-8'))
        payload.setdefault('meta', {}).setdefault('title', '板块资金 3/5/10/20 日成交额汇总')
        return payload

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

    return {
        'meta': {
            'title': '板块资金 3/5/10/20 日成交额汇总',
            'total_entries': len(entries),
            'signal_days': len(dates),
            'roll_windows': [3, 5, 10, 20],
        },
        'dates': dates,
        'byDate': by_date,
        'entries': entries,
    }


def build_money_watchlist_page():
    payload = load_money_watchlist_payload()
    html = _MONEY_WATCHLIST_TEMPLATE.replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False))
    MONEY_WATCHLIST_OUT.write_text(html, encoding='utf-8')
    return MONEY_WATCHLIST_OUT


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

new_detail = defaultdict(list)

for _, row in new_df.iterrows():
    date = row['date']
    new_detail[date].append({
        'stock': row['stock'],
        'name': row['name']
    })


weak_detail = defaultdict(list)
for _, row in weak_df.iterrows():
    weak_detail[row['date']].append({
        'stock': row['股票代码'],
        'name': row['名称'],
    })

strong_detail = defaultdict(list)
for _, row in strong_df.iterrows():
    strong_detail[row['date']].append({
        'stock': row['股票代码'],
        'name': row['名称'],
    })


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
        wrap.innerHTML = parent.buildStockCardHtml(item.name, item.stock, trimmed);
        cardRow.appendChild(wrap);

    });

    if (area.scrollIntoView) {
        area.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

});
""")


# =========================
# 第二部分：行业热力图
# =========================

industry_count = new_df['industry'].value_counts().reset_index()
industry_count.columns = ['industry', 'count']

heat_bar = (
    Bar(init_opts=opts.InitOpts(
        width="100%",
        height="760px",
        theme=ThemeType.DARK
    ))
    .add_xaxis(industry_count['industry'].tolist())
    .add_yaxis('行业出现次数', industry_count['count'].tolist(), category_gap='40%')
    .set_global_opts(
        title_opts=opts.TitleOpts(title='行业热力分布'),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        visualmap_opts=opts.VisualMapOpts(max_=int(industry_count['count'].max()),
                                        pos_right="5%", 
                                        pos_top="middle")
    )
)


# =========================
# 第三部分：行业轮动图
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
            title_opts=opts.TitleOpts(title=f'{d} 行业轮动'),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
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

with open("index.html", "w", encoding="utf-8") as f:
    f.write(index_html)
print(f"  -> index.html 已更新（数据版本 {cache_ver}）")
            