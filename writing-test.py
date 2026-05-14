import pandas as pd
from datetime import timedelta
import jqdata

def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')
    

    run_daily(before_market_open, time='09:00') # 每天 09:00 盘前选股
    run_daily(buy_stocks, time='09:30')         # 每天 09:30 开盘买入
    run_daily(sell_stocks, time='14:55')        # 每天 14:55 尾盘卖出

def before_market_open(context):
    """09:00 盘前大盘判断与选股逻辑"""
    context.target_stocks = [] # 每日重置目标股票池
    yesterday = context.previous_date # 获取上一个真实交易日
    
    # 1. 判断上证指数涨幅
    index_data = get_price('000001.XSHG', end_date=yesterday, count=1, frequency='daily', fields=['open', 'close'])
    if index_data.empty: 
        return
    
    index_open = index_data['open'][0]
    index_close = index_data['close'][0]
    rise_rate = (index_close - index_open) / index_open
    
    if rise_rate <= 0.005:
        return

    # 2. 获取全市场股票并过滤 ST 及停牌股
    all_stocks = list(get_all_securities(['stock'], date=yesterday).index)
    current_data = get_current_data()
    valid_stocks = [code for code in all_stocks 
                    if not current_data[code].is_st and not current_data[code].paused]
                    
    
    # 3. 批量获取昨日数据进行筛选
    df = get_price(valid_stocks, end_date=yesterday, count=1, frequency='daily', 
                   fields=['close', 'pre_close', 'money'], panel=False)
    
    if df.empty:
        return

    # 4. 向量化条件筛选：涨停 且 成交额在 2亿 到 4亿 之间
    condition_limit_up = df['close'] >= df['pre_close'] * 1.098
    condition_volume = (df['money'] >= 200000000) & (df['money'] <= 400000000)
    
    df_filtered = df[condition_limit_up & condition_volume]
    limit_up_stocks = df_filtered['code'].tolist()  

    log.info(f"昨日涨停 + 2-4亿成交额：共 {len(limit_up_stocks)} 只")
    context.target_stocks = limit_up_stocks
    
    # if len(limit_up_stocks) > 0:
    #     q = query(
    #         valuation.code,
    #         valuation.pe_ratio,
    #         valuation.pb_ratio,
    #         indicator.roe
    #     ).filter(
    #         valuation.code.in_(limit_up_stocks)
    #     )

    #      df_funda = get_fundamentals(q)


    #     df_funda = df_funda[
    #         (df_funda['pe_ratio'] > 0)      
    #         & (df_funda['pe_ratio'] < 40)   
    #         & (df_funda['pb_ratio'] < 6)    
    #         & (df_funda['roe'] > 6)          
    #     ]       

    # # 返回股票代码列表
    #     context.target_stocks = df_funda['code'].tolist()
    # else:
    #     context.target_stocks = []
    

    # log.info(f"最终选股（涨停+基本面）：共 {len(context.target_stocks)} 只")
    # log.info(f"股票列表：{context.target_stocks}")

    

def buy_stocks(context):

    if not context.target_stocks:
        return
        
    current_data = get_current_data()
    yesterday = context.previous_date
    
    for code in context.target_stocks:
        today_open = current_data[code].day_open
        yesterday_close = get_price(code, end_date=yesterday, count=1, frequency='daily', fields=['close'])['close'][0]
        
        if yesterday_close == 0: 
            continue
            
        today_rise = (today_open - yesterday_close) / yesterday_close
        
        # 如果开盘涨幅在 0% 到 3% 之间，买入 10000 元
        if 0.00 <= today_rise <= 0.03:
            order_value(code, 10000)


def sell_stocks(context):

    positions = context.portfolio.positions
    if not positions:
        return
        
    current_data = get_current_data()
    
    for stock in list(positions.keys()):
        pos = positions[stock]
        # 只处理可卖出的持仓
        if pos.closeable_amount == 0: 
            continue
            
        current_price = current_data[stock].last_price
        high_limit = current_data[stock].high_limit # 调用聚宽官方精准涨停价
        
        # 如果尾盘没有封死涨停，则全部卖出
        if current_price < high_limit:
            order_target(stock, 0)



