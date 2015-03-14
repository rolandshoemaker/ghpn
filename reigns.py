#!/usr/bin/python3
import argparse, multiprocessing, signal

from redis_worker import run as redis_run
from stats_worker import run as stats_run
from common import get_logger

DEFAULT_REDIS_WORKERS = 4
DEFAULT_STATS_INTERVAL = 3600

parser = argparse.ArgumentParser(description="run the stats and redis works all from one place")
parser.add_argument("--redis-workers", default=DEFAULT_REDIS_WORKERS, help="number of redis workers to run")
parser.add_argument("--stats-interval", default=DEFAULT_STATS_INTERVAL, help="time to wait between collecting cached user stats")
args = parser.parse_args()

logger = get_logger(logger_name="ghpn-reigns")
logger.info("starting up!")

def r_worker():
    redis_run()
    return

# Main
logger.info("starting stats worker")
stats_run(args.stats_interval)

redis_jobs = []
def exiter(signal, frame):
	for p in redis_jobs:
		p.terminate()
	logger.info("killed redis worker processes")
	logger.info("ghpn-reigns has shutdown!")
	exit(0)
	
logger.info("registering signal handler")
signal.signal(signal.SIGINT, exiter)

logger.info("starting %d redis worker processes" % (args.redis_workers))
for i in range(args.redis_workers):
    p = multiprocessing.Process(target=r_worker)
    redis_jobs.append(p)
    p.start()


