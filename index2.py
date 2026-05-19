import pandas as pd
from pyecharts.charts import Bar, Pie, Timeline, Page
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from collections import defaultdict
from pyecharts.globals import CurrentConfig

CurrentConfig.ONLINE_HOST = "https://assets.pyecharts.org/assets/v5/"

# =========================
# 读取数据
# =========================
new_df = pd.read_csv('每日成交额TOP50新增股票.csv')
weak_df = pd.read_csv('弱转强.csv')
strong_df = pd.read_csv('强者恒强.csv')
# 未来10日宽表（横向表格）
wide_df = pd.read_csv('wide_stock_data.csv')

# 构建 future_dict（给前端JS用）
future_dict = defaultdict(dict)

for _, row in wide_df.iterrows():
    add_date = str(row['add_date'])
    stock = str(row['stock'])

    # 日期表头：T, T+1 ... T+10
    dates = [f"T+{i}" if i != 0 else "T" for i in range(11)]

    # 开盘价 open ~ open10
    opens = [row[f'open{i}' if i != 0 else 'open'] for i in range(11)]
    # 收盘价 close ~ close10
    closes = [row[f'close{i}' if i != 0 else 'close'] for i in range(11)]
    # 涨跌幅 today_pct ~ today_pct10
    pcts = [row[f'today_pct{i}' if i != 0 else 'today_pct'] for i in range(11)]

    future_dict[add_date][stock] = {
        "name": row['name'],
        "industry": row['industry'],
        "dates": dates,
        "open": opens,
        "close": closes,
        "pct": pcts
    }

# =========================
# 弱转强、强者恒强、新增股票详情字典（保持不变）
# =========================
weak_detail = defaultdict(list)
for _, row in weak_df.iterrows():
    date = row['日期']
    stock_info = f"""
                    股票代码：{row['股票代码']}
                    名称：{row['名称']}
                    行业：{row['行业']}
                    成交金额（亿）：{row['成交金额（亿）']}

                    T日收盘价：{row['T日收盘价']}
                    T-1日收盘价：{row['T-1日收盘价']}

                    T日涨跌幅：{row['T日涨跌幅']}
                    T+1日涨跌幅：{row['T+1日涨跌幅']}
                    T+2日涨跌幅：{row['T+2日涨跌幅']}
    """
    weak_detail[date].append(stock_info)

strong_detail = defaultdict(list)
for _, row in strong_df.iterrows():
    date = row['日期']
    stock_info = f"""
                    股票代码：{row['股票代码']}
                    名称：{row['名称']}
                    行业：{row['行业']}
                    成交金额（亿）：{row['成交金额（亿）']}

                    T日收盘价：{row['T日收盘价']}
                    T-1日收盘价：{row['T-1日收盘价']}

                    T日涨跌幅：{row['T日涨跌幅']}
                    T+1日涨跌幅：{row['T+1日涨跌幅']}
                    T+2日涨跌幅：{row['T+2日涨跌幅']}
    """
    strong_detail[date].append(stock_info)

new_detail = defaultdict(list)
for _, row in new_df.iterrows():
    date = row['date']
    new_detail[date].append({
        'stock': str(row['stock']),
        'name': row['name']
    })

# =========================
# 第一部分：每日统计柱状图
# =========================
new_count = new_df.groupby('date').size().reset_index(name='新增')
weak_count = weak_df.groupby('日期').size().reset_index(name='弱转强')
weak_count.columns = ['date', '弱转强']
strong_count = strong_df.groupby('日期').size().reset_index(name='强者恒强')
strong_count.columns = ['date', '强者恒强']

all_dates = sorted(set(new_count['date'].tolist() + weak_count['date'].tolist() + strong_count['date'].tolist()))
result = pd.DataFrame({'date': all_dates})
result = result.merge(new_count, on='date', how='left')
result = result.merge(weak_count, on='date', how='left')
result = result.merge(strong_count, on='date', how='left')
result = result.fillna(0)

