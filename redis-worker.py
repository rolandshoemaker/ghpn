import zlib
from redis import StrictRedis

from ghpn import GHProfileStats

STATS_CACHE_LENGTH = 43200

def compress(stuff):
	return zlib.compress(bytes(stuff.encode("utf-8")))

def decompress(stuff):
	return zlib.decompress(stuff).decode("utf-8")

cache = StrictRedis(host="localhost", db=0)

def run():
	while True:
		if not cache.get("ghpn-cooldown"):
			username = cache.blpop("ghpn-work")[1].decode("utf-8")
			print(username)
			cache.set("ghpn-working:"+username, 1)
			profile = GHProfileStats.get(username, json_errors=True)
			# need to set expire too!
			if profile.__dict__.get("error", None):
				expire = 60
				compressed_profile = compress(profile)
			else:
				expire = STATS_CACHE_LENGTH
				compressed_profile = compress(profile.to_json())
			cache.setex("ghpn:%s" % (username), STATS_CACHE_LENGTH, compressed_profile)
			cache.delete("ghpn-working:%s" % (username))

run()
