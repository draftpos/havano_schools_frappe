import json
import sys

with open(sys.argv[1], 'r') as f:
    data = json.load(f)

fieldnames = [f.get('fieldname') for f in data.get('fields', [])]
duplicates = set([x for x in fieldnames if fieldnames.count(x) > 1])
if duplicates:
    print(f"DUPLICATES: {duplicates}")
else:
    print("NO DUPLICATES")
