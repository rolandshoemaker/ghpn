import threading, json, zlib
from redis import StrictRedis
from datetime import datetime

from common import compress, decompress, get_logger

r = StrictRedis(host="localhost", db=0)
logger = get_logger(logger_name="ghpn-stats-worker")

def collect_usage():
	usage = r.get("ghpn-stats")
	if not usage:
		logger.info("no stats key, creating empty list")
		usage = [[" ", 0] for hour in range(0,25)]
	else:
		usage = json.loads(decompress(usage))
	usage.pop(0)
	user_count = len(r.keys("ghpn:*"))
	usage.append([" ", user_count])
	r.set("ghpn-stats", compress(json.dumps(usage)))
	logger.info("collected stats|cached_users=%d" % (user_count))

def run(interval):
	collect_usage()
	threading.Timer(interval, run).start()

if __name__ == "__main__":
	run()
