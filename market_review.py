import pandas as pd

from pyecharts.charts import (
    Bar,
    Page
)

from pyecharts import options as opts


df_all = pd.read_csv("连续留存样本.csv")

industry_count = (
    df_all['行业']
    .value_counts()
    .head(15)
)

bar = (
    Bar()
    .add_xaxis(
        industry_count.index.tolist()
    )
    .add_yaxis(
        "数量",
        industry_count.values.tolist()
    )
    .set_global_opts(
        title_opts=opts.TitleOpts(
            title="连续留存样本行业分布"
        )
    )
)

page = Page()

page.add(bar)

page.render("市场分析.html")

print("生成完成")