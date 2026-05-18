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
future_df = pd.read_csv('new_stock_future_10days.csv')


# =========================
# 未来10日走势数据
# =========================

future_dict = defaultdict(dict)

for (d, stock), group in future_df.groupby(['add_date', 'stock']):

    group = group.sort_values(by='trade_date')

    future_dict[str(d)][str(stock)] = {

        'dates': group['trade_date'].tolist(),

        'open': group['open'].tolist(),

        'close': group['close'].tolist(),

        'pct': ((group['close'] - group['open']) / group['open']).round(2).tolist()
    }



# =========================
#弱转强详情字典
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

    stock_info = f"""
                    股票代码：{row['stock']}
                    名称：{row['name']}
                    行业：{row['industry']}
                    成交金额（亿）：{row['amount']}

                    T日收盘价：{row['close']}
                    T-1日收盘价：{row['pre_close']}

                    T日涨跌幅：{row['pct']}

                    T+1日是否留存TOP50：{'是' if row['day2_in_top50'] else '否'}
                    T+2日是否留存TOP50：{'是' if row['day3_in_top50'] else '否'}

                    T+1日涨跌幅：{row['day2_pct']}
                    T+2日涨跌幅：{row['day3_pct']}
    """
    new_detail[date].append({

    'stock': row['stock'],

    'name': row['name']

    })




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

#创建新df
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

bar.add_js_funcs(f"""

var futureData = {dict(future_dict)};

var newData = {dict(new_detail)};


// ======================
// 点击柱体事件
// ======================

chart_{bar.chart_id}.on('click', function(params) {{

    // 只处理 “新增”
    if(params.seriesName !== '新增'){{
        return;
    }}

    var date = params.name;

    var stocks = newData[date];

    if(!stocks){{
        return;
    }}

    // 找到下方区域
    var area = parent.document.getElementById('futureChartArea');

    // 清空旧内容
    area.innerHTML = "";

    // 遍历股票
    stocks.forEach(function(item, index){{

        // 获取未来数据
        var future = futureData[String(date)][String(item.stock)];

        if(!future){{
            return;
        }}

        // 创建卡片
        var div = parent.document.createElement('div');

        div.className = 'futureChartBox';

        area.appendChild(div);

        // ======================
        // 生成HTML表格
        // ======================

        var html = `

        <div style="
            color:white;
            padding:10px;
        ">

        <h3 style="
            text-align:center;
            margin-bottom:15px;
        ">
        ${{item.name}}
        </h3>

        <table style="
            width:100%;
            border-collapse:collapse;
            text-align:center;
            font-size:13px;
        ">

        <tr style="background:#333;">

            <th style="padding:6px;border:1px solid #555;">日期</th>

            <th style="padding:6px;border:1px solid #555;">开盘价</th>

            <th style="padding:6px;border:1px solid #555;">收盘价</th>

        </tr>

        `;

        for(var i=0; i<future.dates.length; i++){{

            html += `

            <tr>

                <td style="padding:6px;border:1px solid #444;">
                    ${{future.dates[i]}}
                </td>

                <td style="padding:6px;border:1px solid #444;">
                    ${{future.open[i]}}
                </td>

                <td style="padding:6px;border:1px solid #444;">
                    ${{future.close[i]}}
                </td>

            </tr>

            `;
        }}

        html += `</table></div>`;

        // 写入盒子
        div.innerHTML = html;

    }});

}});

""")







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
        height='780px',
        theme=ThemeType.DARK
    ))
    .add_xaxis(industry_count['industry'].tolist())
    .add_yaxis(
        '新增成交额TOP50股票行业总计出现次数',
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
                max_=int(temp['count'].max()),
                pos_right="5%",   # 离右边 5%，往左挪，靠近主图
                pos_top="middle"  # 垂直居中，和主图对齐
            )
        )
    )

    timeline.add(bar_day, time_point=d)

# 自动播放
timeline.add_schema(
    play_interval=1400,
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
    <script src="https://assets.pyecharts.org/assets/v5/echarts.min.js"></script>
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

    /* 新增：左右布局 */

    .main-container{

        position:relative;

        width:100%;

        height:820px;
    }

    iframe{

        width:100%;

        height:100%;

        border:none;
    }
    #futureChartArea{

    width:100%;

    background:#111;

    display:flex;

    flex-wrap:wrap;

    justify-content:center;

    gap:20px;

    padding:20px;

    box-sizing:border-box;
    }

    .futureChartBox{

        width:520px;

        height:420px;

        background:#1b1b1b;

        border-radius:12px;

        padding:10px;
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




<div class="main-container"
     id="mainContainer"
>

    <iframe
        id="frame"
        src="bar.html">
    </iframe>

</div>

<!-- 未来走势区域 -->
<div id="futureChartArea"></div>



<!-- 放图片 -->
<div
    id="imageBox"
    style="
        display:none;

        width:100%;
        height:900px;

        background:#111;

        justify-content:center;
        align-items:flex-star;

        padding:20px;
        box-sizing:border-box;
    "
>
    <img
        src="./new_heatmap.png"
        style="
            max-width:90%;
            max-height:800px; /* 限制最大高度，避免撑破容器 */
            height:auto;
            border-radius:12px;
            box-shadow:0 0 20px rgba(255,255,255,0.15);
        "
    >
</div>



<script>
function changePage(page){

    // 显示主图区域
    document.getElementById("mainContainer").style.display = "block";

    // 隐藏图片
    document.getElementById("imageBox").style.display = "none";

    // 切换 iframe
    document.getElementById("frame").src = page;

    // ======================
    // 控制 futureChartArea
    // ======================

    // bar 页面显示
    if(page === "bar.html"){

        document.getElementById("futureChartArea").style.display = "flex";

    }

    // 其它页面隐藏
    else{

        document.getElementById("futureChartArea").style.display = "none";

    }

}


function showImage(){

    // 整个主图区域消失
    document.getElementById("mainContainer").style.display = "none";

    // 显示热力图
    document.getElementById("imageBox").style.display = "flex";

}


</script>


</body>
</html>
"""

# 生成主页面

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard 生成完成！")