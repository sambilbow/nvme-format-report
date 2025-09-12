"""State management for NVMe wipe operations."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class StateManager:
    """Manages the state JSON file for tracking wipe operations."""
    
    def __init__(self, state_file: str = "build/state.json", report_dir: str = "build"):
        self.state_file = Path(state_file)
        self.report_dir = Path(report_dir)
        self.state_file.parent.mkdir(exist_ok=True)
        self.report_dir.mkdir(exist_ok=True)
        self._state: Dict[str, Any] = {}
        self._load_state()
    
    def _load_state(self) -> None:
        """Load existing state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self._state = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self._state = {}
        else:
            self._state = {
                "created_at": datetime.now().isoformat(),
                "phases": {
                    "collect": {"status": "pending", "data": {}},
                    "plan": {"status": "pending", "data": {}},
                    "execute": {"status": "pending", "data": {}},
                    "report": {"status": "pending", "data": {}}
                }
            }
    
    def save_state(self) -> None:
        """Save current state to file."""
        self._state["updated_at"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self._state, f, indent=2, default=str)
    
    def update_phase(self, phase: str, status: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Update a specific phase with status and data."""
        if phase not in self._state["phases"]:
            raise ValueError(f"Unknown phase: {phase}")
        
        self._state["phases"][phase]["status"] = status
        if data:
            self._state["phases"][phase]["data"].update(data)
        
        self.save_state()
    
    def get_phase_data(self, phase: str) -> Dict[str, Any]:
        """Get data for a specific phase."""
        return self._state["phases"].get(phase, {}).get("data", {})
    
    def get_phase_status(self, phase: str) -> str:
        """Get status for a specific phase."""
        return self._state["phases"].get(phase, {}).get("status", "pending")
    
    def get_state(self) -> Dict[str, Any]:
        """Get the complete state."""
        return self._state.copy()
    
    def get_report_dir(self) -> Path:
        """Get the report directory path."""
        return self.report_dir
