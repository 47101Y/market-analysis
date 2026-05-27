from jqdata import *
import pandas as pd
from datetime import timedelta

# =========================
# 初始化
# =========================
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    log.info('策略初始化')
    log.set_level('order', 'error')

    context.buy_value = 200000
    # 仅记录「真实持仓」的买入日；不在下单瞬间写入
    context.hold_dict = {}
    context.target_stocks = []

    run_daily(before_market_open, time='09:00')
    run_daily(buy_stocks, time='09:30')
    run_daily(sell_stocks, time='14:55')
    run_daily(sync_hold_dict_after_close, time='after_close')


# =========================
# 收盘后：以真实持仓为准同步 hold_dict
# =========================
def sync_hold_dict_after_close(context):
    """
    买入：只有收盘后仍持有才记买入日（未成交/部分成交以实际持仓为准）。
    卖出：只有仓位清零才删记录（跌停卖不掉则保留，次日继续卖）。
    """
    today = context.current_dt.date()
    positions = context.portfolio.positions

    # 已清仓 → 删除记录（须先 in 判断，避免聚宽对不存在的 key 打 WARNING）
    for stock in list(context.hold_dict.keys()):
        if stock not in positions or positions[stock].total_amount <= 0:
            del context.hold_dict[stock]
            log.info(f'已清仓，移除记录：{stock}')

    # 有仓但未记录 → 记录首次建仓日
    for stock, pos in positions.items():
        if pos.total_amount > 0 and stock not in context.hold_dict:
            context.hold_dict[stock] = today
            log.info(f'记录建仓日：{stock} -> {today}，持仓 {pos.total_amount} 股')


def _has_position(stock, context):
    """查询是否持有该票；未持仓时不得直接 positions[stock] / .get()。"""
    positions = context.portfolio.positions
    return stock in positions and positions[stock].total_amount > 0


def _place_buy(context, stock, current_data):
    """返回是否成功发出买单（不代表已成交，成交由收盘同步确认）。"""
    if context.portfolio.available_cash < context.buy_value:
        return False

    limit_price = current_data[stock].high_limit
    if limit_price is None or limit_price <= 0:
        log.warning(f'无效涨停价，跳过：{stock}')
        return False

    # 已有持仓则不再重复买（可按需注释掉）
    if _has_position(stock, context):
        return False

    order_obj = None

    if stock.startswith('688') or stock.startswith('300'):
        # 科创板/创业板：200 股整数倍 + 保护限价
        if limit_price >= 10000:
            limit_price = 1000.0
            order_obj = order_value(
                stock,
                context.buy_value,
                style=LimitOrderStyle(limit_price),
            )
        elif limit_price > 1000:
            order_obj = order(
                stock,
                200,
                style=LimitOrderStyle(limit_price),
            )
        else:
            order_obj = order_value(
                stock,
                context.buy_value,
                style=LimitOrderStyle(limit_price),
            )
    else:
        order_obj = order_value(
            stock,
            context.buy_value,
            style=LimitOrderStyle(limit_price),
        )

    if order_obj is None:
        log.warning(f'买单未发出：{stock}')
        return False

    log.info(f'发出买单：{stock}，限价 {limit_price}')
    return True


# =========================
# 盘前选股
# =========================
def before_market_open(context):
    context.target_stocks = []
    yesterday = context.previous_date
    trade_days = get_trade_days(end_date=yesterday, count=2)
    if len(trade_days) < 2:
        return
    prev_day = trade_days[0]

    df_yesterday = get_price(
        get_all_securities('stock', date=yesterday).index.tolist(),
        end_date=yesterday,
        count=1,
        frequency='daily',
        fields=['money'],
        panel=False,
    )
    top50_yesterday = df_yesterday.sort_values(by='money', ascending=False).head(50)['code'].tolist()

    df_prev = get_price(
        get_all_securities('stock', date=prev_day).index.tolist(),
        end_date=prev_day,
        count=1,
        frequency='daily',
        fields=['money'],
        panel=False,
    )
    top50_prev = df_prev.sort_values(by='money', ascending=False).head(50)['code'].tolist()

    new_stocks = list(set(top50_yesterday) - set(top50_prev))

    current_data = get_current_data()
    filtered = []
    for stock in new_stocks:
        if current_data[stock].paused or current_data[stock].is_st:
            continue
        # if current_data[stock].day_open >= current_data[stock].high_limit:
        #     continue
        filtered.append(stock)

    context.target_stocks = filtered
    log.info(f'当日新进候选股数量: {len(filtered)}')


# =========================
# 开盘买入（不在此处写 hold_dict）
# =========================
def buy_stocks(context):
    if not context.target_stocks:
        return

    current_data = get_current_data()
    for stock in context.target_stocks:
        if context.portfolio.available_cash < context.buy_value:
            log.warning('剩余可用资金不足，停止买入')
            break
        _place_buy(context, stock, current_data)


# =========================
# 持有满 10 个交易日卖出（不在此处删 hold_dict）
# =========================
def sell_stocks(context):
    today = context.current_dt.date()
    current_data = get_current_data()
    positions = context.portfolio.positions
    if not positions:
        return

    for stock in list(positions.keys()):
        if stock not in context.hold_dict:
            continue

        pos = positions[stock]
        if pos.closeable_amount <= 0:
            continue

        buy_date = context.hold_dict[stock]
        trade_days = get_trade_days(start_date=buy_date, end_date=today)
        hold_days = len(trade_days)

        if hold_days < 10:
            continue

        current_price = current_data[stock].last_price
        low_limit = current_data[stock].low_limit

        # 跌停附近：用跌停价挂单，提高成交概率；仍可能卖不掉，记录保留
        if low_limit and low_limit > 0:
            limit_price = round(low_limit, 2)
        else:
            limit_price = round(current_price * 0.98, 2)

        order_obj = order_target(
            stock,
            0,
            style=LimitOrderStyle(limit_price),
        )

        if order_obj is None:
            log.warning(f'卖单未发出：{stock}，将继续跟踪')
            continue

        log.info(
            f'发出卖单：{stock}，已持有 {hold_days} 个交易日，限价 {limit_price}'
        )
        # 注意：此处 deliberately 不 del hold_dict
        # 若未成交，after_close 同步时仍保留，次日继续尝试卖出
