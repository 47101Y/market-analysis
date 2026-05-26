import pandas as pd
from pyecharts.charts import Bar, Pie, Timeline, Page
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from collections import defaultdict
from pyecharts.globals import CurrentConfig
import json

CurrentConfig.ONLINE_HOST = "https://assets.pyecharts.org/assets/v5/"


# =========================
# 读取数据
# =========================

new_df = pd.read_csv('每日成交额TOP50新增股票.csv')
new_df['date'] = pd.to_datetime(new_df['date']).dt.strftime('%Y-%m-%d')
weak_df = pd.read_csv('弱转强.csv')
strong_df = pd.read_csv('强者恒强.csv')
future_df = pd.read_csv('new_stock_future_10days.csv')
future_df['trade_date'] = pd.to_datetime(future_df['trade_date']).dt.strftime('%Y-%m-%d')
future_df['add_date'] = pd.to_datetime(future_df['add_date']).dt.strftime('%Y-%m-%d')


#宽表格重现
df = pd.read_csv("wide_stock_data.csv")
df['add_date'] = pd.to_datetime(df['add_date']).dt.strftime('%Y-%m-%d')

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
last_n_selection_dates = selection_dates[-LOOKBACK_DAYS:]

wide_index = df.set_index(['add_date', 'stock'])
positive_cum_rows = []

for add_date in last_n_selection_dates:
    day_stocks = new_df[new_df['date'] == add_date]
    for _, stock_row in day_stocks.iterrows():
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

        latest_slice = future_df[
            (future_df['add_date'] == add_date)
            & (future_df['stock'] == stock)
            & (future_df['trade_date'] == latest_trade_date)
        ]
        if latest_slice.empty:
            continue

        day_seq = int(latest_slice.iloc[0]['day_seq'])
        if day_seq < 1:
            continue

        latest_close = float(latest_slice.iloc[0]['close'])
        cum_pct = (latest_close - t1_open) / t1_open
        if cum_pct <= 0:
            continue

        positive_cum_rows.append({
            'add_date': add_date,
            'stock': stock,
            'name': stock_row['name'],
            'industry': stock_row['industry'],
            't1_open': round(float(t1_open), 4),
            'latest_close': round(latest_close, 4),
            'cum_pct': cum_pct,
            'hold_days': day_seq,
            'future_days': trim_future_rows(
                future_dict.get(add_date, {}).get(stock, []),
                MAX_DISPLAY_DAY,
            ),
        })

positive_cum_rows.sort(key=lambda x: (x['add_date'], -x['cum_pct']))


def build_positive_cum_payload(rows, latest_date, lookback_dates, thresholds):
    grouped = defaultdict(list)
    for r in rows:
        grouped[r['add_date']].append({
            'name': r['name'],
            'stock': r['stock'],
            'cum_pct': float(r['cum_pct']),
            'future': [
                {
                    'day': int(fd['day']),
                    'open': float(fd['open']),
                    'close': float(fd['close']),
                    'cum_pct': float(fd['cum_pct']),
                }
                for fd in r['future_days']
            ],
        })

    sections = []
    for add_date in lookback_dates:
        stocks = grouped.get(add_date, [])
        if not stocks:
            continue
        sections.append({
            'date': add_date,
            'threshold': float(thresholds.get(add_date, 0) or 0),
            'stocks': stocks,
        })

    return {
        'latest_date': latest_date,
        'lookback_dates': lookback_dates,
        'sections': sections,
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
    positive_cum_rows,
    latest_trade_date,
    last_n_selection_dates,
    threshold_dict,
)

with open('positive_cum_data.js', 'w', encoding='utf-8') as f:
    f.write('window.positiveCumData = ')
    json.dump(positive_cum_payload, f, ensure_ascii=False)
    f.write(';\n')

with open('positive_cum.html', 'w', encoding='utf-8') as f:
    f.write(render_positive_cum_html(
        positive_cum_rows,
        latest_trade_date,
        last_n_selection_dates,
        threshold_dict,
    ))


# =========================
# 第一部分：每日统计柱状图
# =========================

