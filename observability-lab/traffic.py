import urllib.request
import urllib.error
import time

endpoints = [
    ("http://localhost:8000/", 8),
    ("http://localhost:8000/health", 6),
    ("http://localhost:8000/slow?delay=0.5", 4),
    ("http://localhost:8000/error", 3),
    ("http://localhost:8000/error?type=validation", 2),
]

print("Generating telemetry traffic...")
for url, count in endpoints:
    for i in range(count):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as res:
                print(f"[{res.status}] {url}")
        except urllib.error.HTTPError as e:
            print(f"[{e.code} Expected] {url}")
        except Exception as ex:
            print(f"[Error] {url}: {ex}")
        time.sleep(0.05)

print("\nTraffic generated successfully! Check Grafana, Prometheus, and Jaeger.")
