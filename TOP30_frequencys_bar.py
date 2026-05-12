import pandas as pd
import matplotlib.pyplot as plt

# =====================
# 全局设置
# =====================

# 中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']

# 解决负号乱码
plt.rcParams['axes.unicode_minus'] = False

# =====================
# 读取数据
# =====================

df = pd.read_csv(
    "统计任务-3.23至今两市每日成交额TOP50以及TOP50新增统计(2).csv"
)

# =====================
# 数据统计
# =====================

# 统计股票出现次数
count_series = df['name'].value_counts()

# 取前30
top30 = count_series.head(30)

# =====================
# 创建 Figure 和 Axes
# =====================

fig, ax = plt.subplots(
    figsize=(5.4, 3.6),
    dpi=200
)

top30.index = [
    '\n'.join(name)
    for name in top30.index
]

# =====================
# 绘图
# =====================

top30.plot(
    kind='bar',
    ax=ax
)

# =====================
# 图表设置
# =====================

ax.set_title(
    "出现频率TOP30股票",
    fontsize=10
)

ax.set_xlabel(
    "股票名称",
    fontsize=7
)

ax.set_ylabel(
    "出\n现\n次\n数",
    rotation=0,       # 文字不旋转
    labelpad=8,      # 增加文字和Y轴的距离
    va='center',      # 垂直居中
    ha='right',       # 水平靠右
    fontsize=8
)

# X轴旋转
ax.tick_params(
    axis='x',
    rotation=0,
    labelsize=8
)

# Y轴字体大小
ax.tick_params(
    axis='y',
    labelsize=9
)

# 网格（专业图常用）
ax.grid(
    linestyle='--',
    alpha=0.3
)

# 自动布局
fig.tight_layout()

# =====================
# 保存高清图片（推荐）
# =====================

fig.savefig(
    "Top30出现频率.png",
    dpi=300,
    bbox_inches='tight'
)

# 显示图像
plt.show()