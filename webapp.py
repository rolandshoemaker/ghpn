from flask import Flask, Response, jsonify, render_template
from redis import StrictRedis
import zlib

from ghpn import GHProfileStats

STATS_CACHE_LENGTH = 7200

app = Flask(__name__)
app.redis = StrictRedis(host="localhost")

def get_stats(username):
	r_profile = app.redis.get("ghpn:%s" % (username))
	if r_profile:
		# decompress
		decompressed_profile = zlib.decompress(r_profile).decode("utf-8")
		profile = GHProfileStats.from_json(decompressed_profile)
	else:
		profile = GHProfileStats.get(username)
		if not profile:
			# FIXME: return a bad thing!
			pass
		# compress and store in redis
		compressed_profile = zlib.compress(bytes(profile.to_json().encode("utf-8")))
		# need to set expire too!
		app.redis.setex("ghpn:%s" % (username), STATS_CACHE_LENGTH, compressed_profile) 
	return profile, 200

@app.route("/")
def index():
	# search box and SUPER short intro/about
	return "lol"

@app.route("/<string:username>")
def get_user(username):
	# this should actually render a template with the blocks from the profile...
	if username == "favicon.ico":
		# go awway for now
		return Response(status=200)
	stats, status_code = get_stats(username)
	blocks = stats.get_all_blocks()
	return render_template("user.html", blocks=blocks, username=stats.username)

if __name__ == "__main__":
	app.run(debug=True, host="10.0.0.31")