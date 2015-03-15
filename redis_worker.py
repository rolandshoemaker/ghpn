import zlib, datetime, time, json, humanize
from redis import StrictRedis

from libghpn import GHProfileStats
from common import compress, decompress, get_logger

from github3 import GitHubError

STATS_CACHE_LENGTH = 5400

cache = StrictRedis(host="localhost", db=0)
logger = get_logger(logger_name="ghpn-redis-worker")

def run():
	logger.info("redis worker started")
	while True:
		if not cache.get("ghpn-cooldown"):
			username = cache.blpop("ghpn-work")[1].decode("utf-8")
			cache.set("ghpn-working:"+username, 1)
			DEBUG = {"username": username, "start_rl": GHProfileStats._debug_remaining_requests()["resources"]["core"]["remaining"], "start_t": time.time()}
			try:
				profile = GHProfileStats.get(username, json_errors=True)
				DEBUG["request_t"] = time.time()-DEBUG["start_t"]
				DEBUG["num_requests"] = DEBUG["start_rl"]-GHProfileStats._debug_remaining_requests()["resources"]["core"]["remaining"]
			except GitHubError:
				if GHProfileStats._debug_remaining_requests()["resources"]["core"]["remaining"] == 0:
					expiration = int((datetime.datetime.utcfromtimestamp(GHProfileStats._debug_remaining_requests()["resources"]["core"]["reset"])-datetime.datetime.utcnow()).total_seconds())
					cache.setex("ghpn-cooldown", expiration, GHProfileStats._debug_remaining_requests()["resources"]["core"]["reset"])
					logger.warn("github rate limit hit, set cooldown! reset in %s" % (humanize.naturaldelta(expiration)))
					# cache.rpush("ghpn-work", username)
					# clear ghpn-work list so we dont randomly process old users in the queue when rate limit resets.
				else:
					logger.error("error man hmm")
				cache.delete("ghpn-working:%s" % (username))
				continue
			# need to set expire too!
			
			if not isinstance(profile, GHProfileStats):
				expire = 60
				compressed_profile = compress(json.dumps(profile))
				logger.warn("processing error|username=%s|took=%d|requests=%d|rps=%.2f|error=%s" % (username, DEBUG["request_t"], DEBUG["num_requests"], DEBUG["num_requests"]/DEBUG["request_t"], profile["error"]))
			else:
				expire = STATS_CACHE_LENGTH
				compressed_profile = compress(profile.to_json())
				logger.info("processed user|username=%s|took=%d|requests=%d|rps=%.2f" % (username, DEBUG["request_t"], DEBUG["num_requests"], DEBUG["num_requests"]/DEBUG["request_t"]))
			cache.setex("ghpn:%s" % (username), expire, compressed_profile)
			cache.delete("ghpn-working:%s" % (username))
		else:
			time.sleep(120)

if __name__ == "__main__":
	run()
