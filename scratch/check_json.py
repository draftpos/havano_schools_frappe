import json
import sys

try:
    with open(sys.argv[1], 'r') as f:
        json.load(f)
    print("VALID")
except Exception as e:
    print(f"INVALID: {e}")
