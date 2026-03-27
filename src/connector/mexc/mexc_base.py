from monitor.connector.connector_old import BaseConnector, ExchangeName


class MexcBase(BaseConnector):
    """
    Docs: https://www.mexc.com/api-docs/spot-v3/introduction
    """

    @property
    def name(self) -> ExchangeName:
        return ExchangeName.MEXC

    @property
    def exchange_symbol_field(self) -> str:
        return "symbol"
