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
        legend_opts=opts.LegendOpts(pos_top='5%')
    )
)

# =========================
# 第二部分：行业热力图（行业出现次数）
# =========================

industry_total = pd.concat([
    new_df[['industry']],
    weak_df[['行业']].rename(columns={'行业':'industry'}),
    strong_df[['行业']].rename(columns={'行业':'industry'})
])

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
            max_=int(industry_count['count'].max())
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
    width='1400px',
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

page = Page(layout=Page.SimplePageLayout)

page.add(bar)
page.add(heat_bar)
page.add(timeline)

# 输出网页
page.render('index.html')

print('网页生成成功：index.html')