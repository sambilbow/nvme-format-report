"""Plan phase - create execution plan for NVMe wipe operations."""

import os
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .models import DeviceInfo, EraseOperation
from .state import StateManager


class WipePlanner:
    """Creates execution plans for NVMe wipe operations."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    def create_plan(self) -> Dict[str, Any]:
        """Create a complete execution plan based on collected device data."""
        print("Creating wipe execution plan...")
        
        # Get collected device data
        collect_data = self.state_manager.get_phase_data("collect")
        devices = collect_data.get("devices", [])
        
        if not devices:
            raise ValueError("No devices found. Run collect phase first.")
        
        # Select device (for now, use first device - later add user selection)
        selected_device = self._select_device(devices)
        print(f"Selected device: {selected_device['model']} ({selected_device['path']})")
        
        # Validate device is still available
        if not self._validate_device(selected_device['path']):
            raise ValueError(f"Device {selected_device['path']} is no longer available")
        
        # Check for safety issues
        safety_issues = self._check_safety_issues(selected_device['path'])
        if safety_issues:
            print("⚠️  Safety warnings:")
            for issue in safety_issues:
                print(f"   - {issue}")
        
        # Determine best erase method
        erase_method = self._determine_erase_method(selected_device['erase_support'])
        print(f"Selected erase method: {erase_method}")
        
        # Create execution plan
        execution_plan = {
            "device": selected_device,
            "erase_method": erase_method,
            "command": self._build_command(selected_device, erase_method),
            "safety_issues": safety_issues,
            "estimated_duration": self._estimate_duration(selected_device, erase_method),
            "warnings": self._generate_warnings(erase_method, safety_issues),
            "created_at": datetime.now().isoformat()
        }
        
        return execution_plan
    
    def _select_device(self, devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select device for wiping. For now, return first device."""
        if len(devices) == 1:
            return devices[0]
        
        # TODO: Add interactive device selection
        print(f"Found {len(devices)} devices:")
        for i, device in enumerate(devices):
            print(f"  {i+1}. {device['model']} ({device['path']}) - {device['capacity']}")
        
        print(f"Auto-selecting first device: {devices[0]['model']}")
        return devices[0]
    
    def _validate_device(self, device_path: str) -> bool:
        """Check if device is still available and accessible."""
        try:
            # Check if device file exists
            if not Path(device_path).exists():
                return False
            
            # Try to read device info to ensure it's accessible
            result = subprocess.run(
                ["sudo", "nvme", "id-ctrl", device_path, "--output-format=json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_safety_issues(self, device_path: str) -> List[str]:
        """Check for potential safety issues before wiping."""
        issues = []
        
        # Check if device is mounted
        try:
            result = subprocess.run(
                ["findmnt", "-n", "-o", "SOURCE", device_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                issues.append(f"Device {device_path} is currently mounted")
        except FileNotFoundError:
            # findmnt not available, try alternative
            try:
                result = subprocess.run(
                    ["mount", "|", "grep", device_path],
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and device_path in result.stdout:
                    issues.append(f"Device {device_path} appears to be mounted")
            except:
                pass
        
        # Check if device is in use by other processes
        try:
            result = subprocess.run(
                ["lsof", device_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                issues.append(f"Device {device_path} is in use by other processes")
        except FileNotFoundError:
            # lsof not available, skip this check
            pass
        
        return issues
    
    def _determine_erase_method(self, erase_support: Dict[str, bool]) -> str:
        """Determine the best erase method based on device capabilities."""
        # Priority order: crypto_erase > secure_erase > format
        if erase_support.get("crypto_erase", False):
            return "crypto_erase"
        elif erase_support.get("secure_erase", False):
            return "secure_erase"
        elif erase_support.get("format", False):
            return "format"
        else:
            raise ValueError("No supported erase methods found")
    
    def _build_command(self, device: Dict[str, Any], method: str) -> Dict[str, Any]:
        """Build the nvme command for the selected erase method."""
        device_path = device["path"]
        namespace_id = device.get("namespace_id", 1)
        
        if method == "crypto_erase":
            return {
                "command": "sudo",
                "args": ["nvme", "format", device_path, "--ses=2", "--force"],  # crypto erase
                "description": f"Crypto erase on {device_path}"
            }
        elif method == "secure_erase":
            return {
                "command": "sudo",
                "args": ["nvme", "format", device_path, "--ses=1", "--force"],  # secure erase
                "description": f"Secure erase on {device_path}"
            }
        elif method == "format":
            return {
                "command": "sudo",
                "args": ["nvme", "format", device_path, "--force"],  # basic format
                "description": f"Format on {device_path}"
            }
        else:
            raise ValueError(f"Unknown erase method: {method}")
    
    def _estimate_duration(self, device: Dict[str, Any], method: str) -> str:
        """Estimate wipe duration based on device capacity and method."""
        capacity_str = device.get("capacity", "Unknown")
        
        # Very rough estimates based on capacity
        if "TB" in capacity_str:
            capacity_num = float(capacity_str.split()[0])
            if method == "crypto_erase":
                return f"~{int(capacity_num * 2)} minutes"
            elif method == "secure_erase":
                return f"~{int(capacity_num * 5)} minutes"
            else:  # format
                return f"~{int(capacity_num * 0.5)} minutes"
        else:
            return "Unknown (depends on capacity)"
    
    def _generate_warnings(self, method: str, safety_issues: List[str]) -> List[str]:
        """Generate warnings for the execution plan."""
        warnings = [
            "⚠️  THIS OPERATION WILL PERMANENTLY DESTROY ALL DATA ON THE DEVICE",
            "⚠️  This operation cannot be undone",
            "⚠️  Ensure you have backed up any important data"
        ]
        
        if method == "crypto_erase":
            warnings.append("⚠️  Crypto erase will destroy encryption keys")
        elif method == "secure_erase":
            warnings.append("⚠️  Secure erase will overwrite all data")
        else:
            warnings.append("⚠️  Format will remove all data and partition tables")
        
        warnings.extend(safety_issues)
        
        return warnings


def plan_main_with_state(state_manager: StateManager):
    """Main function for plan phase with provided state manager."""
    print("Starting wipe execution planning...")
    planner = WipePlanner(state_manager)
    _run_plan_phase(planner, state_manager)

def main():
    """Main function for plan phase."""
    print("Starting wipe execution planning...")
    
    state_manager = StateManager()
    planner = WipePlanner(state_manager)
    _run_plan_phase(planner, state_manager)

def _run_plan_phase(planner: WipePlanner, state_manager: StateManager):
    """Run the plan phase logic."""
    
    # Check if collect phase completed
    if state_manager.get_phase_status("collect") != "completed":
        print("❌ Collect phase must be completed first. Run: mise collect")
        return
    
    try:
        # Update phase status
        state_manager.update_phase("plan", "running")
        
        # Create execution plan
        execution_plan = planner.create_plan()
        
        # Save plan to state
        state_manager.update_phase("plan", "completed", {
            "execution_plan": execution_plan
        })
        
        print("\n✅ Execution plan created successfully!")
        print(f"Device: {execution_plan['device']['model']}")
        print(f"Method: {execution_plan['erase_method']}")
        print(f"Command: {' '.join(execution_plan['command']['args'])}")
        print(f"Estimated duration: {execution_plan['estimated_duration']}")
        
        print("\n⚠️  Warnings:")
        for warning in execution_plan['warnings']:
            print(f"   {warning}")
        
    except Exception as e:
        print(f"❌ Error during planning: {e}")
        state_manager.update_phase("plan", "failed", {"error": str(e)})


if __name__ == "__main__":
    main()
