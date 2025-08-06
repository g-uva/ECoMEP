# workload-producer.py
import os, random, requests, json, time
# TODO: it must be substituted by Localhost if ran locally. Docker is used for in-cluster network calls.
GWS = ["http://host.docker.internal:31110", "http://host.docker.internal:31120", "http://host.docker.internal:31130"]
PW  = os.getenv("PASSWORD")
AUTH= ("admin", PW)

while True:
    gw  = random.choice(GWS)              # naïve round-robin for now
    fn  = random.choice(["resize", "yolo"])
    body= json.dumps({"url":"https://picsum.photos/512"})
    r   = requests.post(f"{gw}/async-function/{fn}", data=body, auth=AUTH)
    print("->", gw, fn, r.status_code)
    time.sleep(0.5)
