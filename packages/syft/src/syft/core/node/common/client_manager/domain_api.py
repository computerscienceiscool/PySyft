# stdlib
from typing import Any
from typing import List
from typing import Union

# third party
from pandas import DataFrame

# relative
from .....core.common.uid import UID
from .....grid.client.proxy_client import ProxyClient
from .....lib.python import String
from .....logger import error
from ....node.common import AbstractNodeClient
from ..node_service.peer_discovery.peer_discovery_messages import (
    GetPeerInfoMessageWithReply,
)
from ..node_service.peer_discovery.peer_discovery_messages import (
    PeerDiscoveryMessageWithReply,
)
from .request_api import RequestAPI


class DomainRequestAPI(RequestAPI):
    def __init__(self, client: AbstractNodeClient):
        super().__init__(client=client)

    def all(self, pandas: bool = True, online_only=True) -> List[Any]:
        response = self.perform_api_request_generic(
            syft_msg=PeerDiscoveryMessageWithReply, content={}
        )
        result = response.payload.kwargs  # type: ignore

        if result["status"] == "ok":
            _data = result["data"]
            if online_only:
                data = list()
                for domain_metadata in _data:
                    if self.get(domain_metadata["id"]).ping:
                        data.append(domain_metadata)
            else:
                data = _data

            if pandas:
                data = DataFrame(data)

            return data
        return []

    def _repr_html_(self) -> str:
        return self.all(online_only=True)._repr_html_()

    def get(self, key: Union[str, int, UID, String]) -> ProxyClient:  # type: ignore
        # to make sure we target the remote Domain through the proxy we need to
        # construct an 💠 Address which includes the correct UID for the Domain
        # position in the 4 hierarchical locations
        node_uid = key
        try:
            if isinstance(node_uid, int):
                domain_metadata = self.all(pandas=False, online_only=False)[node_uid]
                node_uid = str(domain_metadata["id"])
            elif isinstance(node_uid, String):
                node_uid = node_uid.upcast()
        except Exception as e:
            error(f"Invalid int or String key for list of Domain Clients. {e}")

        if isinstance(node_uid, UID):
            node_uid = node_uid.no_dash

        if not isinstance(node_uid, str):
            msg = (
                f"Unable to get ProxyClient with key with type {type(node_uid)} {node_uid}. "
                "API Request requires key to resolve to a str."
            )
            error(msg)
            raise Exception(msg)
        response = self.perform_api_request_generic(
            syft_msg=GetPeerInfoMessageWithReply, content={"uid": node_uid}
        )

        result = response.payload.kwargs.upcast()  # type: ignore

        # a ProxyClient requires an existing NetworkClient and a Remote Domain Address
        # or a known Domain Node UID, and a Node Name
        proxy_client = ProxyClient.create(
            proxy_node_client=self.client,
            remote_domain=node_uid,
            domain_name=result["data"]["name"],
        )

        return proxy_client

    def __getitem__(self, key: Union[str, int, UID]) -> ProxyClient:
        return self.get(key=key)
