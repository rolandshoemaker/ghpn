import threading, json, zlib
from redis import StrictRedis
from datetime import datetime

r = StrictRedis(host="localhost", db=0)
INTERVAL = 3600

def compress(stuff):
	return zlib.compress(bytes(stuff.encode("utf-8")))

def decompress(stuff):
	return zlib.decompress(stuff).decode("utf-8")

def set_usage():
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
	set_usage()
	threading.Timer(INTERVAL, do_it).start()

if __name__ == "__main__":
	do_it()