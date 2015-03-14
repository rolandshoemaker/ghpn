import threading, json, zlib
from redis import StrictRedis
from datetime import datetime

from common import compress, decompress

r = StrictRedis(host="localhost", db=0)
INTERVAL = 3600

def collect_usage():
	usage = r.get("ghpn-stats")
	now = datetime.now().hour
	if not usage:
		usage = [[" ", 0] for hour in range(0,25)]
	else:
		usage = json.loads(decompress(usage))
	usage.pop(0)
	usage.append([" ", len(r.keys("ghpn:*"))])
	r.set("ghpn-stats", compress(json.dumps(usage)))

def run(interval=INTERVAL):
	collect_usage()
	threading.Timer(interval, run).start()

if __name__ == "__main__":
	run()
