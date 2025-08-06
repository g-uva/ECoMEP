# workload-producer.py
import os, random, requests, json, time
GWS = ["http://localhost:31110", "http://localhost:31120", "http://localhost:31130"]
PW  = os.getenv("PASSWORD")
AUTH= ("admin", PW)

while True:
    gw  = random.choice(GWS)              # naïve round-robin for now
    fn  = random.choice(["resize", "yolo"])
    body= json.dumps({"url":"https://picsum.photos/512"})
    r   = requests.post(f"{gw}/async-function/{fn}", data=body, auth=AUTH)
    print("->", gw, fn, r.status_code)
    time.sleep(0.5)
