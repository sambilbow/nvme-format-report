"""Data models for NVMe device information and wipe operations."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DeviceInfo(BaseModel):
    """NVMe device information."""
    model: str
    serial: str
    firmware: str
    capacity: str
    path: str
    namespace_id: Optional[int] = None


class EraseOperation(BaseModel):
    """Erase operation details."""
    method: str  # secure_erase, crypto_erase, format, etc.
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None  # in seconds (with millisecond precision)
    duration_ms: Optional[int] = None  # duration in milliseconds
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None


class DataAnalysis(BaseModel):
    """Data analysis results."""
    total_lines: int
    non_zero_lines: int
    hexdump_sample: str
    hexdump_non_zero_lines: int
    hexdump_sample_non_zero: str


class WipeReport(BaseModel):
    """Complete wipe report."""
    device: DeviceInfo
    erase_operation: EraseOperation
    data_analysis: Optional[DataAnalysis] = None
    business_info: Dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.now)
