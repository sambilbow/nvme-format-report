"""Report phase - generate PDF and JSON reports from wipe results."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from .models import WipeReport, DeviceInfo, EraseOperation, DataAnalysis
from .state import StateManager


class ReportGenerator:
    """Generates PDF and JSON reports from wipe operation results."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.business_info = self._load_business_info()
        self.report_dir = state_manager.get_report_dir()
    
    def _load_business_info(self) -> Dict[str, str]:
        """Load business information from environment variables."""
        from dotenv import load_dotenv
        load_dotenv()
        
        return {
            "business_name": os.getenv("BUSINESS_NAME", "Your Company Name"),
            "business_address": os.getenv("BUSINESS_ADDRESS", "123 Main St, City, State 12345"),
            "business_contact": os.getenv("BUSINESS_CONTACT", "John Doe"),
            "business_phone": os.getenv("BUSINESS_PHONE", "+1-555-123-4567"),
            "business_email": os.getenv("BUSINESS_EMAIL", "contact@yourcompany.com"),
            "business_website": os.getenv("BUSINESS_WEBSITE", "https://yourcompany.com"),
            "technician_name": os.getenv("TECHNICIAN_NAME", "Sam")
        }
    
    def generate_reports(self) -> Dict[str, str]:
        """Generate both PDF and JSON reports."""
        print("Generating wipe reports...")
        
        # Get data from all phases
        collect_data = self.state_manager.get_phase_data("collect")
        plan_data = self.state_manager.get_phase_data("plan")
        execute_data = self.state_manager.get_phase_data("execute")
        
        if not all([collect_data, plan_data, execute_data]):
            raise ValueError("Missing required phase data. Ensure all phases completed successfully.")
        
        # Create timestamp for file naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate JSON report
        json_path = self._generate_json_report(collect_data, plan_data, execute_data, timestamp)
        
        # Generate PDF report
        pdf_path = self._generate_pdf_report(collect_data, plan_data, execute_data, timestamp)
        
        return {
            "json_report": json_path,
            "pdf_report": pdf_path,
            "timestamp": timestamp
        }
    
    def _generate_json_report(self, collect_data: Dict, plan_data: Dict, execute_data: Dict, timestamp: str) -> str:
        """Generate JSON report."""
        # Build complete report data
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "generated_by": self.business_info["technician_name"],
                "business_info": self.business_info
            },
            "device_info": collect_data["devices"][0],  # First device
            "system_info": collect_data.get("system_info", {}),
            "execution_plan": plan_data["execution_plan"],
            "execution_results": execute_data,
            "wipe_summary": {
                "method": execute_data["erase_operation"]["method"],
                "status": execute_data["erase_operation"]["status"],
                "duration_seconds": execute_data["erase_operation"]["duration"],
                "duration_ms": execute_data["erase_operation"].get("duration_ms"),
                "start_time": execute_data["erase_operation"]["start_time"],
                "end_time": execute_data["erase_operation"]["end_time"]
            }
        }
        
        # Save JSON report
        json_filename = f"wipe_report_{timestamp}.json"
        json_path = self.report_dir / json_filename
        json_path.parent.mkdir(exist_ok=True)
        
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"✅ JSON report saved: {json_path}")
        return str(json_path)
    
    def _generate_pdf_report(self, collect_data: Dict, plan_data: Dict, execute_data: Dict, timestamp: str) -> str:
        """Generate PDF report."""
        pdf_filename = f"wipe_report_{timestamp}.pdf"
        pdf_path = self.report_dir / pdf_filename
        pdf_path.parent.mkdir(exist_ok=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("NVMe Device Wipe Report", title_style))
        
        # Add device summary information
        device = collect_data["devices"][0]
        execution_results = execute_data["erase_operation"]
        verification_results = execute_data.get("verification", {})
        
        # Serial Number
        serial_style = ParagraphStyle(
            'SerialNumber',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            alignment=1  # Center
        )
        story.append(Paragraph(f"Serial Number: {device['serial']}", serial_style))
        
        # Description
        desc_style = ParagraphStyle(
            'Description',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            alignment=1  # Center
        )
        story.append(Paragraph(f"Description: {device.get('description', 'N/A')}", desc_style))
        
        # Wipe Success
        wipe_status = "YES" if execution_results["status"] == "completed" else "NO"
        wipe_color = colors.green if execution_results["status"] == "completed" else colors.red
        wipe_style = ParagraphStyle(
            'WipeStatus',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6,
            alignment=1,  # Center
            textColor=wipe_color
        )
        story.append(Paragraph(f"Wipe Success: {wipe_status}", wipe_style))
        
        # Verification Success
        verif_status = "YES" if verification_results.get("success", False) and verification_results.get("wipe_effective", False) else "NO"
        verif_color = colors.green if verif_status == "YES" else colors.red
        verif_style = ParagraphStyle(
            'VerificationStatus',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=1,  # Center
            textColor=verif_color
        )
        story.append(Paragraph(f"Verification Success: {verif_status}", verif_style))
        story.append(Spacer(1, 20))
        # Business Information
        story.append(Paragraph("Business Information", styles['Heading2']))
        business_table_data = [
            ["Company:", self.business_info["business_name"]],
            ["Address:", self.business_info["business_address"]],
            ["Contact:", self.business_info["business_contact"]],
            ["Phone:", self.business_info["business_phone"]],
            ["Email:", self.business_info["business_email"]],
            ["Website:", self.business_info["business_website"]],
            ["Technician:", self.business_info["technician_name"]]
        ]
        
        business_table = Table(business_table_data, colWidths=[1.5*inch, 4*inch])
        business_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(business_table)
        story.append(Spacer(1, 20))
        
        # System Information
        story.append(Paragraph("System Information", styles['Heading2']))
        system_info = collect_data.get("system_info", {})
        system_table_data = [
            ["System UUID:", system_info.get("system_uuid", "Unknown")],
            ["OS Information:", system_info.get("os_info", "Unknown")],
            ["Kernel Version:", system_info.get("kernel_version", "Unknown")]
        ]
        
        system_table = Table(system_table_data, colWidths=[1.5*inch, 4*inch])
        system_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(system_table)
        story.append(Spacer(1, 20))
        
        # Device Information
        story.append(Paragraph("Device Information", styles['Heading2']))
        device = collect_data["devices"][0]
        device_table_data = [
            ["Model:", device["model"]],
            ["Serial Number:", device["serial"]],
            ["Firmware:", device["firmware"]],
            ["Capacity:", device["capacity"]],
            ["Device Path:", device["path"]],
            ["Namespace ID:", str(device.get("namespace_id", "N/A"))],
            ["Description:", device.get("description", "N/A")]
        ]
        
        device_table = Table(device_table_data, colWidths=[1.5*inch, 4*inch])
        device_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(device_table)
        story.append(Spacer(1, 20))
        
        # Wipe Operation Details
        story.append(Paragraph("Wipe Operation Details", styles['Heading2']))
        operation = execute_data["erase_operation"]
        duration_display = f"{operation['duration']:.3f} seconds"
        if operation.get("duration_ms"):
            duration_display += f" ({operation['duration_ms']} ms)"
        
        wipe_table_data = [
            ["Method:", operation["method"]],
            ["Status:", operation["status"]],
            ["Start Time:", operation["start_time"]],
            ["End Time:", operation["end_time"]],
            ["Duration:", duration_display],
            ["Success:", "Yes" if operation["status"] == "completed" else "No"]
        ]
        
        if operation.get("error_message"):
            wipe_table_data.append(["Error:", operation["error_message"]])
        
        wipe_table = Table(wipe_table_data, colWidths=[1.5*inch, 4*inch])
        wipe_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(wipe_table)
        story.append(Spacer(1, 20))
        
        # Verification Results
        if "verification" in execute_data:
            story.append(Paragraph("Verification Results", styles['Heading2']))
            verif = execute_data["verification"]
            verif_table_data = [
                ["Verification Method:", verif.get("verification_method", "Unknown")],
                ["Sample Size:", f"{verif.get('total_bytes', 0):,} bytes"],
                ["Zero Percentage:", f"{verif.get('zero_percentage', 0)}%"],
                ["Expected Result:", verif.get("expected_result", "Unknown")],
                ["Wipe Effective:", "Yes" if verif.get("wipe_effective") else "No"],
                ["Verification Success:", "Yes" if verif.get("success") else "No"]
            ]
            
            if not verif.get("success"):
                verif_table_data.append(["Verification Error:", verif.get("error", "Unknown")])
            
            verif_table = Table(verif_table_data, colWidths=[1.5*inch, 4*inch])
            verif_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(verif_table)
            story.append(Spacer(1, 20))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            alignment=1  # Center
        )
        story.append(Paragraph(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
        
        # Build PDF
        doc.build(story)
        print(f"✅ PDF report saved: {pdf_path}")
        return str(pdf_path)


def report_main_with_state(state_manager: StateManager):
    """Main function for report phase with provided state manager."""
    print("Starting report generation...")
    generator = ReportGenerator(state_manager)
    _run_report_phase(generator, state_manager)

def main():
    """Main function for report phase."""
    print("Starting report generation...")
    
    state_manager = StateManager()
    generator = ReportGenerator(state_manager)
    _run_report_phase(generator, state_manager)

def _run_report_phase(generator: ReportGenerator, state_manager: StateManager):
    """Run the report phase logic."""
    
    # Check if execute phase completed
    if state_manager.get_phase_status("execute") != "completed":
        print("❌ Execute phase must be completed first. Run: mise execute")
        return
    
    try:
        # Update phase status
        state_manager.update_phase("report", "running")
        
        # Generate reports
        report_paths = generator.generate_reports()
        
        # Save report info to state
        state_manager.update_phase("report", "completed", {
            "reports": report_paths,
            "generated_at": datetime.now().isoformat()
        })
        
        print("\n✅ Reports generated successfully!")
        print(f"📄 PDF Report: {report_paths['pdf_report']}")
        print(f"📄 JSON Report: {report_paths['json_report']}")
        print(f"🕒 Generated: {report_paths['timestamp']}")
        
    except Exception as e:
        print(f"❌ Error during report generation: {e}")
        state_manager.update_phase("report", "failed", {"error": str(e)})


if __name__ == "__main__":
    main()
