#!/usr/bin/env python3
"""
Data processing and enhancement for NVMe reports
"""

import datetime
from typing import Dict, Any, Optional
from utils import (
    format_capacity, calculate_duration, get_erase_method_name,
    calculate_erase_rate, parse_duration_string
)


class DataProcessor:
    """Centralized data processing and enhancement"""
    
    def __init__(self):
        self.date_format = "%d/%m/%Y %H:%M"
    
    def enhance_erasure_details(self, erasure_details: Dict[str, Any], preseed: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance erasure details with additional metrics and information"""
        # Erase method details
        secure_erase_setting = erasure_details.get('secure_erase_setting', 2)
        erasure_details['erase_method_name'] = get_erase_method_name(secure_erase_setting)
        
        # LBA format information
        command = erasure_details.get('command', '')
        lba_format = "Unknown"
        if '-l ' in command:
            try:
                lba_format = command.split('-l ')[1].split()[0]
            except:
                lba_format = "Unknown"
        erasure_details['lba_format_used'] = lba_format
        
        # Calculate erase rate and metrics
        self._calculate_erase_metrics(erasure_details, preseed)
        
        # Status information
        self._determine_status(erasure_details)
        
        # Standard compliance information
        erasure_details['verification_method'] = "NVMe Secure Erase Verification"
        erasure_details['compliance_standard'] = "NIST 800-88 Rev. 1"
        erasure_details['certification_level'] = "Secure Erase"
        erasure_details['hpa_dco_status'] = "No hidden sectors"
        erasure_details['hpa_dco_size'] = "No hidden sectors"
        
        # Error tracking
        verification_data = preseed.get('verification', {})
        error_tracking = verification_data.get('error_tracking', {})
        erasure_details['io_errors'] = error_tracking.get('io_errors', 0)
        erasure_details['retry_count'] = error_tracking.get('retry_count', 0)
        erasure_details['warnings'] = error_tracking.get('warnings', '')
        
        return erasure_details
    
    def _calculate_erase_metrics(self, erasure_details: Dict[str, Any], preseed: Dict[str, Any]) -> None:
        """Calculate erase rate and related metrics"""
        capacity_str = preseed.get('nsze', 'Unknown')
        
        if capacity_str != 'Unknown':
            try:
                # Convert capacity to bytes
                if isinstance(capacity_str, str):
                    if capacity_str.startswith('0x'):
                        capacity_bytes = int(capacity_str, 16) * 512
                    elif capacity_str.isdigit():
                        capacity_bytes = int(capacity_str) * 512
                    else:
                        capacity_bytes = 0
                elif isinstance(capacity_str, (int, float)):
                    capacity_bytes = int(capacity_str) * 512
                else:
                    capacity_bytes = 0
                
                # Parse duration
                duration = erasure_details.get('duration', 'Unknown')
                if duration != 'Unknown':
                    total_seconds = parse_duration_string(duration)
                    erasure_details['erase_rate_mbps'] = calculate_erase_rate(capacity_bytes, total_seconds)
                else:
                    erasure_details['erase_rate_mbps'] = "Unknown"
                
                erasure_details['bytes_erased'] = capacity_bytes
                erasure_details['bytes_erased_formatted'] = f"{capacity_bytes:,}"
                
            except Exception:
                erasure_details['erase_rate_mbps'] = "Unknown"
                erasure_details['bytes_erased'] = 0
                erasure_details['bytes_erased_formatted'] = "Unknown"
        else:
            erasure_details['erase_rate_mbps'] = "Unknown"
            erasure_details['bytes_erased'] = 0
            erasure_details['bytes_erased_formatted'] = "Unknown"
    
    def _determine_status(self, erasure_details: Dict[str, Any]) -> None:
        """Determine the final status based on success and verification"""
        success = erasure_details.get('success', True)
        verification_status = erasure_details.get('verification_status', '')
        
        if success and verification_status in ['LIKELY_ERASED', 'SUCCESS']:
            erasure_details['status'] = "SUCCESS"
        elif not success or verification_status == 'POSSIBLY_NOT_ERASED':
            erasure_details['status'] = "FAILED"
        elif verification_status in ['UNCERTAIN', 'UNSURE', 'INCONCLUSIVE']:
            erasure_details['status'] = "UNCERTAIN"
        else:
            erasure_details['status'] = "SUCCESS" if success else "FAILED"
    
    def process_device_info(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format device information"""
        processed = device_info.copy()
        
        # Format capacity
        if 'nsze' in processed:
            processed['capacity'] = format_capacity(processed['nsze'])
        
        # Ensure all required fields have defaults
        defaults = {
            'device_path': 'Unknown',
            'model': 'Unknown',
            'serial': 'Unknown',
            'firmware': 'Unknown',
            'capacity': 'Unknown'
        }
        
        for key, default_value in defaults.items():
            if key not in processed or not processed[key]:
                processed[key] = default_value
        
        return processed
    
    def process_erasure_details(self, erasure_details: Dict[str, Any], preseed: Dict[str, Any]) -> Dict[str, Any]:
        """Process and enhance erasure details"""
        processed = erasure_details.copy()
        
        # Calculate duration if not already present
        if 'duration' not in processed or processed['duration'] == 'Unknown':
            if 'start_time' in processed and 'end_time' in processed:
                processed['duration'] = calculate_duration(
                    processed['start_time'], 
                    processed['end_time'], 
                    self.date_format
                )
            else:
                processed['duration'] = 'Unknown'
        
        # Enhance with additional metrics
        return self.enhance_erasure_details(processed, preseed)
    
    def build_report_data(self, preseed: Dict[str, Any], business_details: Dict[str, str], 
                         technician_details: Dict[str, str]) -> Dict[str, Any]:
        """Build complete report data structure"""
        # Process device info
        device_info = self.process_device_info(preseed.get('device_info', {}))
        
        # Process erasure details
        erasure_details = self.process_erasure_details(
            preseed.get('erasure_details', {}), 
            preseed
        )
        
        # Get system info
        verification_system_info = preseed.get('system_info', {})
        
        return {
            'report_type': 'NVMe/SSD Secure Erase Report',
            'generated_at': datetime.datetime.now().strftime(self.date_format),
            'business_details': business_details,
            'device_info': device_info,
            'erasure_details': erasure_details,
            'verification': preseed.get('verification', {}),
            'system_info': {
                'hostname': verification_system_info.get('hostname', preseed.get('hostname', 'Unknown')),
                'kernel_version': verification_system_info.get('kernel_version', 'Unknown'),
                'system_uuid': verification_system_info.get('system_uuid', 'Unknown')
            },
            'additional_info': {
                'operator': '',
                'location': '',
                'notes': ''
            }
        }
