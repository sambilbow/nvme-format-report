#!/usr/bin/env python3
"""
Template system for report generation
"""

from typing import Dict, Any


class ReportTemplates:
    """Centralized templates for all report formats"""
    
    @staticmethod
    def get_text_report_template() -> str:
        """Get text report template"""
        return """{header}
{status_line}
{report_generated}
{business_details}
{device_info}
{erasure_details}
{command_used}
{system_info}
{technician_info}
{additional_info}
{compliance_statement}
{footer}"""

    @staticmethod
    def get_html_report_template() -> str:
        """Get HTML report template"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NVMe/SSD Secure Erase Report</title>
    <style>
        {css_styles}
    </style>
</head>
<body>
    {header}
    {erasure_section}
    {device_section}
    {command_section}
    {system_section}
    {additional_section}
    {compliance_section}
    {footer}
</body>
</html>"""

    @staticmethod
    def get_css_styles() -> str:
        """Get CSS styles for HTML reports"""
        return """body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #2c3e50;
            margin: 0;
            font-size: 2.2em;
        }
        .section {
            margin-bottom: 30px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .section-header {
            background-color: #34495e;
            color: white;
            padding: 15px 20px;
            margin: 0;
            font-size: 1.3em;
            font-weight: bold;
        }
        .section-content {
            padding: 20px;
            background-color: #f8f9fa;
        }
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        .info-table th {
            background-color: #ecf0f1;
            padding: 12px;
            text-align: left;
            border: 1px solid #bdc3c7;
            font-weight: bold;
            width: 30%;
        }
        .info-table td {
            padding: 12px;
            border: 1px solid #bdc3c7;
            background-color: white;
        }
        .status-success { color: #27ae60; font-weight: bold; }
        .status-failed { color: #e74c3c; font-weight: bold; }
        .status-uncertain { color: #f39c12; font-weight: bold; }
        .command {
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
            margin: 10px 0;
        }
        .compliance {
            background-color: #e8f5e8;
            border-left: 4px solid #27ae60;
            padding: 20px;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #bdc3c7;
            color: #7f8c8d;
        }"""

    @staticmethod
    def format_text_section(title: str, data: Dict[str, str], include_status: bool = False) -> str:
        """Format a section for text reports"""
        lines = [f"{title}:", "-" * 40]
        
        for key, value in data.items():
            if key == 'status' and include_status:
                # Add color coding for status
                status_colors = {
                    'SUCCESS': '\033[92m',  # Green
                    'FAILED': '\033[91m',   # Red
                    'UNCERTAIN': '\033[93m' # Yellow
                }
                color = status_colors.get(value, '')
                reset = '\033[0m' if color else ''
                lines.append(f"{key.title()}: {color}{value}{reset}")
            else:
                lines.append(f"{key.title()}: {value}")
        
        return '\n'.join(lines) + '\n\n'

    @staticmethod
    def format_html_table(title: str, data: Dict[str, str], status_key: str = None) -> str:
        """Format data as HTML table"""
        html = f"""
    <div class="section">
        <h2 class="section-header">{title}</h2>
        <div class="section-content">
            <table class="info-table">"""
        
        for key, value in data.items():
            if key == status_key:
                status_class = ReportTemplates.get_status_class(value)
                html += f"""
                <tr>
                    <th>{key.title()}</th>
                    <td class="{status_class}">{value}</td>
                </tr>"""
            else:
                html += f"""
                <tr>
                    <th>{key.title()}</th>
                    <td>{value}</td>
                </tr>"""
        
        html += """
            </table>
        </div>
    </div>"""
        return html

    @staticmethod
    def get_status_class(status: str) -> str:
        """Get CSS class for status"""
        status_classes = {
            'SUCCESS': 'status-success',
            'FAILED': 'status-failed',
            'UNCERTAIN': 'status-uncertain'
        }
        return status_classes.get(status, '')

    @staticmethod
    def format_business_details(business_details: Dict[str, str]) -> str:
        """Format business details section"""
        data = {
            'Business Name': business_details.get('name', 'Not Applicable'),
            'Business Address': business_details.get('address', 'Not Applicable'),
            'Contact Name': business_details.get('contact_name', 'Not Applicable'),
            'Contact Phone': business_details.get('contact_phone', 'Not Applicable')
        }
        
        if business_details.get('email'):
            data['Email'] = business_details['email']
        if business_details.get('website'):
            data['Website'] = business_details['website']
            
        return ReportTemplates.format_text_section("BUSINESS DETAILS", data)

    @staticmethod
    def format_device_info(device_info: Dict[str, str]) -> str:
        """Format device information section"""
        data = {
            'Device Path': device_info.get('device_path', 'Unknown'),
            'Model': device_info.get('model', 'Unknown'),
            'Serial Number': device_info.get('serial', 'Unknown'),
            'Firmware': device_info.get('firmware', 'Unknown'),
            'Capacity': device_info.get('capacity', 'Unknown')
        }
        return ReportTemplates.format_text_section("DEVICE INFORMATION", data)

    @staticmethod
    def format_erasure_details(erasure_details: Dict[str, Any]) -> str:
        """Format erasure details section"""
        data = {
            'Start Time': erasure_details.get('start_time', 'Unknown'),
            'End Time': erasure_details.get('end_time', 'Unknown'),
            'Duration': erasure_details.get('duration', 'Unknown'),
            'Status': erasure_details.get('status', 'UNKNOWN'),
            'Method': erasure_details.get('erase_method_name', 'Unknown'),
            'LBA Format Used': erasure_details.get('lba_format_used', 'Unknown'),
            'Bytes Erased': erasure_details.get('bytes_erased_formatted', 'Unknown'),
            'Throughput': erasure_details.get('erase_rate_mbps', 'Unknown'),
            'Verification Method': erasure_details.get('verification_method', 'Unknown'),
            'Compliance Standard': erasure_details.get('compliance_standard', 'Unknown'),
            'HPA/DCO': erasure_details.get('hpa_dco_status', 'Unknown')
        }
        
        errors_text = f"{erasure_details.get('io_errors', 0)} (pass/sync/verify)"
        if erasure_details.get('warnings'):
            errors_text += f" | Warnings: {erasure_details['warnings']}"
        data['Errors'] = errors_text
        
        return ReportTemplates.format_text_section("DISK ERASURE DETAILS", data, include_status=True)
