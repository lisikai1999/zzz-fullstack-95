from pydantic import BaseModel
from datetime import datetime


class MetricDataPoint(BaseModel):
    timestamp: str
    value: float


class MetricResponse(BaseModel):
    metric_key: str
    resource_arn: str
    data_points: list[MetricDataPoint]


class LogEvent(BaseModel):
    timestamp: str
    message: str


class LogResponse(BaseModel):
    log_group: str
    events: list[LogEvent]


class ConsoleUrlResponse(BaseModel):
    url: str
