import pandas as pd
import matplotlib.pyplot as plt

# =====================
# 中文字体
# =====================

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# =====================
# 读取数据
# =====================

df = pd.read_csv(
    "统计任务-3.23至今两市每日成交额TOP50以及TOP50新增统计(2).csv"
)

# =====================
# 计算平均成交额
# =====================

top_amount = (
    df.groupby('name')['amount']
    .mean()
    .sort_values(ascending=False)
    .head(15)
    / 1e8
)

# 中文竖排
top_amount.index = [
    '\n'.join(stock)
    for stock in top_amount.index
]

# =====================
# 创建图表
# =====================

fig, ax = plt.subplots(
    figsize=(5, 3),
    dpi=200
)

# =====================
# 绘图
# =====================

top_amount.plot(
    kind='bar',
    ax=ax
)

# =====================
# 图表设置
# =====================

ax.set_title(
    "平均成交额最高股票（亿元）",
    fontsize=10
)

ax.set_xlabel(
    "股票名称",
    fontsize=8
)

# ax.set_ylabel(
#     "亿\n元",
#     rotation=0,
#     labelpad=8,
#     fontsize=8
# )

ax.grid(
    linestyle='--',
    alpha=0.3
)

ax.tick_params(
    axis='x',
    rotation=0,
    labelsize=9
)

# 自动布局
fig.tight_layout()

# 保存高清图片
fig.savefig(
    "平均成交额最高股票.png",
    dpi=300,
    bbox_inches='tight'
)

plt.show()