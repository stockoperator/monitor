base_spot_url = "https://api.binance.com/api/"
base_perp_url = "https://fapi.binance.com/fapi/"

perp_exchange_info_url = "v1/exchangeInfo"
spot_exchange_info_url = "v3/exchangeInfo"

spot_klines_url = "v3/klines"
perp_klines_url = "v1/klines"


ws_perp_base_url = "wss://fstream.binance.com"

ws_perp_public_url = f"{ws_perp_base_url}/public/ws"
ws_perp_market_url = f"{ws_perp_base_url}/market/ws"
ws_perp_private_url = f"{ws_perp_base_url}/private/ws"

ws_spot_url = "wss://stream.binance.com:443/ws"

perp_leverage_brackets_url = "v1/leverageBracket"

perp_listen_key_url = "v1/listenKey"
perp_order_url = "v1/order"
perp_open_orders_url = "v1/openOrders"
perp_position_risk_url = "v2/positionRisk"
perp_balance_url = "v2/balance"

SPOT_IP_WEIGHT_BUDGET = 6000
PERP_IP_WEIGHT_BUDGET = 2400
IP_WEIGHT_HEADER = "X-MBX-USED-WEIGHT-1M"
