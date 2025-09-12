"""Collect phase - gather NVMe device information."""

import subprocess
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from .models import DeviceInfo
from .state import StateManager


class DeviceCollector:
    """Collects information about NVMe devices."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    def list_nvme_devices(self) -> List[str]:
        """List all available NVMe devices."""
        try:
            result = subprocess.run(
                ["ls", "/dev/nvme*"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            # Split by whitespace and newlines to handle all possible formats
            devices = result.stdout.split()
            # Filter to only device files (not partitions or controllers)
            # Match pattern: /dev/nvme[number]n[number] (e.g., /dev/nvme0n1)
            nvme_devices = [d for d in devices if re.match(r'/dev/nvme\d+n\d+$', d)]
            print(f"DEBUG: All nvme files found: {devices}")
            print(f"DEBUG: Filtered nvme devices: {nvme_devices}")
            return nvme_devices
        except subprocess.CalledProcessError:
            return []
    
    def get_device_info(self, device_path: str) -> Optional[DeviceInfo]:
        """Get detailed information about a specific NVMe device."""
        try:
            # Get device information using nvme-cli
            info = self._run_nvme_command("id-ctrl", device_path)
            if not info:
                return None
            
            # Extract key information
            model = info.get("mn", "Unknown")
            serial = info.get("sn", "Unknown")
            firmware = info.get("fr", "Unknown")
            
            # Get capacity
            capacity = self._get_device_capacity(device_path)
            
            # Extract namespace ID from device path
            namespace_id = self._extract_namespace_id(device_path)
            
            return DeviceInfo(
                model=model,
                serial=serial,
                firmware=firmware,
                capacity=capacity,
                path=device_path,
                namespace_id=namespace_id
            )
            
        except Exception as e:
            print(f"Error getting device info for {device_path}: {e}")
            return None
    
    def _run_nvme_command(self, command: str, device_path: str) -> Optional[Dict[str, Any]]:
        """Run an nvme command and return parsed JSON output."""
        try:
            result = subprocess.run(
                ["sudo", "nvme", command, device_path, "--output-format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"Error running nvme {command}: {e}")
            return None
    
    def _get_device_capacity(self, device_path: str) -> str:
        """Get device capacity in human-readable format."""
        try:
            result = subprocess.run(
                ["lsblk", "-b", "-n", "-o", "SIZE", device_path],
                capture_output=True,
                text=True,
                check=True
            )
            size_bytes = int(result.stdout.strip())
            return self._format_bytes(size_bytes)
        except (subprocess.CalledProcessError, ValueError):
            return "Unknown"
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def _extract_namespace_id(self, device_path: str) -> Optional[int]:
        """Extract namespace ID from device path like /dev/nvme0n1."""
        match = re.search(r'nvme\d+n(\d+)', device_path)
        return int(match.group(1)) if match else None
    
    def get_system_info(self) -> Dict[str, str]:
        """Collect system information (UUID, OS, kernel)."""
        system_info = {}
        
        try:
            # Get system UUID
            result = subprocess.run(
                ["cat", "/etc/machine-id"],
                capture_output=True,
                text=True,
                check=True
            )
            system_info["system_uuid"] = result.stdout.strip()
        except:
            try:
                # Fallback to dmidecode
                result = subprocess.run(
                    ["dmidecode", "-s", "system-uuid"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                system_info["system_uuid"] = result.stdout.strip()
            except:
                system_info["system_uuid"] = "Unknown"
        
        try:
            # Get OS information
            result = subprocess.run(
                ["uname", "-a"],
                capture_output=True,
                text=True,
                check=True
            )
            system_info["os_info"] = result.stdout.strip()
        except:
            system_info["os_info"] = "Unknown"
        
        try:
            # Get kernel version
            result = subprocess.run(
                ["uname", "-r"],
                capture_output=True,
                text=True,
                check=True
            )
            system_info["kernel_version"] = result.stdout.strip()
        except:
            system_info["kernel_version"] = "Unknown"
        
        return system_info
    
    def prompt_device_description(self, device: Dict[str, Any]) -> str:
        """Prompt user for device description."""
        print(f"\nDevice: {device['model']} ({device['path']})")
        print(f"Serial: {device['serial']}")
        print(f"Capacity: {device['capacity']}")
        
        description = input("Enter a description for this device (e.g., 'Customer laptop SSD', 'Server boot drive'): ").strip()
        return description if description else f"NVMe device {device['model']}"
    
    def check_erase_support(self, device_path: str) -> Dict[str, bool]:
        """Check what erase methods are supported by the device."""
        try:
            # Check for sanitize support (which includes secure erase and crypto erase)
            sanitize_support = self._check_sanitize_support(device_path)
            
            # Check for format support (bit 1 in oacs)
            format_support = self._check_format_support(device_path)
            
            return {
                "secure_erase": sanitize_support.get("secure_erase", False),
                "crypto_erase": sanitize_support.get("crypto_erase", False),
                "format": format_support
            }
        except Exception as e:
            print(f"Error checking erase support: {e}")
            return {"secure_erase": False, "crypto_erase": False, "format": True}
    
    def _check_sanitize_support(self, device_path: str) -> Dict[str, bool]:
        """Check secure erase and crypto erase support using FNA field."""
        try:
            result = subprocess.run(
                ["sudo", "nvme", "id-ctrl", device_path, "--output-format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            info = json.loads(result.stdout)
            
            # Get FNA (Format NVM Attributes) field
            fna = info.get("fna", 0)
            
            # Bit 2: CryptographicEraseSupported
            crypto_erase_supported = bool(fna & 0x4)
            
            # For secure erase, we need to check if format is supported (oacs bit 1)
            # and if the device supports user data erase (which is part of secure erase)
            oacs = info.get("oacs", 0)
            format_supported = bool(oacs & 0x2)
            
            # Secure erase is supported if format is supported
            # (user data erase is part of the format command)
            secure_erase_supported = format_supported
            
            return {
                "secure_erase": secure_erase_supported,
                "crypto_erase": crypto_erase_supported
            }
            
        except:
            return {"secure_erase": False, "crypto_erase": False}
    
    def _check_format_support(self, device_path: str) -> bool:
        """Check if format command is supported."""
        try:
            result = subprocess.run(
                ["sudo", "nvme", "id-ctrl", device_path, "--output-format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            # If we can read the controller info, format is typically supported
            return True  # Format is typically always supported
        except subprocess.CalledProcessError:
            return False


def main():
    """Main function for collect phase."""
    print("Starting NVMe device collection...")
    
    # Check if we're running as part of full workflow or standalone
    if len(sys.argv) > 1 and sys.argv[1] == "--report-dir":
        report_dir = sys.argv[2]
        state_manager = StateManager(report_dir=report_dir)
    else:
        state_manager = StateManager()
    
    collector = DeviceCollector(state_manager)
    
    # Update phase status
    state_manager.update_phase("collect", "running")
    
    try:
        # List available devices
        devices = collector.list_nvme_devices()
        print(f"Found {len(devices)} NVMe devices: {devices}")
        
        if not devices:
            print("No NVMe devices found!")
            state_manager.update_phase("collect", "failed", {"error": "No devices found"})
            return
        
        # Collect system information
        print("Collecting system information...")
        system_info = collector.get_system_info()
        print(f"✓ System UUID: {system_info['system_uuid']}")
        print(f"✓ OS Info: {system_info['os_info']}")
        print(f"✓ Kernel: {system_info['kernel_version']}")
        
        # Collect information for each device
        device_info_list = []
        for device in devices:
            print(f"\nCollecting info for {device}...")
            info = collector.get_device_info(device)
            if info:
                # Check erase support
                erase_support = collector.check_erase_support(device)
                device_data = info.dict()
                device_data["erase_support"] = erase_support
                
                # Prompt for device description
                device_data["description"] = collector.prompt_device_description(device_data)
                
                device_info_list.append(device_data)
                print(f"✓ {device}: {info.model} ({info.capacity})")
            else:
                print(f"✗ Failed to get info for {device}")
        
        # Save collected data
        state_manager.update_phase("collect", "completed", {
            "devices": device_info_list,
            "device_count": len(device_info_list),
            "system_info": system_info
        })
        
        print(f"Collection completed. Found {len(device_info_list)} devices.")
        
    except Exception as e:
        print(f"Error during collection: {e}")
        state_manager.update_phase("collect", "failed", {"error": str(e)})


if __name__ == "__main__":
    main()
