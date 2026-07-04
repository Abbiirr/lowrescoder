"""Environment setup detection and validation for meta-autocode.

Detects build system from file contents and generates setup commands.
This is Phase 5 of meta-autocode.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List


class BuildSystem(Enum):
    """Build system types detected by EnvironmentSetup."""
    PYTHON_PIP = "PYTHON_PIP"
    PYTHON_UV = "PYTHON_UV"  
    NODE_NPM = "NODE_NPM"
    UNKNOWN = "UNKNOWN"


@dataclass
class SetupResult:
    """Result of environment setup validation."""
    success: bool
    build_system: str
    commands_run: List[str]
    error: str = ""


class EnvironmentSetup:
    """Detects build system and generates setup commands."""

    def __init__(self, files: dict[str, str]) -> None:
        """Detect build system from file contents.
        
        Args:
            files: Dictionary mapping filenames to their contents
        """
        self.files = files
        self.build_system = self._detect_build_system()

    def _detect_build_system(self) -> BuildSystem:
        """Detect the build system from file contents.
        
        Returns:
            The detected BuildSystem enum value
        """
        # Check for NODE_NPM first (package.json present)
        if "package.json" in self.files:
            return BuildSystem.NODE_NPM
        
        # Check for Python build systems
        if "pyproject.toml" in self.files:
            content = self.files["pyproject.toml"]
            if "[build-system]" in content or "[project]" in content:
                return BuildSystem.PYTHON_UV
            # If pyproject.toml exists but doesn't match UV criteria, fall back to PIP
            return BuildSystem.PYTHON_PIP
        
        # Check for requirements.txt (traditional pip setup)
        if "requirements.txt" in self.files:
            return BuildSystem.PYTHON_PIP
        
        # No known build system detected
        return BuildSystem.UNKNOWN

    def setup_commands(self) -> list[str]:
        """Generate setup commands based on detected build system.
        
        Returns:
            List of shell commands to set up the environment
        """
        if self.build_system == BuildSystem.PYTHON_PIP:
            if "requirements.txt" in self.files:
                return ["pip install -r requirements.txt"]
            return []
        elif self.build_system == BuildSystem.PYTHON_UV:
            return ["uv sync"]
        elif self.build_system == BuildSystem.NODE_NPM:
            return ["npm install"]
        else:  # UNKNOWN
            return []

    def validate(self) -> SetupResult:
        """Validate the environment setup.
        
        Returns:
            SetupResult indicating success and containing build system info
        """
        return SetupResult(
            success=True,
            build_system=self.build_system.value,
            commands_run=self.setup_commands()
        )