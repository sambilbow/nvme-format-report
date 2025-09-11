#!/usr/bin/env python3
"""
NVMe/SSD Erasure Report Builder - Refactored and optimized
"""

import os
import sys
import json
import datetime
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Import our new modules
from utils import format_capacity, calculate_duration, extract_device_info_from_text
from templates import ReportTemplates
from data_processor import DataProcessor

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def get_report_formats():
    """Get report formats from user using gum choose"""
    try:
        # Check if gum is available
        subprocess.run(['gum', '--version'], capture_output=True, check=True)
        
        # Use gum to select formats
        result = subprocess.run([
            'gum', 'choose', 
            '--header', 'Select report formats to generate:',
            '--no-limit',
            'Text (TXT)', 'HTML', 'JSON', 'PDF'
        ], capture_output=True, text=True, check=True)
        
        # Parse the output
        selected = result.stdout.strip().split('\n')
        format_map = {
            'Text (TXT)': 'text',
            'HTML': 'html', 
            'JSON': 'json',
            'PDF': 'pdf'
        }
        
        return [format_map[choice] for choice in selected if choice in format_map]
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback if gum is not available
        print("gum not available, generating all formats...")
        return ['text', 'html', 'json', 'pdf']


class NVMeReportBuilder:
    """Refactored NVMe report builder with reduced LOC"""
    
    def __init__(self):
        self.date_format = "%d/%m/%Y %H:%M"
        self.report_data = {}
        self.preseed = {}
        self.data_processor = DataProcessor()
        self.templates = ReportTemplates()
        
        # Load environment variables
        load_dotenv()
        
        # Load business and customer details from .env
        self.business_details = {
            'name': os.getenv('BUSINESS_NAME', 'Not Applicable (BN)'),
            'address': os.getenv('BUSINESS_ADDRESS', 'Not Applicable (BA)'),
            'contact_name': os.getenv('BUSINESS_CONTACT_NAME', 'Not Applicable (BCN)'),
            'contact_phone': os.getenv('BUSINESS_CONTACT_PHONE', 'Not Applicable (BCP)'),
            'email': os.getenv('BUSINESS_EMAIL', ''),
            'website': os.getenv('BUSINESS_WEBSITE', '')
        }
        
        self.technician_details = {
            'name': os.getenv('TECHNICIAN_NAME', 'Not Provided')
        }

    def load_preseed_from_plan(self, plan_file: str) -> dict:
        """Load data from unified execution plan file"""
        try:
            with open(plan_file, 'r') as f:
                plan_data = json.load(f)
            
            # Convert plan data to preseed format for compatibility
            preseed = {
                'device_info': plan_data.get('device_info', {}),
                'system_info': plan_data.get('system_info', {}),
                'business_details': plan_data.get('business_details', {}),
                'technician_details': plan_data.get('technician_details', {}),
                'hostname': plan_data.get('system_info', {}).get('hostname', 'Unknown'),
                'verification': plan_data.get('verification', {}),
                'erasure_details': {
                    'command': plan_data.get('execution_plan', {}).get('recommended_command', ''),
                    'secure_erase_setting': plan_data.get('execution_plan', {}).get('secure_erase_setting', 2),
                    'start_time': plan_data.get('execution_plan', {}).get('start_time', ''),
                    'end_time': plan_data.get('execution_plan', {}).get('end_time', ''),
                    'duration': plan_data.get('execution_plan', {}).get('duration', ''),
                    'success': plan_data.get('execution_plan', {}).get('success', False),
                    'io_errors': plan_data.get('execution_plan', {}).get('io_errors', 0),
                    'warnings': plan_data.get('execution_plan', {}).get('warnings', ''),
                    'verification_status': plan_data.get('verification', {}).get('data_analysis', {}).get('status', 'UNKNOWN')
                },
                'nsze': plan_data.get('device_info', {}).get('nsze', 'Unknown')
            }
            
            return preseed
        except Exception as e:
            print(f"Error loading plan file: {e}")
            return {}

    def build_report_data_from_preseed(self):
        """Build report data using the data processor"""
        # Prepare device info for processing
        device_info = {
            'device_path': self.preseed.get('device_path', '/dev/nvme0'),
            'model': self.preseed.get('model', 'Unknown'),
            'serial': self.preseed.get('serial', 'Unknown'),
            'firmware': self.preseed.get('firmware', 'Unknown'),
            'nsze': self.preseed.get('nsze', 'Unknown')
        }
        
        # Prepare preseed for data processor
        self.preseed['device_info'] = device_info
        
        # Use data processor to build complete report data
        self.report_data = self.data_processor.build_report_data(
            self.preseed, 
            self.business_details, 
            self.technician_details
        )

    def generate_text_report(self, output_dir="build"):
        """Generate text report using templates"""
        os.makedirs(output_dir, exist_ok=True)
        
        data = self.report_data
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        device_name = data['device_info']['device_path'].replace('/', '_')
        report_file = os.path.join(output_dir, f"nvme_erase_report_{device_name}_{timestamp}.txt")
        
        # Build report sections using templates
        header = "=" * 80 + "\nNVMe/SSD SECURE ERASE REPORT\n" + "=" * 80
        status = data['erasure_details'].get('status', 'UNKNOWN')
        status_line = f"Status: {status}\nReport Generated: {data['generated_at']}\n"
        
        business_details = self.templates.format_business_details(data['business_details'])
        device_info = self.templates.format_device_info(data['device_info'])
        erasure_details = self.templates.format_erasure_details(data['erasure_details'])
        
        # Get the actual command that was used
        actual_command = data.get('execution_plan', {}).get('actual_command', 'Unknown')
        command_used = f"COMMAND USED:\n{'-' * 40}\n{actual_command}\n\n"
        
        system_info = self.templates.format_text_section("SYSTEM INFORMATION", {
            'Hostname': data['system_info']['hostname'],
            'System UUID': data['system_info']['system_uuid'],
            'Kernel Version': data['system_info']['kernel_version']
        })
        
        technician_info = self.templates.format_text_section("TECHNICIAN/OPERATOR", {
            'Name': data['erasure_details'].get('technician_name', 'Not Provided')
        })
        
        additional_info = ""
        if any(data['additional_info'].values()):
            additional_info = self.templates.format_text_section("ADDITIONAL INFORMATION", {
                k: v for k, v in data['additional_info'].items() if v
            })
        
        compliance_statement = """COMPLIANCE STATEMENT:
This report certifies that the NVMe/SSD device listed above has been securely
erased using the NVMe Format command with secure erase settings. The erasure
process has been completed according to industry standards for data sanitization.

Erasure Method: NVMe Format with Secure Erase
Compliance Standard: NIST SP 800-88 Guidelines for Media Sanitization
Verification: Device status confirmed post-erase

"""
        
        footer = "=" * 80 + "\nReport generated by nvme-format-report\nFor Device Erasure Policy Compliance\n" + "=" * 80
        
        # Combine all sections
        report_content = self.templates.get_text_report_template().format(
            header=header,
            status_line=status_line,
            report_generated="",
            business_details=business_details,
            device_info=device_info,
            erasure_details=erasure_details,
            command_used=command_used,
            system_info=system_info,
            technician_info=technician_info,
            additional_info=additional_info,
            compliance_statement=compliance_statement,
            footer=footer
        )
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        print(f"✓ Text report generated: {report_file}")
        return report_file

    def generate_html_report(self, output_dir="build"):
        """Generate HTML report using templates"""
        os.makedirs(output_dir, exist_ok=True)
        
        data = self.report_data
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        device_name = data['device_info']['device_path'].replace('/', '_')
        html_file = os.path.join(output_dir, f"nvme_erase_report_{device_name}_{timestamp}.html")
        
        # Build HTML sections
        status = data['erasure_details'].get('status', 'UNKNOWN')
        status_class = self.templates.get_status_class(status)
        
        header = f"""
    <div class="header">
        <h1>NVMe/SSD Secure Erase Report</h1>
        <p><strong>Status:</strong> <span class="{status_class}">{status}</span></p>
        <p><strong>Report Generated:</strong> {data['generated_at']}</p>
        <p><strong>Device Path:</strong> {data['device_info']['device_path']}</p>
    </div>"""
        
        erasure_section = self.templates.format_html_table("Erasure Details", {
            'Status': status,
            'Start Time': data['erasure_details']['start_time'],
            'End Time': data['erasure_details']['end_time'],
            'Duration': data['erasure_details'].get('duration', 'Unknown'),
            'Method': data['erasure_details'].get('erase_method_name', 'Unknown'),
            'Namespace ID': str(data['erasure_details']['namespace_id'])
        }, 'Status')
        
        device_section = self.templates.format_html_table("Device Information", {
            'Device Path': data['device_info']['device_path'],
            'Model': data['device_info']['model'],
            'Serial Number': data['device_info']['serial'],
            'Firmware Version': data['device_info']['firmware'],
            'Capacity': data['device_info']['capacity']
        })
        
        command_section = f"""
    <div class="section">
        <h2 class="section-header">Command Executed</h2>
        <div class="section-content">
            <div class="command">{data['erasure_details']['command']}</div>
        </div>
    </div>"""
        
        system_section = self.templates.format_html_table("System Information", {
            'Hostname': data['system_info']['hostname'],
            'System UUID': data['system_info']['system_uuid'],
            'Kernel Version': data['system_info']['kernel_version']
        })
        
        additional_section = ""
        if any(data['additional_info'].values()):
            additional_section = self.templates.format_html_table("Additional Information", {
                k: v for k, v in data['additional_info'].items() if v
            })
        
        compliance_section = f"""
    <div class="compliance">
        <h3>Compliance Statement</h3>
        <p>This report certifies that the NVMe/SSD device listed above has been securely 
        erased using the NVMe Format command with secure erase settings. The erasure 
        process has been completed according to industry standards for data sanitization.</p>
        
        <p><strong>Erasure Method:</strong> NVMe Format with Secure Erase<br/>
        <strong>Compliance Standard:</strong> NIST SP 800-88 Guidelines for Media Sanitization<br/>
        <strong>Verification:</strong> Device status confirmed post-erase<br/>
        <strong>Report Generated:</strong> {data['generated_at']}</p>
    </div>"""
        
        footer = """
    <div class="footer">
        <p>Report generated by nvme-format-report</p>
        <p>For Device Erasure Policy Compliance</p>
    </div>"""
        
        # Combine all sections
        html_content = self.templates.get_html_report_template().format(
            css_styles=self.templates.get_css_styles(),
            header=header,
            erasure_section=erasure_section,
            device_section=device_section,
            command_section=command_section,
            system_section=system_section,
            additional_section=additional_section,
            compliance_section=compliance_section,
            footer=footer
        )
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        print(f"✓ HTML report generated: {html_file}")
        return html_file

    def create_pdf_report(self, text_report):
        """Create PDF using reportlab (simplified)"""
        if not HAS_REPORTLAB:
            print("! reportlab not available - install with: pip install reportlab")
            return None
        
        pdf_file = text_report.replace('.txt', '.pdf')
        
        try:
            doc = SimpleDocTemplate(pdf_file, pagesize=A4, 
                                  rightMargin=72, leftMargin=72, 
                                  topMargin=72, bottomMargin=18)
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=1,
                textColor=colors.darkblue
            )
            elements.append(Paragraph("NVMe/SSD Secure Erase Report", title_style))
            elements.append(Spacer(1, 12))
            
            # Report info
            data = self.report_data
            status = data['erasure_details'].get('status', 'UNKNOWN')
            elements.append(Paragraph(f"<b>Status:</b> {status}", styles['Normal']))
            elements.append(Paragraph(f"<b>Report Generated:</b> {data['generated_at']}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # Device Information
            elements.append(Paragraph("Device Information", styles['Heading2']))
            device_data = [
                ['Device Path', data['device_info']['device_path']],
                ['Model', data['device_info']['model']],
                ['Serial Number', data['device_info']['serial']],
                ['Firmware Version', data['device_info']['firmware']],
                ['Capacity', data['device_info']['capacity']]
            ]
            device_table = Table(device_data, colWidths=[2*inch, 4*inch])
            device_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(device_table)
            elements.append(Spacer(1, 20))
            
            # Erasure Details
            elements.append(Paragraph("Erasure Details", styles['Heading2']))
            erasure_data = [
                ['Start Time', data['erasure_details']['start_time']],
                ['End Time', data['erasure_details']['end_time']],
                ['Duration', data['erasure_details'].get('duration', 'Unknown')],
                ['Status', status],
                ['Method', data['erasure_details'].get('erase_method_name', 'Unknown')],
                ['Command', data['erasure_details']['command']]
            ]
            erasure_table = Table(erasure_data, colWidths=[2*inch, 4*inch])
            erasure_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(erasure_table)
            
            # Build PDF
            doc.build(elements)
            
            if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
                print(f"✓ PDF report created: {pdf_file}")
                return pdf_file
            else:
                print("✗ PDF creation failed")
                return None
                
        except Exception as e:
            print(f"✗ PDF creation failed: {e}")
            return None

    def save_reports(self, output_dir="build", formats=None):
        """Save reports in selected formats"""
        if formats is None:
            formats = ['text', 'html', 'json', 'pdf']
        
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        
        # Generate selected reports
        if 'text' in formats:
            text_report = self.generate_text_report(output_dir)
            results['text_file'] = text_report
        
        if 'html' in formats:
            html_report = self.generate_html_report(output_dir)
            results['html_file'] = html_report
        
        if 'json' in formats:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            device_name = self.report_data['device_info']['device_path'].replace('/', '_')
            json_file = os.path.join(output_dir, f"nvme_erase_report_{device_name}_{timestamp}.json")
            
            with open(json_file, 'w') as f:
                json.dump(self.report_data, f, indent=2)
            print(f"✓ JSON report saved: {json_file}")
            results['json_file'] = json_file
        
        if 'pdf' in formats:
            # PDF needs text report for creation
            if 'text' in formats:
                pdf_file = self.create_pdf_report(results.get('text_file'))
            else:
                # Generate text report temporarily for PDF
                temp_text = self.generate_text_report(output_dir)
                pdf_file = self.create_pdf_report(temp_text)
            results['pdf_file'] = pdf_file
        
        return results


def main():
    parser = argparse.ArgumentParser(description="NVMe/SSD Erasure Report Builder - Simplified Architecture")
    parser.add_argument("--from-plan", dest="from_plan", help="Execution plan file from collect-and-plan")
    parser.add_argument("--formats", nargs="+", choices=['text', 'html', 'json', 'pdf'], 
                       help="Report formats to generate (default: interactive selection)")
    args = parser.parse_args()
    
    if not args.from_plan:
        print("No plan file specified.")
        print("Usage: python3 src/nvme_report_builder_system.py --from-plan <plan_file>")
        return

    print("NVMe/SSD Erasure Report Builder")
    print("Simplified two-phase architecture")
    print()
    
    # Create report builder
    builder = NVMeReportBuilder()
    
    # Load data from plan file
    builder.load_preseed_from_plan(args.from_plan)
    print(f"Loaded execution plan from: {args.from_plan}")
    
    # Build report data
    builder.build_report_data_from_preseed()
    
    # Get format selection from user or command line
    if args.formats:
        formats = args.formats
        print(f"\nUsing specified formats: {', '.join(formats)}")
    else:
        print("\nSelecting report formats...")
        formats = get_report_formats()
        print(f"Selected formats: {', '.join(formats)}")
    
    # Generate reports
    print("\nGenerating reports...")
    files = builder.save_reports("build", formats)
    
    print("\nReport generation complete!")
    for file_type, file_path in files.items():
        if file_path and os.path.exists(file_path):
            print(f"  {file_type.upper()}: {file_path}")


if __name__ == "__main__":
    main()
