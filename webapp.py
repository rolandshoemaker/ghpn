from flask import Flask, make_response, jsonify, render_template, send_from_directory
from redis import StrictRedis
import zlib, json, humanize
from datetime import datetime

from libghpn import GHProfileStats, logo_block, section_header_block
from common import compress, decompress

app = Flask(__name__)
app.cache = StrictRedis(host="localhost", db=0)
app.debug = True

def get_usage_graph():
	usage = json.loads(decompress(app.cache.get("ghpn-stats")))
	return GHProfileStats.construct_event_graph_block("Users cached over 24hr", usage, height=20)

def get_stats(username):
	r_profile = app.cache.get("ghpn:%s" % (username))
	if r_profile:
		# decompress
		decompressed = decompress(r_profile)
		if json.loads(decompressed).get("error", None):
			decompressed_j = json.loads(decompressed)
			return decompressed_j, decompressed_j.get("status_code", None) or decompressed_j.get("error_status_code", None)
		else:
			profile = GHProfileStats.from_json(decompressed)
			return profile, 200
	else:
		if not app.cache.get("ghpn-cooldown"):
			# if not in 'ghpn-work' then add it
			if app.cache.get("ghpn-working:%s" % (username)) or username.encode("utf-8") in app.cache.lrange("ghpn-work", 0, -1):
				return None, 202
			else:
				app.cache.rpush("ghpn-work", username)
				return None, 202
		else:
			cooldown = app.cache.get("ghpn-cooldown")
			cooldown = "%s" % (humanize.naturaltime(datetime.utcnow()-datetime.utcfromtimestamp(int(cooldown.decode("utf-8")))))
			return {"error": "ghpn has hit its GitHub rate limit and cannot proccess any new users, this will reset in %s, already cached users can still be accessed." % (cooldown), "error_status_code": 500}, None

@app.route("/")
def index():
	# search box and SUPER short intro/about
	# one page to rule them all!
	return render_template("index.html", logo=logo_block(), usage=get_usage_graph(), rl=GHProfileStats._debug_remaining_requests()["resources"]["core"])

@app.route("/favicon.ico")
def serv_favicon():
	return ("", 200)

@app.route("/<string:username>")
def get_user(username):
	resp, status_code = get_stats(username)

	headers = {}
	if resp and not isinstance(resp, GHProfileStats):
		blocks = [resp["error"]]
		status_code = resp["error_status_code"]
	elif status_code == 200:
		blocks = resp.get_all_blocks()
		cache_expires = app.cache.ttl("ghpn:%s" % (username))
		headers["cache-control"] = "public, max-age=%d" % (cache_expires)
	elif status_code == 202:
		blocks = []

	return (jsonify({"blocks": blocks}), status_code, headers)

if __name__ == "__main__":
	app.run(host="10.0.0.31", use_reloader=False)
