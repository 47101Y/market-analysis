import os
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import akshare as ak
import pandas as pd
from tqdm import tqdm
import time

start_date = "20240323"
end_date = "20240430"   # 可以自己改

result = []

# 生成日期序列（交易日简单处理版）
dates = pd.date_range(start=start_date, end=end_date)

prev_top50 = None

for date in tqdm(dates):
    date_str = date.strftime("%Y%m%d")

    try:
        # ⭐ 一次性获取“当天全市场数据”
        df = ak.stock_zh_a_spot_em()

        if df.empty:
            continue

        # 只保留需要的列
        df = df[['代码', '成交额']].copy()
        df.columns = ['stock', 'amount']

        # 转数值（防止字符串问题）
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        # 去掉空值
        df = df.dropna(subset=['amount'])

        # 取前50
        today_top50 = df.sort_values(by='amount', ascending=False).head(50)

        # 第一天不计算
        if prev_top50 is None:
            prev_top50 = today_top50
            continue

        # 找新增
        new_df = today_top50[~today_top50['stock'].isin(prev_top50['stock'])].copy()

        # 加日期
        new_df['date'] = date_str

        result.append(new_df)

        # 更新“昨天”
        prev_top50 = today_top50

        time.sleep(0.5)  # ⭐防止被封

    except Exception as e:
        print(f"错误日期: {date_str}", e)
        continue

# 合并结果
if result:
    final_df = pd.concat(result, ignore_index=True)
    final_df.to_csv("新增股票_优化版.csv", index=False)
    print("完成！")
else:
    print("没有数据")