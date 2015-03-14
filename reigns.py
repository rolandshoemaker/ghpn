#!/usr/bin/python3
import argparse, multiprocessing

from redis_worker import run as redis_run
from stats_worker import run as stats_run
from stats_worker import INTERVAL as DEFAULT_STATS_INTERVAL

DEFAULT_REDIS_WORKERS = 4

parser = argparse.ArgumentParser(description="run the stats and redis works all from one place")
parser.add_argument("--redis-workers", default=DEFAULT_REDIS_WORKERS, help="number of redis workers to run")
parser.add_argument("--stats-interval", default=DEFAULT_STATS_INTERVAL, help="time to wait between collecting stats")
args = parser.parse_args()

def r_worker():
    redis_run()
    return

def s_worker(interval):
    stats_run(interval)

# Main
print("# starting stats worker")
stats_job = multiprocessing.Process(target=s_worker, args=(args.stats_interval,))
stats_job.start()

redis_jobs = []
print("# starting %d redis workers" % (args.redis_workers))
for i in range(args.redis_workers):
    p = multiprocessing.Process(target=r_worker)
    redis_jobs.append(p)
    p.start()

