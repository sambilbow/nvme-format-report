"""Main entry point for NVMe wipe tool."""

import sys
import subprocess
from pathlib import Path

from .state import StateManager
from .collect import main as collect_main
from .plan import main as plan_main
from .execute import main as execute_main
from .report import main as report_main


def run_full_workflow():
    """Run the complete wipe workflow."""
    print("🚀 Starting NVMe Wipe Tool - Full Workflow")
    print("=" * 50)
    
    # Prompt for report directory
    report_dir = input("Enter directory to save reports (default: build): ").strip()
    if not report_dir:
        report_dir = "build"
    
    print(f"Reports will be saved to: {report_dir}")
    
    state_manager = StateManager(report_dir=report_dir)
    
    try:
        # Phase 1: Collect
        print("\n📋 Phase 1: Collecting device information...")
        collect_main()
        
        if state_manager.get_phase_status("collect") != "completed":
            print("❌ Collect phase failed. Stopping workflow.")
            return False
        
        # Phase 2: Plan
        print("\n📋 Phase 2: Creating execution plan...")
        plan_main()
        
        if state_manager.get_phase_status("plan") != "completed":
            print("❌ Plan phase failed. Stopping workflow.")
            return False
        
        # Phase 3: Execute
        print("\n📋 Phase 3: Executing wipe operation...")
        print("⚠️  WARNING: This will permanently destroy all data on the selected device!")
        confirm = input("Type 'YES' to continue: ")
        
        if confirm != "YES":
            print("❌ Operation cancelled by user.")
            return False
        
        execute_main()
        
        if state_manager.get_phase_status("execute") != "completed":
            print("❌ Execute phase failed. Stopping workflow.")
            return False
        
        # Phase 4: Report
        print("\n📋 Phase 4: Generating reports...")
        report_main()
        
        if state_manager.get_phase_status("report") != "completed":
            print("❌ Report phase failed.")
            return False
        
        print("\n✅ Full workflow completed successfully!")
        return True
        
    except KeyboardInterrupt:
        print("\n❌ Workflow interrupted by user.")
        return False
    except Exception as e:
        print(f"\n❌ Workflow failed with error: {e}")
        return False


def show_status():
    """Show current status of all phases."""
    print("📊 NVMe Wipe Tool - Status")
    print("=" * 30)
    
    # Check for existing state file to determine report directory
    state_file = Path("build/state.json")
    if state_file.exists():
        state_manager = StateManager()
    else:
        # No existing state, use default
        state_manager = StateManager()
    
    state = state_manager.get_state()
    
    phases = ["collect", "plan", "execute", "report"]
    
    for phase in phases:
        status = state_manager.get_phase_status(phase)
        status_icon = "✅" if status == "completed" else "⏳" if status == "running" else "❌" if status == "failed" else "⭕"
        print(f"{status_icon} {phase.capitalize()}: {status}")
    
    # Show device info if available
    collect_data = state_manager.get_phase_data("collect")
    if collect_data.get("devices"):
        print(f"\n📱 Devices found: {len(collect_data['devices'])}")
        for device in collect_data["devices"]:
            print(f"   - {device['model']} ({device['path']})")


def show_help():
    """Show help information."""
    print("NVMe Wipe Tool - Help")
    print("=" * 25)
    print()
    print("Available commands:")
    print("  mise dev          - Run full workflow")
    print("  mise collect      - Collect device information")
    print("  mise plan         - Create execution plan")
    print("  mise execute      - Execute wipe operation")
    print("  mise report       - Generate reports")
    print("  mise setup        - Install dependencies and setup environment")
    print()
    print("Workflow phases:")
    print("  1. Collect  - Gather NVMe device information")
    print("  2. Plan     - Create execution plan based on device capabilities")
    print("  3. Execute  - Perform the actual wipe operation")
    print("  4. Report   - Generate PDF and JSON reports")
    print()
    print("Safety features:")
    print("  - Device validation and safety checks")
    print("  - User confirmation before destructive operations")
    print("  - Comprehensive logging and state tracking")
    print("  - Professional report generation")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            show_status()
        elif command == "help":
            show_help()
        elif command == "workflow":
            run_full_workflow()
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' to see available commands.")
    else:
        # Default: show status
        show_status()


if __name__ == "__main__":
    main()
