#!/usr/bin/env python
"""
run.py - Simple root runner that calls the main runner in src/
"""
import subprocess
import sys

if __name__ == "__main__":
    print("🎯 AlphaBetting System")
    print("======================")
    print("Redirecting to src/run.py...")
    print("-" * 40)
    
    # Run src/run.py with the same arguments
    result = subprocess.run([sys.executable, "src/run.py"] + sys.argv[1:])
    
    # Exit with the same code
    sys.exit(result.returncode)
