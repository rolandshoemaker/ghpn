import zlib, datetime, time
from redis import StrictRedis

from libghpn import GHProfileStats
from common import compress, decompress

from github3 import GitHubError

STATS_CACHE_LENGTH = 5400

cache = StrictRedis(host="localhost", db=0)

def run():
	while True:
		if not cache.get("ghpn-cooldown"):
			username = cache.blpop("ghpn-work")[1].decode("utf-8")
			print(username)
			cache.set("ghpn-working:"+username, 1)
			try:
				profile = GHProfileStats.get(username, json_errors=True)
			except GitHubError:
				if GHProfileStats._debug_remaining_requests()["resources"]["core"]["remaining"] == 0:
					expiration = int((datetime.datetime.utcfromtimestamp(GHProfileStats._debug_remaining_requests()["resources"]["core"]["reset"])-datetime.datetime.utcnow()).total_seconds())
					cache.setex("ghpn-cooldown", expiration, GHProfileStats._debug_remaining_requests()["resources"]["core"]["reset"])
				cache.delete("ghpn-working:%s" % (username))
				continue
			# need to set expire too!
			if profile.__dict__.get("error", None):
				expire = 60
				compressed_profile = compress(profile)
			else:
				expire = STATS_CACHE_LENGTH
				compressed_profile = compress(profile.to_json())
			cache.setex("ghpn:%s" % (username), STATS_CACHE_LENGTH, compressed_profile)
			cache.delete("ghpn-working:%s" % (username))
		else:
			time.sleep(120)

if __name__ == "__main__":
	run()
