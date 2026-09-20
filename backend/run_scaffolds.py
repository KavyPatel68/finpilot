import os
import sys

base_dir = r'c:\Users\patel\OneDrive\Desktop\ai agent\finpilot\backend'
sys.path.append(base_dir)

try:
    with open('scaffold1.py', 'r') as f:
        exec(f.read())
    with open('scaffold2.py', 'r') as f:
        exec(f.read())
    with open('scaffold3.py', 'r') as f:
        exec(f.read())
    with open('scaffold4.py', 'r') as f:
        exec(f.read())
    print("ALL FILES CREATED SUCCESSFULLY USING EMBEDDED PYTHON.")
except Exception as e:
    print("Error:", e)
