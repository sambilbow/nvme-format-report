"""Execute phase - perform the actual NVMe wipe operation."""

import subprocess
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .models import EraseOperation
from .state import StateManager


class WipeExecutor:
    """Executes NVMe wipe operations based on execution plans."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    def execute_wipe(self) -> Dict[str, Any]:
        """Execute the wipe operation based on the plan."""
        print("Starting wipe execution...")
        
        # Get execution plan
        plan_data = self.state_manager.get_phase_data("plan")
        execution_plan = plan_data.get("execution_plan")
        
        if not execution_plan:
            raise ValueError("No execution plan found. Run plan phase first.")
        
        device = execution_plan["device"]
        command_info = execution_plan["command"]
        
        print(f"Executing: {command_info['description']}")
        print(f"Command: {' '.join([command_info['command']] + command_info['args'])}")
        
        # Create erase operation record
        erase_operation = EraseOperation(
            method=execution_plan["erase_method"],
            start_time=datetime.now(),
            status="running"
        )
        
        # Execute the command
        try:
            result = self._run_wipe_command(command_info)
            erase_operation.end_time = datetime.now()
            erase_operation.duration = (erase_operation.end_time - erase_operation.start_time).total_seconds()
            
            if result["success"]:
                erase_operation.status = "completed"
                erase_operation.duration_ms = int(erase_operation.duration * 1000)
                print("✅ Wipe completed successfully!")
                
                # Verify wipe by analyzing device data
                verification = self.verify_wipe(device["path"], execution_plan["erase_method"])
                result["verification"] = verification
                
                if verification["success"] and verification["wipe_effective"]:
                    print(f"✅ Verification passed: {verification['zero_percentage']}% zeros, {verification['expected_result']} expected")
                else:
                    print(f"⚠️  Verification warning: {verification.get('error', 'Wipe may not be fully effective')}")
            else:
                erase_operation.status = "failed"
                erase_operation.error_message = result["error"]
                erase_operation.duration_ms = int(erase_operation.duration * 1000)
                print(f"❌ Wipe failed: {result['error']}")
            
        except Exception as e:
            erase_operation.end_time = datetime.now()
            erase_operation.duration = (erase_operation.end_time - erase_operation.start_time).total_seconds()
            erase_operation.duration_ms = int(erase_operation.duration * 1000)
            erase_operation.status = "failed"
            erase_operation.error_message = str(e)
            print(f"❌ Wipe failed with exception: {e}")
        
        # Return execution results
        return {
            "erase_operation": erase_operation.model_dump(),
            "command_output": result.get("output", ""),
            "command_error": result.get("error", ""),
            "execution_time": erase_operation.duration
        }
    
    def _run_wipe_command(self, command_info: Dict[str, Any]) -> Dict[str, Any]:
        """Run the actual wipe command."""
        command = command_info["command"]
        args = command_info["args"]
        
        print(f"Running: {command} {' '.join(args)}")
        print("This may take several minutes...")
        
        try:
            # Run the command with timeout
            result = subprocess.run(
                [command] + args,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "error": result.stderr
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr or f"Command failed with return code {result.returncode}"
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out after 1 hour"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": f"Command not found: {command}"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": f"Unexpected error: {str(e)}"
            }
    
    def verify_wipe(self, device_path: str, erase_method: str = "format") -> Dict[str, Any]:
        """Verify that the wipe was successful by analyzing device data."""
        print("Verifying wipe completion...")
        
        try:
            # Read sample data from device (100MB for better verification)
            result = subprocess.run(
                ["sudo", "dd", f"if={device_path}", "bs=1M", "count=100", "status=none"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "Failed to read device for verification"
                }
            
            # Convert to binary data for analysis
            data = result.stdout.encode('latin-1')
            total_bytes = len(data)
            
            # Count non-zero bytes
            non_zero_bytes = sum(1 for b in data if b != 0)
            zero_bytes = total_bytes - non_zero_bytes
            zero_percentage = round((zero_bytes / total_bytes) * 100, 2)
            
            # Get hexdump sample (first 64 bytes)
            hexdump_sample = data[:64].hex()
            
            # Determine expected result based on erase method
            if erase_method == "secure_erase":
                # Secure erase should result in mostly zeros
                wipe_effective = non_zero_bytes < (total_bytes * 0.01)  # Less than 1% non-zero
                expected_result = "zeros"
            elif erase_method == "crypto_erase":
                # Crypto erase should result in random data (not all zeros)
                wipe_effective = non_zero_bytes > (total_bytes * 0.5)  # More than 50% non-zero
                expected_result = "random"
            else:  # format
                # Basic format - should be mostly zeros
                wipe_effective = non_zero_bytes < (total_bytes * 0.01)  # Less than 1% non-zero
                expected_result = "zeros"
            
            return {
                "success": True,
                "total_bytes": total_bytes,
                "zero_bytes": zero_bytes,
                "non_zero_bytes": non_zero_bytes,
                "zero_percentage": zero_percentage,
                "expected_result": expected_result,
                "wipe_effective": wipe_effective,
                "hexdump_sample": hexdump_sample,
                "verification_method": "dd_analysis"
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Verification timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Verification failed: {str(e)}"
            }


def execute_main_with_state(state_manager: StateManager):
    """Main function for execute phase with provided state manager."""
    executor = WipeExecutor(state_manager)
    _run_execute_phase(executor, state_manager)

def main():
    """Main function for execute phase."""
    state_manager = StateManager()
    executor = WipeExecutor(state_manager)
    _run_execute_phase(executor, state_manager)

def _run_execute_phase(executor: WipeExecutor, state_manager: StateManager):
    """Run the execute phase logic."""
    
    # Check if plan phase completed
    if state_manager.get_phase_status("plan") != "completed":
        print("❌ Plan phase must be completed first. Run: mise plan")
        return
    
    try:
        # Update phase status
        state_manager.update_phase("execute", "running")
        
        # Execute the wipe
        execution_results = executor.execute_wipe()
        
        # Verify wipe if successful
        if execution_results["erase_operation"]["status"] == "completed":
            plan_data = state_manager.get_phase_data("plan")
            device_path = plan_data["execution_plan"]["device"]["path"]
            verification = executor.verify_wipe(device_path)
            execution_results["verification"] = verification
        
        # Save results to state
        state_manager.update_phase("execute", "completed", execution_results)
        
        # Display results
        operation = execution_results["erase_operation"]
        print(f"\n📊 Execution Summary:")
        print(f"   Method: {operation['method']}")
        print(f"   Status: {operation['status']}")
        print(f"   Duration: {operation['duration']:.3f} seconds ({operation['duration']*1000:.0f} ms)")
        
        if operation["status"] == "completed":
            print("✅ Wipe completed successfully!")
            if "verification" in execution_results:
                verif = execution_results["verification"]
                if verif["success"]:
                    print(f"✅ Verification: {'All zeros' if verif['is_all_zeros'] else 'Non-zero data found'}")
                else:
                    print(f"⚠️  Verification failed: {verif['error']}")
        else:
            print(f"❌ Wipe failed: {operation['error_message']}")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        state_manager.update_phase("execute", "failed", {"error": str(e)})


if __name__ == "__main__":
    main()
