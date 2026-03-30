#!/usr/bin/env python3
"""
ARIA Dependency Validator and Installer
Ensures all required packages are installed before runtime
"""

import subprocess
import sys
import importlib
from pathlib import Path

class DependencyChecker:
    """Check and install missing dependencies."""
    
    REQUIRED_PACKAGES = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'mlx': 'mlx',
        'mlx_lm': 'mlx-lm',
        'pydantic': 'pydantic',
        'psutil': 'psutil',
    }
    
    OPTIONAL_PACKAGES = {
        'requests': 'requests',
        'python-dotenv': 'python-dotenv',
    }
    
    @classmethod
    def check_python_version(cls):
        """Verify Python 3.11+ is running."""
        if sys.version_info < (3, 11):
            print(f"❌ Python 3.11+ required (found {sys.version_info.major}.{sys.version_info.minor})")
            sys.exit(1)
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    @classmethod
    def check_package(cls, import_name, package_name):
        """Check if a package is installed."""
        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
    
    @classmethod
    def install_package(cls, package_name):
        """Install a package using pip."""
        try:
            print(f"  Installing {package_name}...", end=" ")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", package_name],
                check=True,
                capture_output=True
            )
            print("✓")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed")
            return False
    
    @classmethod
    def validate_all(cls):
        """Check and install all dependencies."""
        print("\n" + "="*60)
        print("ARIA DEPENDENCY VALIDATION")
        print("="*60 + "\n")
        
        # Check Python version
        cls.check_python_version()
        
        # Check required packages
        print("\nChecking required packages:")
        missing_required = []
        
        for import_name, package_name in cls.REQUIRED_PACKAGES.items():
            if cls.check_package(import_name, package_name):
                print(f"  ✅ {package_name}")
            else:
                print(f"  ❌ {package_name} (MISSING)")
                missing_required.append(package_name)
        
        # Check optional packages
        print("\nChecking optional packages:")
        for import_name, package_name in cls.OPTIONAL_PACKAGES.items():
            if cls.check_package(import_name, package_name):
                print(f"  ✅ {package_name}")
            else:
                print(f"  ⚠️  {package_name} (optional, not critical)")
        
        # Install missing required packages
        if missing_required:
            print(f"\n⚠️  Installing {len(missing_required)} missing package(s)...")
            
            for package in missing_required:
                if not cls.install_package(package):
                    print(f"\n❌ Failed to install {package}")
                    print("Please install manually: pip install {package}")
                    sys.exit(1)
            
            print(f"\n✅ All required packages installed successfully")
        else:
            print("\n✅ All required packages already installed")
        
        print("\n" + "="*60)
        print("VALIDATION COMPLETE - Ready to run ARIA")
        print("="*60 + "\n")
        
        return True

if __name__ == "__main__":
    try:
        if DependencyChecker.validate_all():
            sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        sys.exit(1)
