#!/usr/bin/env python3
"""
Utility functions for NVMe report generation
"""

import datetime
import re
from typing import Dict, Any, Optional


def format_capacity(capacity_str: str) -> str:
    """Convert capacity from hex/decimal to human-readable format"""
    if capacity_str == 'Unknown' or not capacity_str:
        return 'Unknown'
    
    try:
        if isinstance(capacity_str, str):
            if capacity_str.startswith('0x'):
                capacity_bytes = int(capacity_str, 16) * 512
            elif capacity_str.isdigit():
                capacity_bytes = int(capacity_str) * 512
            else:
                return capacity_str
        elif isinstance(capacity_str, (int, float)):
            capacity_bytes = int(capacity_str) * 512
        else:
            return str(capacity_str)
        
        # Convert to human-readable format
        if capacity_bytes >= 1024**4:  # TB
            return f"{capacity_bytes / (1024**4):.2f} TB"
        elif capacity_bytes >= 1024**3:  # GB
            return f"{capacity_bytes / (1024**3):.2f} GB"
        elif capacity_bytes >= 1024**2:  # MB
            return f"{capacity_bytes / (1024**2):.2f} MB"
        else:
            return f"{capacity_bytes:,} bytes"
    except:
        return str(capacity_str)


def calculate_duration(start_time: str, end_time: str, date_format: str = "%d/%m/%Y %H:%M") -> str:
    """Calculate duration between two timestamps"""
    try:
        start_dt = datetime.datetime.strptime(start_time, date_format)
        end_dt = datetime.datetime.strptime(end_time, date_format)
        duration = end_dt - start_dt
        total_seconds = duration.total_seconds()
        
        if total_seconds < 0:
            return "Invalid"
        elif total_seconds < 1:
            milliseconds = int(total_seconds * 1000)
            return f"{milliseconds}ms"
        elif total_seconds < 60:
            return f"{total_seconds:.3f}s"
        elif total_seconds < 3600:
            minutes = int(total_seconds // 60)
            seconds = total_seconds % 60
            return f"{minutes}m {seconds:.3f}s"
        else:
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = total_seconds % 60
            return f"{hours}h {minutes}m {seconds:.3f}s"
    except:
        return "Unknown"


def get_erase_method_name(secure_erase_setting: int) -> str:
    """Get human-readable erase method name"""
    erase_method_map = {
        1: "User Data Erase",
        2: "Crypto Erase"
    }
    return erase_method_map.get(secure_erase_setting, "Unknown")


def get_status_color_class(status: str) -> str:
    """Get CSS class for status color coding"""
    status_colors = {
        'SUCCESS': 'status-success',
        'FAILED': 'status-failed', 
        'UNCERTAIN': 'status-uncertain'
    }
    return status_colors.get(status, '')


def sanitize_hexdump(hexdump_sample: str, max_lines: int = 5) -> str:
    """Sanitize hexdump sample for report display"""
    if not hexdump_sample or not hexdump_sample.strip():
        return "No hexdump data available"
    
    lines = hexdump_sample.strip().split('\n')
    
    if len(lines) <= max_lines:
        return '\n'.join(lines)
    else:
        first_lines = lines[:2]
        last_lines = lines[-2:]
        summary = f"... ({len(lines) - 4} lines omitted) ..."
        return '\n'.join(first_lines + [summary] + last_lines)


def extract_device_info_from_text(content: str) -> Dict[str, str]:
    """Extract device information from text content using regex patterns"""
    preseed = {}
    
    def match_key(pattern: str):
        m = re.search(pattern, content, re.IGNORECASE)
        return m.group(1).strip() if m else None

    preseed['model'] = match_key(r"^\s*mn\s*:\s*(.+)$")
    preseed['serial'] = match_key(r"^\s*sn\s*:\s*(.+)$")
    preseed['firmware'] = match_key(r"^\s*fr\s*:\s*(.+)$")
    preseed['nsze'] = match_key(r"^\s*nsze\s*:\s*(\S+)")
    preseed['nuse'] = match_key(r"^\s*nuse\s*:\s*(\S+)")
    preseed['hostname'] = match_key(r"^\s*HOSTNAME\s*:\s*(.+)$") or match_key(r"^\s*hostname\s*[:=]?\s*(.+)$")
    
    # Filter out None values
    return {k: v for k, v in preseed.items() if v is not None}


def calculate_erase_rate(capacity_bytes: int, duration_seconds: float) -> str:
    """Calculate erase rate in MB/s"""
    if duration_seconds > 0:
        erase_rate_mbps = (capacity_bytes / (1024 * 1024)) / duration_seconds
        return f"{erase_rate_mbps:.2f} MB/s"
    else:
        return "Instant (< 1s)"


def parse_duration_string(duration_str: str) -> float:
    """Parse duration string to seconds"""
    if 'h' in duration_str and 'm' in duration_str and 's' in duration_str:
        # Format: "0h 0m 1.234s"
        parts = duration_str.replace('h', '').replace('m', '').replace('s', '').split()
        if len(parts) >= 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    elif 'ms' in duration_str:
        # Format: "123ms"
        return int(duration_str.replace('ms', '')) / 1000.0
    elif 's' in duration_str:
        # Format: "1.234s" or "0.001s"
        return float(duration_str.replace('s', ''))
    
    return 0.001  # Minimum 1ms for calculation
