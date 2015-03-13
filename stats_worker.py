import threading, json, zlib
from redis import StrictRedis
from datetime import datetime

from common import compress, decompress

r = StrictRedis(host="localhost", db=0)
INTERVAL = 3600

def run():
	usage = r.get("ghpn-s")
	now = datetime.now().hour
	if not usage:
		usage = [[" ", 0] for hour in range(0,25)]
	else:
		usage = json.loads(decompress(usage))
	usage.pop(0)
	usage.append([" ", len(r.keys("ghpn:*"))])
	r.set("ghpn-stats", compress(json.dumps(usage)))

def do_it():
	run()
	threading.Timer(INTERVAL, do_it).start()

if __name__ == "__main__":
	do_it()