new_count = new_df.groupby('date').size().reset_index(name='新增')
weak_count = weak_df.groupby('日期').size().reset_index(name='弱转强')
weak_count.columns = ['date', '弱转强']
strong_count = strong_df.groupby('日期').size().reset_index(name='强者恒强')
strong_count.columns = ['date', '强者恒强']

all_dates = sorted(list(set(new_count['date'].tolist() + weak_count['date'].tolist() + strong_count['date'].tolist())))
result = pd.DataFrame({'date': all_dates})
result = result.merge(new_count, on='date', how='left')
result = result.merge(weak_count, on='date', how='left')
result = result.merge(strong_count, on='date', how='left')
result = result.fillna(0)

bar = (
    Bar(init_opts=opts.InitOpts(
        width="100%",
        height="760px",
        theme=ThemeType.DARK
    ))
    .add_xaxis(result['date'].tolist())
    .add_yaxis('新增', result['新增'].tolist())
    .add_yaxis('弱转强', result['弱转强'].tolist())
    .add_yaxis('强者恒强', result['强者恒强'].tolist())
    .set_global_opts(
        title_opts=opts.TitleOpts(
            title='每日成交额TOP50统计',
            subtitle='本模块统计每日进入两市成交额TOP50的新增个股数量,并筛选出T+1日、T+2日仍留存的股票,\n' 
            '然后分为两类:T日增跌幅<0,T+1日>0以及T日增跌幅>0,T+1日>0的股票'
        ),
        tooltip_opts=opts.TooltipOpts(trigger='axis'),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        datazoom_opts=[opts.DataZoomOpts()],
        legend_opts=opts.LegendOpts(pos_top='10%')
    )
)

# 点击事件
# 点击事件
# 点击事件（终极无错版）
bar.add_js_funcs("""

window.myChart = chart_""" + bar.chart_id + """;

var futureData = """ + json.dumps(future_dict, ensure_ascii=False) + """;
var newData = """ + json.dumps(dict(new_detail), ensure_ascii=False) + """;
var thresholdData = """ + threshold_json + """;

chart_""" + bar.chart_id + """.on('click', function(params) {

    if(params.seriesName !== '新增') {
        return;
    }

    var date = params.name;
    var stocks = newData[date];

    if(!stocks) {
        return;
    }

    var area = parent.document.getElementById('futureChartArea');
    area.innerHTML = "";

    var threshold = thresholdData[date] || 0;
    area.insertAdjacentHTML('beforeend', parent.buildDateHeaderHtml(date, threshold, ''));

    var cardRow = parent.document.createElement('div');
    cardRow.className = 'card-row';
    area.appendChild(cardRow);

    stocks.forEach(function(item) {

        var future = futureData[String(date)][String(item.stock)];

        if(!future) {
            return;
        }

        var trimmed = parent.trimFutureRows(future, parent.MAX_DISPLAY_DAY || 10);
        var wrap = parent.document.createElement('div');
        wrap.className = 'stock-card-wrap';
        wrap.innerHTML = parent.buildStockCardHtml(item.name, item.stock, trimmed);
        cardRow.appendChild(wrap);

    });

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

print("Dashboard 生成完成！")
print(f"最新交易日: {latest_trade_date}，累计为正: {len(positive_cum_rows)} 只")
print(f"  -> 入选日共 {LOOKBACK_DAYS} 天: {last_n_selection_dates[0]} ~ {last_n_selection_dates[-1]}")
print("  -> positive_cum_data.js / positive_cum.html 已更新")

# 更新 index.html 中 JS 缓存参数，避免浏览器仍加载旧的 10 日数据
cache_ver = f"{latest_trade_date}-d{LOOKBACK_DAYS}"
with open("index.html", "r", encoding="utf-8") as f:
    index_html = f.read()
new_src = f"positive_cum_data.js?v={cache_ver}"
if "positive_cum_data.js?v=" in index_html:
    i = index_html.find("positive_cum_data.js?v=")
    j = index_html.find('"', i)
    index_html = index_html[:i] + new_src + index_html[j:]
else:
    index_html = index_html.replace("positive_cum_data.js", new_src, 1)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(index_html)
print(f"  -> index.html 已刷新脚本缓存参数: ?v={cache_ver}")
            