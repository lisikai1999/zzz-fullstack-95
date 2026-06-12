from pydantic import BaseModel


class TopologyNodeResponse(BaseModel):
    id: str
    label: str
    node_type: str
    region: str
    metadata: dict | None = None

    class Config:
        from_attributes = True


class TopologyEdgeResponse(BaseModel):
    source: str
    target: str
    edge_type: str


class TopologyGraphResponse(BaseModel):
    nodes: list[TopologyNodeResponse]
    edges: list[TopologyEdgeResponse]


class NodeHealthResponse(BaseModel):
    node_id: str
    node_type: str
    health_status: str
    details: dict | None = None


class ReverseLookupResponse(BaseModel):
    domain: str
    chain: list[TopologyNodeResponse]
    edges: list[TopologyEdgeResponse]
