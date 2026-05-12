from pyecharts.charts import Bar
from pyecharts import options as opts

bar = (
    Bar()
    .add_xaxis(["A", "B", "C"])
    .add_yaxis("测试", [1, 2, 3])
    .set_global_opts(
        title_opts=opts.TitleOpts(title="测试图表")
    )
)

bar.render("test.html")

print("完成")