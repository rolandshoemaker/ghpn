from flask import Flask, make_response, jsonify, render_template, send_from_directory
from redis import StrictRedis
import zlib, json
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
		if app.cache.get("ghpn-working:%s" % (username)) or username in app.cache.zrange("ghpn-work", 0, -1):
			return None, 202
		else:
			app.cache.rpush("ghpn-work", username)
			return None, 202

@app.route("/")
def index():
	# search box and SUPER short intro/about
	return render_template("index.html", logo=logo_block(), usage=get_usage_graph(), rl=GHProfileStats._debug_remaining_requests()["resources"]["core"], cooldown=app.cache.get("ghpn-cooldown"))

@app.route("/favicon.ico")
def serv_favicon():
	pass

@app.route("/<string:username>")
def get_user(username):
	# this should actually render a template with the blocks from the profile...
	if not app.cache.get("ghpn-cooldown"):
		resp, status_code = get_stats(username)
		if status_code == 200:
			blocks = resp.get_all_blocks()
		elif status_code == 202:
			blocks = []
		else:
			blocks = ["\n".join([section_header_block("ERROR"), resp.get("error", "")])]
		return make_response(jsonify({"blocks": blocks}), status_code)

if __name__ == "__main__":
	app.run(host="10.0.0.31", use_reloader=False)