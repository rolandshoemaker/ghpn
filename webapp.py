from flask import Flask, make_response, jsonify, render_template, send_from_directory
from redis import StrictRedis
import zlib, json, humanize
from datetime import datetime

from ghpn import GHProfileStats, logo_block, section_header_block

app = Flask(__name__)
app.cache = StrictRedis(host="localhost", db=0)
app.debug = True

def compress(stuff):
	return zlib.compress(bytes(stuff.encode("utf-8")))

def decompress(stuff):
	return zlib.decompress(stuff).decode("utf-8")

def get_usage_graph():
	usage = json.loads(decompress(app.cache.get("ghpn-stats")))
	return GHProfileStats.construct_event_graph_block("User cache size over 24hr", usage, height=20)

def get_stats(username):
	r_profile = app.cache.get("ghpn:%s" % (username))
	if r_profile:
		# decompress
		decompressed = decompress(r_profile)
		if json.loads(decompressed).get("error", None):
			decompressed_j = json.loads(decompressed)
			return decompressed_j, decompressed_j["status_code"]
		else:
			profile = GHProfileStats.from_json(decompressed)
			return profile, 200
	else:
		# if not in 'ghpn-work' then add it
		if app.cache.get("ghpn-working:%s" % (username)) or username.encode("utf-8") in app.cache.lrange("ghpn-work", 0, -1):
			return None, 202
		else:
			app.cache.rpush("ghpn-work", username)
			return None, 202

@app.route("/")
def index():
	# search box and SUPER short intro/about
	return render_template("index.html", logo=logo_block(), usage=get_usage_graph(), rl=GHProfileStats._debug_remaining_requests()["resources"]["core"])

@app.route("/favicon.ico")
def serv_favicon():
	return ("", 200)

@app.route("/<string:username>")
def get_user(username):
	# this should actually render a template with the blocks from the profile...
	if not app.cache.get("ghpn-cooldown"):
		resp, status_code = get_stats(username)

		headers = {}
		if resp.get("error", None):
			blocks = [resp.get("error", "")]
			status_code = resp.get("error_status_code", 400)
		elif status_code == 200:
			blocks = resp.get_all_blocks()
			cache_expires = app.cache.ttl("gphn:%s" % (username))
			headers["cache-control"] = "public, max-age=%d" % (cache_expire)
		elif status_code == 202:
			blocks = []

		return (jsonify({"blocks": blocks}), status_code, headers)
	else:
		cooldown = app.cache.get("ghpn-cooldown")
		if cooldown:
			cooldown = "%s" % (humanize.naturaltime(datetime.utcfromtimestamp(int(cooldown.decode("utf-8")))-datetime.utcnow()))
		return (jsonify({"blocks": ["\n".join(["ghpn has hit its GitHub rate limit and cannot proccess any new users, this will reset in %s, already cached users can still be accessed." % (cooldown)])]}), 403)

if __name__ == "__main__":
	app.run(host="10.0.0.31", use_reloader=False)