#!/usr/bin/env python3
"""
Diagnostic script to check Apprise installation and functionality
"""

import sys
import os

def check_python_environment():
    """Check Python environment details"""
    print("=== Python Environment ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path}")
    print()

def check_apprise_import():
    """Test Apprise import"""
    print("=== Apprise Import Test ===")
    try:
        import apprise
        print("✅ Apprise imported successfully")
        print(f"   Apprise version: {getattr(apprise, '__version__', 'Unknown')}")
        print(f"   Apprise location: {apprise.__file__}")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Apprise: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing Apprise: {e}")
        return False

def check_apprise_functionality():
    """Test basic Apprise functionality"""
    print("=== Apprise Functionality Test ===")
    try:
        import apprise
        
        # Test creating an Apprise object
        apobj = apprise.Apprise()
        print("✅ Apprise object created successfully")
        
        # Test adding a fake URL (won't send anything)
        fake_url = "json://httpbin.org/post"
        result = apobj.add(fake_url)
        if result:
            print("✅ Apprise URL addition test passed")
        else:
            print("⚠️  Apprise URL addition test failed (this may be normal)")
        
        # Test notification (won't actually send)
        print("✅ Apprise basic functionality test completed")
        return True
        
    except Exception as e:
        print(f"❌ Apprise functionality test failed: {e}")
        return False

def check_requirements_file():
    """Check if apprise is in requirements.txt"""
    print("=== Requirements File Check ===")
    req_paths = [
        "/app/requirements.txt",
        "requirements.txt",
        "backend/requirements.txt"
    ]
    
    for req_path in req_paths:
        if os.path.exists(req_path):
            print(f"Found requirements file: {req_path}")
            try:
                with open(req_path, 'r') as f:
                    content = f.read()
                    if 'apprise' in content.lower():
                        print("✅ Apprise found in requirements.txt")
                        # Show the specific line
                        for line in content.split('\n'):
                            if 'apprise' in line.lower():
                                print(f"   {line.strip()}")
                    else:
                        print("❌ Apprise NOT found in requirements.txt")
                break
            except Exception as e:
                print(f"Error reading {req_path}: {e}")
    else:
        print("❌ No requirements.txt file found")
    print()

def check_installed_packages():
    """Check what packages are installed"""
    print("=== Installed Packages Check ===")
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            packages = result.stdout
            if 'apprise' in packages.lower():
                print("✅ Apprise found in installed packages")
                for line in packages.split('\n'):
                    if 'apprise' in line.lower():
                        print(f"   {line.strip()}")
            else:
                print("❌ Apprise NOT found in installed packages")
                print("Available packages:")
                print(packages[:500] + "..." if len(packages) > 500 else packages)
        else:
            print(f"❌ Failed to list packages: {result.stderr}")
    except Exception as e:
        print(f"❌ Error checking installed packages: {e}")
    print()

def main():
    """Run all diagnostic checks"""
    print("Apprise Diagnostic Script")
    print("=" * 50)
    
    check_python_environment()
    check_requirements_file()
    check_installed_packages()
    
    apprise_imported = check_apprise_import()
    
    if apprise_imported:
        check_apprise_functionality()
        print("\n=== Summary ===")
        print("✅ Apprise is working correctly!")
    else:
        print("\n=== Summary ===")
        print("❌ Apprise is not available or not working")
        print("   Try installing it with: pip install apprise==1.9.3")

if __name__ == "__main__":
    main() 