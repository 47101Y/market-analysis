"""可选独立脚本：宽表转换已并入 index.py 的 build_wide_from_future()。"""
import pandas as pd

# 1. 读取原始数据
df = pd.read_csv('new_stock_future_10days.csv', encoding='utf-8-sig')

# 2. 确保 day_seq 是数字（防止排序出错）
df['day_seq'] = df['day_seq'].astype(int)

# 3. 按 add_date, name, stock, industry, day_seq 排序，保证顺序正确
df = df.sort_values(['add_date', 'name', 'stock', 'industry', 'day_seq'])

# 4. 用 day_seq 给列名加后缀（day_seq=0 → 不加后缀，day_seq=1 → 加1，以此类推）
df['open_col'] = df.apply(lambda row: f'open{row["day_seq"] if row["day_seq"] != 0 else ""}', axis=1)
df['close_col'] = df.apply(lambda row: f'close{row["day_seq"] if row["day_seq"] != 0 else ""}', axis=1)
df['pct_col'] = df.apply(lambda row: f'today_pct{row["day_seq"] if row["day_seq"] != 0 else ""}', axis=1)

# 5. 分别把 open / close / today_pct 按 day_seq 展开
# 先做 open 的宽表
df_open = df.pivot_table(
    index=['add_date', 'name', 'stock', 'industry'],
    columns='open_col',
    values='open',
    aggfunc='first'
).reset_index()

# 再做 close 的宽表
df_close = df.pivot_table(
    index=['add_date', 'name', 'stock', 'industry'],
    columns='close_col',
    values='close',
    aggfunc='first'
).reset_index()

# 再做 today_pct 的宽表
df_pct = df.pivot_table(
    index=['add_date', 'name', 'stock', 'industry'],
    columns='pct_col',
    values='today_pct',
    aggfunc='first'
).reset_index()

# 6. 把三个宽表合并起来（按 add_date+name+stock+industry 对齐）
df_merged = pd.merge(df_open, df_close, on=['add_date', 'name', 'stock', 'industry'], how='left')
df_merged = pd.merge(df_merged, df_pct, on=['add_date', 'name', 'stock', 'industry'], how='left')

# 7. 按你要求的列顺序重新排列
# 先固定的列
fixed_cols = ['add_date', 'stock', 'name', 'industry']
# 然后是 day_seq 从0到10的 open/close/today_pct
dynamic_cols = []
for i in range(11):  # 0~10
    suffix = str(i) if i != 0 else ""
    dynamic_cols.extend([f'open{suffix}', f'close{suffix}', f'today_pct{suffix}'])

# 组合成最终的列顺序
final_cols = fixed_cols + dynamic_cols
# 确保列存在（防止有的 day_seq 缺失）
final_cols = [col for col in final_cols if col in df_merged.columns]
df_final = df_merged[final_cols]

# 8. 查看结果（前5行）
print(df_final.head())

# 9. 保存为新的宽表格 CSV
df_final.to_csv('wide_stock_data.csv', index=False, encoding='utf-8-sig')