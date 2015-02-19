from flask import Flask, Response, jsonify, render_template, send_from_directory
from redis import StrictRedis
import zlib, json
from datetime import datetime

from ghpn import GHProfileStats, logo_block

STATS_CACHE_LENGTH = 43200

app = Flask(__name__)
app.cache = StrictRedis(host="localhost", db=0)
app.debug = True

def compress(stuff):
	return zlib.compress(bytes(stuff.encode("utf-8")))

def decompress(stuff):
	return zlib.decompress(stuff).decode("utf-8")

def get_usage_graph():
	usage = json.loads(decompress(app.cache.get("ghpn-s")))
	return GHProfileStats.construct_event_graph_block("User cache size over 24hr", usage, height=20)

def get_stats(username):
	r_profile = app.cache.get("ghpn:%s" % (username))
	if r_profile:
		# decompress
		profile = GHProfileStats.from_json(decompress(r_profile))
		return profile, 200
	else:
		pass		

@app.route("/")
def index():
	# search box and SUPER short intro/about
	return render_template("index.html", logo=logo_block(), usage=get_usage_graph(), rl=GHProfileStats._debug_remaining_requests())

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
	app.run(host="10.0.0.31")