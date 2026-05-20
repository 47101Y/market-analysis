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
future_df = pd.read_csv('new_stock_future_10days.csv')


#宽表格重现
df = pd.read_csv("wide_stock_data.csv")


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
            "open": row[f'open'],
            "close": row[f'close'],
            "pct": row[f'today_pct'],
            "cum_pct": (row[f'close']-row[f'open'])/row[f'open']
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


# =========================
# 强者恒强详情字典
# =========================

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
        height="820px",
        bg_color="#111111",
        theme=ThemeType.DARK
    ))
    .add_xaxis(result['date'].tolist())
    .add_yaxis('新增', result['新增'].tolist())
    .add_yaxis('弱转强', result['弱转强'].tolist())
    .add_yaxis('强者恒强', result['强者恒强'].tolist())
    .set_global_opts(
        title_opts=opts.TitleOpts(
            title='每日成交额TOP50统计',
            subtitle='本模块统计每日进入两市成交额TOP50的新增个股数量,并筛选出T+1日、T+2日仍留存的股票,' \
            '然后分为两类:T日增跌幅<0,T+1日>0以及T日增跌幅>0,T+1日>0的股票'
        ),
        tooltip_opts=opts.TooltipOpts(trigger='axis'),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        datazoom_opts=[opts.DataZoomOpts()],
        legend_opts=opts.LegendOpts(pos_top='10%')
    )
)

# 点击事件
bar.add_js_funcs(f"""

// ======================
// 暴露 chart 给父页面
// ======================

window.myChart = chart_{bar.chart_id};

// ======================
// 数据
// ======================

var futureData = {json.dumps(future_dict, ensure_ascii=False)};
var newData = {json.dumps(dict(new_detail), ensure_ascii=False)};

chart_{bar.chart_id}.on('click', function(params) {{

    if(params.seriesName !== '新增') {{
        return;
    }}

    var date = params.name;

    var stocks = newData[date];

    if(!stocks) {{
        return;
    }}

    var area = parent.document.getElementById('futureChartArea');

    area.innerHTML = "";

    stocks.forEach(function(item) {{

        var future = futureData[String(date)][String(item.stock)];

        if(!future) {{
            return;
        }}

        var div = parent.document.createElement('div');

        div.style.marginBottom = '30px';

        area.appendChild(div);

        var html = `

        <div style="
            background:#1f1f1f;
            padding:15px;
            border-radius:10px;
            color:white;
        ">

        <h3 style="
            text-align:center;
            margin-bottom:15px;
            color:#ffd666;
        ">
            ${{item.name}}（${{item.stock}}）
        </h3>

        <table style="
            width:100%;
            border-collapse:collapse;
            text-align:center;
            font-size:13px;
        ">

        <tr style="background:#333;">

            <th style="padding:8px;border:1px solid #555;">
                第N日
            </th>

            <th style="padding:8px;border:1px solid #555;">
                开盘价
            </th>

            <th style="padding:8px;border:1px solid #555;">
                收盘价
            </th>

            <th style="padding:8px;border:1px solid #555;">
                自T+1日涨跌幅
            </th>

        </tr>
        `;

        future.forEach(function(row) {{


            html += `

            <tr>

                <td style="
                    padding:6px;
                    border:1px solid #444;
                ">
                    ${{row.day}}
                </td>

                <td style="
                    padding:6px;
                    border:1px solid #444;
                ">
                    ${{row.open}}
                </td>

                <td style="
                    padding:6px;
                    border:1px solid #444;
                ">
                    ${{row.close}}
                </td>


                <td style="
                    padding:6px;
                    border:1px solid #444;
                    color:${{row.cum_pct > 0 ? '#ff4d4f' : '#52c41a'}};
                    font-weight:bold;
                ">
                     ${{(row.cum_pct * 100).toFixed(2)}}%
</td>

            </tr>
            `;
        }});

        html += `
        </table>
        </div>
        `;

        div.innerHTML = html;

    }});

}});
""")

# =========================
# 第二部分：行业热力图
# =========================

industry_count = new_df['industry'].value_counts().reset_index()
industry_count.columns = ['industry', 'count']

heat_bar = (
    Bar(init_opts=opts.InitOpts(
        width="100%",
        height="820px",
        bg_color="#111111",
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
                                                    height="820px",
                                                    bg_color="#111111", 
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
timeline.render("timeline.html")

print("Dashboard 生成完成！")