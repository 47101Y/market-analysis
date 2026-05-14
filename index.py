import pandas as pd
from pyecharts.charts import Bar, Pie, Timeline, Page
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from collections import defaultdict

# =========================
# 读取数据
# =========================

new_df = pd.read_csv('每日成交额TOP50新增股票.csv')
weak_df = pd.read_csv('弱转强.csv')
strong_df = pd.read_csv('强者恒强.csv')

# =========================
# 第一部分：每日统计柱状图
# =========================

# 新增数量
new_count = (
    new_df.groupby('date')
    .size()
    .reset_index(name='新增')
)

# 弱转强数量
weak_count = (
    weak_df.groupby('日期')
    .size()
    .reset_index(name='弱转强')
)
weak_count.columns = ['date', '弱转强']

# 强者恒强数量
strong_count = (
    strong_df.groupby('日期')
    .size()
    .reset_index(name='强者恒强')
)
strong_count.columns = ['date', '强者恒强']

# 合并日期
all_dates = sorted(list(set(
    new_count['date'].tolist()
    + weak_count['date'].tolist()
    + strong_count['date'].tolist()
)))
result = pd.DataFrame({'date': all_dates})

result = result.merge(new_count, on='date', how='left')
result = result.merge(weak_count, on='date', how='left')
result = result.merge(strong_count, on='date', how='left')
result = result.fillna(0)

# 柱状图
bar = (
    Bar(init_opts=opts.InitOpts(
        width='1400px',
        height='650px',
        theme=ThemeType.DARK
    ))
    .add_xaxis(result['date'].tolist())
    .add_yaxis('新增', result['新增'].tolist())
    .add_yaxis('弱转强', result['弱转强'].tolist())
    .add_yaxis('强者恒强', result['强者恒强'].tolist())
    .set_global_opts(
        title_opts=opts.TitleOpts(
            title='每日成交额TOP50统计'
        ),
        tooltip_opts=opts.TooltipOpts(trigger='axis'),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        datazoom_opts=[opts.DataZoomOpts()],
        legend_opts=opts.LegendOpts(pos_top='10%')
    )
)





# =========================
# 第二部分：行业热力图（行业出现次数）
# =========================

industry_total =new_df[['industry']]


industry_count = (
    industry_total['industry']
    .value_counts()
    .reset_index()
)

industry_count.columns = ['industry', 'count']

heat_bar = (
    Bar(init_opts=opts.InitOpts(
        width='1400px',
        height='650px',
        theme=ThemeType.DARK
    ))
    .add_xaxis(industry_count['industry'].tolist())
    .add_yaxis(
        '出现次数',
        industry_count['count'].tolist(),
        category_gap='40%'
    )
    .set_global_opts(
        title_opts=opts.TitleOpts(
            title='行业热力分布'
        ),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=45)),
        visualmap_opts=opts.VisualMapOpts(
            max_=int(industry_count['count'].max()),
            pos_right="5%",   # 离右边 5%，往左挪，靠近主图
            pos_top="middle"  # 垂直居中，和主图对齐
        )
    )
)





# =========================
# 第三部分：行业轮动图（Timeline）
# =========================

# 使用新增数据做行业轮动
rotation_df = new_df.copy()

rotation_group = rotation_df.groupby(['date', 'industry']).size().reset_index(name='count')

# 时间轴
timeline = Timeline(init_opts=opts.InitOpts(
    width='120px',
    height='700px',
    theme=ThemeType.DARK
))

for d in sorted(rotation_group['date'].unique()):

    temp = rotation_group[
        rotation_group['date'] == d
    ].sort_values(by='count', ascending=False)

    bar_day = (
        Bar()
        .add_xaxis(temp['industry'].tolist())
        .add_yaxis('行业数量', temp['count'].tolist())
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title=f'{d} 行业轮动'
            ),
            xaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(rotate=45)
            ),
            visualmap_opts=opts.VisualMapOpts(
                max_=int(temp['count'].max())
            )
        )
    )

    timeline.add(bar_day, time_point=d)

# 自动播放
timeline.add_schema(
    play_interval=1200,
    is_auto_play=True,
    is_loop_play=False
)





# =========================
# 页面组合
# =========================

html = f"""
<!DOCTYPE html>
<html>

<head>
    <meta charset="UTF-8">
    <title>市场分析Dashboard</title>

    <script src="https://assets.pyecharts.org/assets/v5/echarts.min.js"></script>

    <style>

        body {{
            background-color: #111;
            color: white;
            font-family: Arial;
        }}

        .tab {{
            overflow: hidden;
            border-bottom: 1px solid #333;
            background-color: #1b1b1b;
            padding: 10px;
        }}

        .tab button {{
            background-color: #222;
            color: white;
            float: left;
            border: none;
            outline: none;
            cursor: pointer;
            padding: 12px 18px;
            margin-right: 10px;
            border-radius: 8px;
            transition: 0.3s;
        }}

        .tab button:hover {{
            background-color: #444;
        }}

        .tab button.active {{
            background-color: #666;
        }}

        .chart-container {{
            display: none;
            padding: 20px;
        }}

    </style>

</head>

<body>

<div class="tab">

    <button class="tablinks"
        onclick="showChart(event, 'chart1')">
        每日统计
    </button>

    <button class="tablinks"
        onclick="showChart(event, 'chart2')">
        行业热力
    </button>

    <button class="tablinks"
        onclick="showChart(event, 'chart3')">
        行业轮动
    </button>

</div>

<div id="chart1" class="chart-container">
    {bar.render_embed()}
</div>

<div id="chart2" class="chart-container">
    {heat_bar.render_embed()}
</div>

<div id="chart3" class="chart-container">
    {timeline.render_embed()}
</div>

<script>

function showChart(evt, chartID) {{

    let containers =
        document.getElementsByClassName("chart-container");

    for (let i = 0; i < containers.length; i++) {{
        containers[i].style.display = "none";
    }}

    let tablinks =
        document.getElementsByClassName("tablinks");

    for (let i = 0; i < tablinks.length; i++) {{
        tablinks[i].className =
            tablinks[i].className.replace(" active", "");
    }}

    document.getElementById(chartID).style.display = "block";

    evt.currentTarget.className += " active";
}}

// 默认显示第一页
document.getElementById("chart1").style.display = "block";

</script>

</body>
</html>
"""
# 写入文件，生成 index.html
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)