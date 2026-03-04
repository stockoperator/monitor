from monitor.connector.connector_old import BaseConnector, ExchangeName


class GateioBase(BaseConnector):
    """
    Docs: https://www.gate.com/docs/developers/apiv4/en
    """

    @property
    def name(self) -> ExchangeName:
        return ExchangeName.GATEIO

    @property
    def base_url(self) -> str:
        return "https://api.gateio.ws/api/v4/"
