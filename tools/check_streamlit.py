import urllib.request
import sys

url = 'http://localhost:8501'
try:
    with urllib.request.urlopen(url, timeout=5) as r:
        data = r.read(2000)
        print('STATUS', r.status)
        print(data.decode('utf-8', errors='replace'))
except Exception as e:
    print('ERROR', repr(e))
    sys.exit(1)
