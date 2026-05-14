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
        width='1680px',
        height='7800px',
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
    width='1680px',
    height='780px',
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

# =========================
# 分别生成三个图表页面
# =========================

bar.render("bar.html")

heat_bar.render("heat.html")

timeline.render("timeline.html")


# =========================
# 主页面
# =========================

html = """
<!DOCTYPE html>
<html>

<head>
    <meta charset="UTF-8">
    <title>市场分析Dashboard</title>

    <style>

        body{
            margin:0;
            background:#111;
            font-family:Arial;
        }

        .tab{
            background:#1b1b1b;
            padding:15px;
        }

        .tab button{

            background:#333;
            color:white;
            border:none;
            padding:12px 20px;
            margin-right:10px;
            border-radius:8px;
            cursor:pointer;
            font-size:15px;
        }

        .tab button:hover{
            background:#555;
        }

        iframe{
            width:100%;
            height:900px;
            border:none;
        }

    </style>
</head>


<body>
<div class="tab">

    <button onclick="changePage('bar.html')">
        每日成交额TOP50新增个股统计
    </button>

    <button onclick="changePage('heat.html')">
        新增股票行业热力分析
    </button>

    <button onclick="showImage()">
        新增股票行业热力图
    </button>

    <button onclick="changePage('timeline.html')">
        新增股票行业轮动
    </button>

</div>

<div
    id="description"
    style="
        color:white;
        padding:20px 30px;
        font-size:16px;
        line-height:1.8;
        background:#1b1b1b;
        border-bottom:1px solid #333;
    "
>

    <h2 style="margin-top:0;">
        每日成交额TOP50新增个股统计
    </h2>

    <p>
        本模块统计每日进入两市成交额TOP50的新增个股数量，
        并筛选出T+1日、T+2日仍留存的股票，然后分为两类：T日增跌幅<0,T+1日>0的股票（弱转强）；T日增跌幅>0,T+1日>0的股票（强者恒强）。
    </p>

    <p>
        通过该指标可以观察市场风险偏好变化、
        情绪周期切换以及资金抱团方向。
    </p>

</div>



<iframe
    id="frame"
    src="bar.html">
</iframe>



<div
    id="imageBox"
    style="
        display:none;
        text-align:center;
        padding:20px;
        position:relative;
        z-index:9999;
        background:#111;
        min-height:100vh;
    "
>

    <img
        src="./new_heatmap.png"
        style="
            max-width:65%;
            height:auto;
            border-radius:12px;
            box-shadow:0 0 20px rgba(255,255,255,0.15);
        "
    >

</div>

<script>

function changePage(page){

    document.getElementById("frame").style.display = "block";

    document.getElementById("imageBox").style.display = "none";

    document.getElementById("frame").src = page;

}

function showImage(){

    document.getElementById("frame").style.display = "none";

    document.getElementById("imageBox").style.display = "block";

}

</script>

</body>
</html>
"""

# 生成主页面

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard 生成完成！")