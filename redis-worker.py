import zlib
from redis import StrictRedis

STATS_CACHE_LENGTH = 43200

def compress(stuff):
	return zlib.compress(bytes(stuff.encode("utf-8")))

def decompress(stuff):
	return zlib.decompress(stuff).decode("utf-8")

cache = StrictRedis(host="localhost", db=0)

def run():
	while True:
		if not cache.get("ghpn-cooldown"):
			username = cache.blpop("ghpn-work")
			cache.set("ghpn-working:%s" % (username))
			profile = GHProfileStats.get(username, json_errors=True)
			# need to set expire too!
			if profile.get("error", None):
				expire = 60
				compressed_profile = compress(profile)
			else:
				expire = STATS_CACHE_LENGTH
				compressed_profile = compress(profile.to_json())
			app.cache.setex("ghpn:%s" % (username), STATS_CACHE_LENGTH, compressed_profile)
			app.cache.delete("ghpn-working:%s" % (username))
