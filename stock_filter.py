from jqdata import *
import pandas as pd

start_date = "2026-03-23"
end_date = "2026-05-09"


# 股票列表
stock_info = get_all_securities(types=['stock'])

stocks = stock_info.index.tolist()

name_map = stock_info['display_name'].to_dict()

# 交易日
trade_days = get_trade_days(
    start_date=start_date,
    end_date=end_date
)

trade_day_str = [
    d.strftime("%Y-%m-%d")
    for d in trade_days
]



#定义分段请求函数
def get_batch_price(
    stocks,
    date,
    batch_size=500
):

    all_df = []

    for i in range(0, len(stocks), batch_size):

        batch = stocks[i:i+batch_size]

        df = get_price(
            batch,
            end_date=date,
            frequency='daily',
            fields=[
                'money',
                'close',
                'pre_close'
            ],
            count=1,
            panel=False
        )

        if not df.empty:

            all_df.append(df)

    if all_df:

        return pd.concat(
            all_df,
            ignore_index=True
        )

    else:

        return pd.DataFrame()
    



#获取每日TOP50新增
top50_daily = {}

for date in trade_days:

    date_str = date.strftime("%Y-%m-%d")

    df = get_batch_price(stocks, date)

    if df.empty:
        continue

    # 数据处理
    df = df[[
        'code',
        'money',
        'close',
        'pre_close'
    ]].copy()

    df.columns = [
        'stock',
        'amount',
        'close',
        'pre_close'
    ]

    # 成交额转亿
    df['amount'] = (
        df['amount'] / 100000000
    ).round(2)

    # 股票名称
    df['name'] = df['stock'].map(name_map)

    # 当日涨幅
    df['pct'] = (
        (df['close'] - df['pre_close'])
        / df['pre_close']
        * 100
    ).round(2)

    # Top50
    today_top50 = (
        df
        .sort_values(
            by='amount',
            ascending=False
        )
        .head(50)
    )

    # 行业
    industry_list = []

    for stock in today_top50['stock']:

        try:

            industry = get_industry(stock)

            sw1 = industry[stock]['sw_l1']['industry_name']

        except:

            sw1 = None

        industry_list.append(sw1)

    today_top50['industry'] = industry_list

    top50_daily[date_str] = today_top50




#筛选出成交额每日TOP50新增，并得到新增股票T日、T+1日留存率以及涨跌幅的数据
result_list = []

for i in range(1, len(trade_day_str)-2):

    today = trade_day_str[i]

    prev_day = trade_day_str[i-1]

    day2 = trade_day_str[i+1]

    day3 = trade_day_str[i+2]

#     print(today)

    today_df = top50_daily[today]

    prev_df = top50_daily[prev_day]

    # =====================
    # 新增股票
    # =====================

    new_df = today_df[
        ~today_df['stock'].isin(
            prev_df['stock']
        )
    ].copy()

    # 日期
    new_df['date'] = today

    # =====================
    # 第二天是否仍在Top50
    # =====================
    

    day2_set = set(
        top50_daily[day2]['stock']
    )

    new_df['day2_in_top50'] = (
        new_df['stock']
        .isin(day2_set)
    )
    

    # =====================
    # 第三天是否仍在Top50
    # =====================

    day3_set = set(
        top50_daily[day3]['stock']
    )

    new_df['day3_in_top50'] = (
        new_df['stock']
        .isin(day3_set)
    )
    
    # ===================== 
    # 第二天涨幅 
    # ===================== 
    day2_pct_map = ( 
        top50_daily[day2] 
        .set_index('stock')['pct'] 
        .to_dict() 
    )
    new_df['day2_pct'] = ( 
        new_df['stock']
        .map(day2_pct_map) 
    )
    
    # =====================
    # 第三天涨幅 
    # ===================== 
    day3_pct_map = ( 
        top50_daily[day3] 
        .set_index('stock')['pct'] 
        .to_dict() 
    ) 
    new_df['day3_pct'] = ( 
        new_df['stock'] 
        .map(day3_pct_map) 
    )

    result_list.append(new_df)
    
print("分析完成")



# 按留存率以及涨跌幅筛选：选出T+1日、T+2日仍在成交额TOP50的，
# 然后分为两种情况：T日涨跌幅为正、T+1日涨跌幅为正；T日涨跌幅为负、T+1日涨跌幅为正 -----> 条件可以合并为T+1日涨跌幅为正

final_df = pd.concat(
    result_list,
    ignore_index=True
)

# 只保留第二天和第三天都在Top50的股票

final_df = final_df[
    (final_df['day2_in_top50'] == True)
    &
    (final_df['day3_in_top50'] == True)
    &
    (final_df['day2_pct'] > 0)
]

final_df = final_df[
    [
        'date',
        'stock',
        'name',
        'industry',
        'amount',        
        'close',
        'pre_close',
        'pct',
        'day2_pct',
        'day3_pct'
    ]
].copy()

# 修改列名
final_df.columns = [
    '日期',
    '股票代码',
    '名称',
    '行业',
    '成交金额（亿）',
    'T日收盘价',
    'T-1日收盘价',
    'T日涨跌幅',
    'T+1日涨跌幅',
    'T+2日涨跌幅'
]

final_df = final_df.reset_index(drop=True)

# 显示
display(final_df)
