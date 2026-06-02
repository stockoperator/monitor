base_spot_url = "https://api.binance.com/api/"
base_perp_url = "https://fapi.binance.com/fapi/"

perp_exchange_info_url = "v1/exchangeInfo"
spot_exchange_info_url = "v3/exchangeInfo"

spot_klines_url = "v3/klines"
perp_klines_url = "v1/klines"

perp_balance_url = "v3/balance"

_ws_perp_base_url = "wss://fstream.binance.com"

ws_perp_public_url = f"{_ws_perp_base_url}/public/ws"
ws_perp_market_url = f"{_ws_perp_base_url}/market/ws"
ws_perp_private_url = f"{_ws_perp_base_url}/private/ws"

ws_spot_url = "wss://stream.binance.com:443/ws"

perp_leverage_brackets_url = "v1/leverageBracket"

perp_listen_key_url = "v1/listenKey"
perp_order_url = "v1/order"
perp_open_orders_url = "v1/openOrders"
perp_position_risk_url = "v2/positionRisk"
perp_balance_url = "v2/balance"
perp_position_mode = "v1/positionSide/dual"

# all-market mark price + funding stream: pushes funding rate (`r`) and next funding time (`T`)
# for every perp instrument in a single subscription. No `@1s` suffix → 3s cadence (funding is slow-moving)
perp_mark_price_all_channel = "!markPrice@arr"

SPOT_IP_WEIGHT_BUDGET = 6000
PERP_IP_WEIGHT_BUDGET = 2400
IP_WEIGHT_HEADER = "X-MBX-USED-WEIGHT-1M"

ORDER_10S_HEADER = "X-MBX-ORDER-COUNT-10S"
PERP_ORDER_1M_HEADER = "X-MBX-ORDER-COUNT-1M"

PERP_ORDER_10S_BUDGET = 300
PERP_ORDER_1M_BUDGET = 1200

SPOT_ORDER_1D_HEADER = "X-MBX-ORDER-COUNT-1D"

SPOT_ORDER_10S_BUDGET = 100
SPOT_ORDER_1D_BUDGET = 200000
