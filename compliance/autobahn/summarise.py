import json
import sys

with open('reports/servers/index.json') as file_:
    report = json.load(file_)

failures = sum(value['behavior'] == 'FAILED' for value in report['websockets'].values())

if failures > 0:
    sys.exit(1)
else:
    sys.exit(0)
