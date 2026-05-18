import pandas as pd
import matplotlib.pyplot as plt

# =====================
# 中文字体
# =====================

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# =====================
# 读取“新增股票”数据
# =====================

df_new = pd.read_csv(
    "统计任务-3.23至今两市每日成交额TOP50以及TOP50新增统计(1).csv"
)

# =====================
# 统计每日新增数量
# =====================

daily_new = (
    df_new.groupby('date')['stock']
    .count()
)

# =====================
# 创建图表
# =====================

fig, ax = plt.subplots(
    figsize=(5, 3.3),
    dpi=200
)

# =====================
# 绘图
# =====================

daily_new.plot(
    kind='line',
    marker='o',
    ax=ax
)

# =====================
# 图表设置
# =====================

ax.set_title(
    "每日Top50新增股票数量",
    fontsize=10
)

ax.set_xlabel(
    "日期",
    fontsize=8
)

ax.set_ylabel(
    "新增数量",
    fontsize=8
)

ax.grid(
    linestyle='--',
    alpha=0.3
)

ax.tick_params(
    axis='x',
    rotation=45,
    labelsize=8
)

# 自动布局
fig.tight_layout()

# 保存高清图片
fig.savefig(
    "每日Top50新增数量.png",
    dpi=300,
    bbox_inches='tight'
)

plt.show()