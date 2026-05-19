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
weak_df = pd.read_csv('弱转强.csv')
strong_df = pd.read_csv('强者恒强.csv')
# 未来10日宽表（横向表格）
wide_df = pd.read_csv('wide_stock_data.csv')


# =========================
# 构建 future_dict（给前端JS用）
# =========================
future_dict = defaultdict(dict)

for _, row in wide_df.iterrows():
    add_date = str(row['add_date'])
    stock = str(row['stock'])

    dates = []
    open_vals = []
    close_vals = []
    pct_vals = []

    # T
    dates.append("T")
    open_vals.append(row['open'])
    close_vals.append(row['close'])
    pct_vals.append(row['today_pct'])

    # T+1 ~ T+10
    for i in range(1, 11):
        dates.append(f"T+{i}")
        open_vals.append(row[f'open{i}'])
        close_vals.append(row[f'close{i}'])
        pct_vals.append(row[f'today_pct{i}'])

    future_dict[add_date][stock] = {
        'name': row['name'],
        'industry': row['industry'],
        'dates': dates,
        'open': open_vals,
        'close': close_vals,
        'pct': pct_vals
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

# =========================
# 2. 注入 JS 点击事件（修复版）
# =========================
# 使用 json.dumps 确保 Python 字典完美转换为 JS 能识别的 JSON 格式（双引号）
future_data_json = json.dumps(dict(future_dict), ensure_ascii=False)
new_data_json = json.dumps(dict(new_detail), ensure_ascii=False)


# 下面是修好语法的 JS 代码
bar.add_js_funcs(f"""
window.futureData = {future_data_json};
window.newData = {new_data_json};

chart_{bar.chart_id}.on('click', function(params) {{
    if (params.seriesName !== '新增') return;

    var date = params.name;
    var stockList = window.newData[date];
    if (!stockList || stockList.length === 0) return;

    var area = parent.document.getElementById('futureChartArea');
    if (!area) return;
    area.innerHTML = '';

    var html = [];
    html.push('<div style="color:white; padding:10px;">');
    html.push('<h4 style="text-align:center;">' + date + ' 未来10天数据</h4>');
    html.push('<div style="overflow-x:auto;">');
    html.push('<table style="width:100%; min-width:1200px; border-collapse:collapse; text-align:center; font-size:13px;">');

    // 表头
    html.push('<tr style="background:#333;">');
    html.push('<th style="padding:8px; border:1px solid #666;">股票</th>');
    html.push('<th style="padding:8px; border:1px solid #666;">行业</th>');
    
    var firstStock = stockList[0].stock;
    var first = window.futureData[date][firstStock];
    
    // 动态生成日期表头
    for(var i = 0; i < first.dates.length; i++){{
        html.push('<th style="padding:8px; border:1px solid #666;">' + first.dates[i] + '开</th>');
        html.push('<th style="padding:8px; border:1px solid #666;">' + first.dates[i] + '收</th>');
        html.push('<th style="padding:8px; border:1px solid #666;">' + first.dates[i] + '涨跌幅</th>');
    }}

    html.push('</tr>');

    // 每只股票一行
    for(var s = 0; s < stockList.length; s++){{
        var item = stockList[s];
        var fut = window.futureData[date][item.stock];
        if(!fut) continue;

        html.push('<tr>');
        html.push('<td style="padding:8px; border:1px solid #444;">' + fut.name + '</td>');
        html.push('<td style="padding:8px; border:1px solid #444;">' + fut.industry + '</td>');

        for(var i = 0; i < fut.dates.length; i++){{
            var o = fut.open[i];
            var c = fut.close[i];
            var p = fut.pct[i];
            var color = p > 0 ? '#ff4d4f' : (p < 0 ? '#52c41a' : '#fff');

            html.push('<td style="padding:8px; border:1px solid #444;">' + o + '</td>');
            html.push('<td style="padding:8px; border:1px solid #444;">' + c + '</td>');
            html.push('<td style="padding:8px; border:1px solid #444;color:' + color + ';">' + p + '</td>');
        }}

        html.push('</tr>');
    }}

    html.push('</table></div></div>');
    area.innerHTML = html.join('');
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