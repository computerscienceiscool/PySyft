# stdlib
from typing import List

# third party
from result import Result

# relative
from ....telemetry import instrument
from .credentials import SyftVerifyKey
from .document_store import BaseUIDStoreStash
from .document_store import DocumentStore
from .document_store import PartitionKey
from .document_store import PartitionSettings
from .node_metadata import NodeMetadata
from .serializable import serializable
from .uid import UID

NamePartitionKey = PartitionKey(key="name", type_=str)
ActionIDsPartitionKey = PartitionKey(key="action_ids", type_=List[UID])


@instrument
@serializable(recursive_serde=True)
class MetadataStash(BaseUIDStoreStash):
    object_type = NodeMetadata
    settings: PartitionSettings = PartitionSettings(
        name=NodeMetadata.__canonical_name__, object_type=NodeMetadata
    )

    def __init__(self, store: DocumentStore) -> None:
        super().__init__(store=store)

    def set(
        self, credentials: SyftVerifyKey, metadata: NodeMetadata
    ) -> Result[NodeMetadata, str]:
        res = self.check_type(metadata, self.object_type)
        # we dont use and_then logic here as it is hard because of the order of the arguments
        if res.is_err():
            return res
        return super().set(credentials=credentials, obj=res.ok())

    def update(
        self, credentials: SyftVerifyKey, metadata: NodeMetadata
    ) -> Result[NodeMetadata, str]:
        res = self.check_type(metadata, self.object_type)
        # we dont use and_then logic here as it is hard because of the order of the arguments
        if res.is_err():
            return res
        return super().update(credentials=credentials, obj=res.ok())
