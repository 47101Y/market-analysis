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

bar.add_js_funcs("""
var futureData = __futureData__;
var newData = __newData__;

chart_ __chartId__.on('click', function(params) {
    if (params.seriesName !== '新增') return;

    var date = params.name;
    var stockList = newData[date];
    if (!stockList || stockList.length === 0) return;

    var area = parent.document.getElementById('futureChartArea');
    area.innerHTML = '';

    // 开始构建表格
    var tableHTML = '<div style="color:white; padding:15px; font-family: sans-serif;">';
    tableHTML += '<h3 style="text-align:center; margin-bottom: 20px;">' + date + ' 未来10天详细数据</h3>';
    tableHTML += '<div style="overflow-x:auto;">';

    // 设置宽度 1800px，确保横向足够宽，不会挤在一起
    tableHTML += '<table style="width:1800px; border-collapse:collapse; text-align:center; font-size:13px; margin: 0 auto;">';

    // ================= 表头部分 =================
    tableHTML += '<tr style="background:#222; color: #ccc;">';
    tableHTML += '<th style="padding:10px; border:1px solid #444; width: 100px;">股票名称</th>';
    tableHTML += '<th style="padding:10px; border:1px solid #444; width: 100px;">所属行业</th>';

    // 获取第一只股票的数据来确定日期长度
    var first = futureData[date][stockList[0].stock];

    for(var i=0; i < first.dates.length; i++){
        var d = first.dates[i];
        // 表头改为：日期在最上，下面分两列
        tableHTML += '<th colspan="2" style="padding:5px; border:1px solid #444; background:#333;">' + d + '</th>';
    }
    tableHTML += '</tr>';

    // 第二行表头：具体的 开/收
    tableHTML += '<tr style="background:#222; color: #999;">';
    tableHTML += '<th style="padding:5px; border:1px solid #444;"></th>'; // 对应股票名
    tableHTML += '<th style="padding:5px; border:1px solid #444;"></th>'; // 对应行业
    for(var i=0; i < first.dates.length; i++){
        // 这里顺序改为：先收(左) 后开(右)，或者你可以改回 先开后收
        tableHTML += '<th style="padding:5px; border:1px solid #444; font-weight:normal;">收</th>';
        tableHTML += '<th style="padding:5px; border:1px solid #444; font-weight:normal;">开</th>';
    }
    tableHTML += '</tr>';

    // ================= 数据行部分 =================
    for(var s=0; s < stockList.length; s++){
        var item = stockList[s];
        var fut = futureData[date][item.stock];
        if(!fut) continue;

        tableHTML += '<tr style="background:#111;">';

        // 股票名和行业（固定列）
        tableHTML += '<td style="padding:8px; border:1px solid #444; font-weight:bold; color:#fff;">' + fut.name + '</td>';
        tableHTML += '<td style="padding:8px; border:1px solid #444; color:#aaa;">' + fut.industry + '</td>';

        // 循环每一天的数据
        for(var i=0; i < fut.dates.length; i++){
            var o = fut.open[i];   // 开盘
            var c = fut.close[i];  // 收盘
            var p = fut.pct[i];    // 涨跌幅
            var color = p >= 0 ? '#ff4d4f' : '#52c41a'; // 红涨绿跌

            // 为了让表格整齐，我们将 收盘 和 开盘 分别放在两个 <td> 里
            // 第一列：收盘 + 涨跌幅
            tableHTML += '<td style="padding:5px; border:1px solid #444; line-height:1.5;">';
            tableHTML += '<div style="color:#fff; font-size:12px;">' + c + '</div>'; // 收盘价白色
            tableHTML += '<div style="color:' + color + '; font-size:11px;">' + p + '%</div>'; // 涨跌幅带颜色
            tableHTML += '</td>';

            // 第二列：开盘
            tableHTML += '<td style="padding:5px; border:1px solid #444; background:#1a1a1a;">';
            tableHTML += '<div style="color:#bbb; font-size:12px;">' + o + '</div>'; // 开盘价灰色一点，区分主次
            tableHTML += '</td>';
        }
        tableHTML += '</tr>';
    }

    tableHTML += '</table></div></div>';
    area.innerHTML = tableHTML;
});
""".replace("__futureData__", json.dumps(dict(future_dict)))
 .replace("__newData__", json.dumps(dict(new_detail)))
 .replace("__chartId__", str(bar.chart_id)))


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