bar = (
    Bar(init_opts=opts.InitOpts(
        width='1680px',
        height='780px',
        theme=ThemeType.DARK
    ))
    .add_xaxis(result['date'].tolist())
    .add_yaxis('新增', result['新增'].tolist())
    .add_yaxis('弱转强', result['弱转强'].tolist())
    .add_yaxis('强者恒强', result['强者恒强'].tolist())
    .set_global_opts(
        title_opts=opts.TitleOpts(
            title='每日成交额TOP50统计',
            subtitle='本模块统计每日进入两市成交额TOP50的新增个股数量,并筛选出T+1日、T+2日仍留存的股票,'
                     '然后分为两类:T日增跌幅<0,T+1日>0以及T日增跌幅>0,T+1日>0的股票'
        ),
        tooltip_opts=opts.TooltipOpts(trigger='axis'),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        datazoom_opts=[opts.DataZoomOpts()],
        legend_opts=opts.LegendOpts(pos_top='10%')
    )
)

# 点击事件：生成宽表格（指标为行，日期为列）
bar.add_js_funcs(f"""
var futureData = {dict(future_dict)};
var newData = {dict(new_detail)};

chart_{bar.chart_id}.on('click', function(params) {{
    if (params.seriesName !== '新增') return;

    var clickDate = params.name;
    var stocks = newData[clickDate];
    if (!stocks || stocks.length === 0) return;

    var area = parent.document.getElementById('futureChartArea');
    area.innerHTML = "";

    var bigTable = parent.document.createElement('div');
    bigTable.style.padding = '10px';
    bigTable.style.color = 'white';
    area.appendChild(bigTable);

    var html = `
    <h3 style="text-align:center;">${{clickDate}} 未来10天表现</h3>
    <div style="overflow-x:auto;">
    <table style="width:100%;min-width:1200px;border-collapse:collapse;text-align:center;font-size:13px;">
        <tr style="background:#333;">
            <th style="padding:8px;border:1px solid #666;">股票名称</th>
            <th style="padding:8px;border:1px solid #666;">行业</th>
    `;

    var firstStock = futureData[clickDate][stocks[0].stock];
    firstStock.dates.forEach(d => {{
        html += `<th style="padding:8px;border:1px solid #666;">${{d}}</th>`;
    }});
    html += `</tr>`;

    stocks.forEach(item => {{
        var fut = futureData[clickDate][item.stock];
        if (!fut) return;

        html += `<tr>`;
        html += `<td style="padding:8px;border:1px solid #444;">${{fut.name}}</td>`;
        html += `<td style="padding:8px;border:1px solid #444;">${{fut.industry}}</td>`;

        for (var i = 0; i < fut.dates.length; i++) {{
            var o = fut.open[i];
            var c = fut.close[i];
            var p = fut.pct[i];
            var color = p > 0 ? '#ff4d4f' : (p < 0 ? '#52c41a' : '#fff');

            html += `
            <td style="padding:8px;border:1px solid #444;line-height:1.5;">
                开:${{o}}<br>收:${{c}}<br><span style="color:${{color}}">${{p}}</span>
            </td>`;
        }}

        html += `</tr>`;
    }});

    html += `</table></div>`;
    bigTable.innerHTML = html;
}});
""")
# =========================
# 第二部分：行业热力图
# =========================
industry_count = new_df['industry'].value_counts().reset_index()
industry_count.columns = ['industry', 'count']

heat_bar = (
    Bar(init_opts=opts.InitOpts(
        width='1680px',
        height='780px',
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
timeline = Timeline(init_opts=opts.InitOpts(width='1680px', height='780px', theme=ThemeType.DARK))

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
                                            pos_right="5%",
                                            pos_top="middle")
        )
    )
    timeline.add(bar_day, time_point=d)

timeline.add_schema(play_interval=1400, is_auto_play=True, is_loop_play=False)

# =========================
# 输出三个图表
# =========================
bar.render("bar.html")
heat_bar.render("heat.html")
timeline.render("timeline.html")

print("Dashboard 生成完成！")