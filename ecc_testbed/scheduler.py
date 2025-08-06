# scheduler.py  (edge of simplicity!)
import requests, subprocess, os, time, json

PROMS = {"edge": "http://localhost:31110/prometheus",
         "fog":  "http://localhost:31120/prometheus",
         "cloud":"http://localhost:31130/prometheus"}
FAAS  = {"edge": "http://localhost:31110",
         "fog":  "http://localhost:31120",
         "cloud":"http://localhost:31130"}
PW    = os.getenv("PASSWORD")

def get_cpu(cluster):
    q = '100 - (avg by(instance)(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    r = requests.get(f"{PROMS[cluster]}/api/v1/query", params={"query":q}).json()
    return float(r["data"]["result"][0]["value"][1])

while True:
    loads = {c:get_cpu(c) for c in PROMS}
    best  = min(loads, key=loads.get)           # pick least-loaded cluster
    if loads[best] < 50:                        # threshold
        # deploy function if not present
        subprocess.run(["faas-cli","deploy","--gateway",FAAS[best],
                        "--image","functions/alpine:latest",
                        "--name","resize","--env","mode=resize",
                        "--annotation","tier="+best], check=False)
    time.sleep(30)