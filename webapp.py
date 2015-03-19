from redis import StrictRedis
import zlib, json, humanize, os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from flask import Flask, make_response, jsonify, render_template, send_from_directory, url_for, g, redirect
from flask.ext.github import GitHub as GitHub_flask

from libghpn import GHProfileStats, logo_block, section_header_block
from common import compress, decompress

##################
# oauth token db #
##################

engine = create_engine("sqlite:///oauth_tokens.db")
db = scoped_session(sessionmaker(autocommit=False, bind=engine))

Base = declarative_base()

def init_db():
	Base.metadata.create_all(bind=engine)

class User(Base):
	__tablename__ = "users"
	id = Column(Integer, primary_key=True)
	github_access_token = Column(String(200))

	def __init__(self, token):
		self.github_access_token = token

##############################
# flask + github-flask setup #
##############################

app = Flask(__name__)
app.cache = StrictRedis(host="localhost", db=0)
app.debug = True
app.config["SECRET_KEY"] = "uuid?"
app.config["GITHUB_CLIENT_ID"] = os.environ["GHPN_CLIENT_ID"]
app.config["GITHUB_CLIENT_SECRET"] = os.environ["GHPN_CLIENT_SECRET"]

github_oauth = GitHub_flask(app)

##################
# ghpn-web utils #
##################

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
		if not app.cache.get("ghpn-cooldown:%d" % (g.user.id)):
			# if not in 'ghpn-work' then add it
			if app.cache.get("ghpn-working:%s" % (username)) or username.encode("utf-8") in app.cache.lrange("ghpn-work", 0, -1):
				return None, 202
			else:
				app.cache.rpush("ghpn-work", "%s %s %d" % (username, token, g.user.id))
				return None, 202
		else:
			cooldown = app.cache.get("ghpn-cooldown:%d" % (g.user.id))
			cooldown = "%s" % (humanize.naturaltime(datetime.utcnow()-datetime.utcfromtimestamp(int(cooldown.decode("utf-8")))))
			return {"error": "You have hit your GitHub rate limit so ghpn cannot proccess any new users, this will reset in %s, already cached users can still be accessed." % (cooldown), "error_status_code": 403}, None # Wrong error code!


###############
# ghpn routes #
###############

@app.route("/")
def index():
	# search box and SUPER short intro/about
	# one page to rule them all!
	if g.user:
		rl = GHProfileStats(token=g.user.github_access_token)._debug_remaining_requests # think this should work...?
	else:
		rl = None
	return render_template("index.html", logo=logo_block(), usage=get_usage_graph(), rl=rl, user=g.user)

@app.route("/favicon.ico")
def serve_favicon():
	return ("", 200)

@app.route("/<string:username>")
def get_user(username):
	if g.user:
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
	else:
		return (jsonify({"blocks": ["you are not logged in!"]}), 403)

#############################
# github oauth routes/utils #
#############################

@app.before_request
def before_request():
	g.user = None
	if "user_id" in session:
		g.user = User.query.get(session["user_id"])

@app.after_request
def after_request(response):
	db.remove()
	return response

@app.route("/login")
def login():
	if not g.user:
		return github_oauth.authorize()
	else:
		return ("already logged in", 403)

@app.route("/logout")
def logout():
	if g.user:
		session.pop("user_id", None)
		db.delete(g.user)
		db.commit()
		return redirect(url_for("index"))
	else:
		return ("not logged in", 403)

@app.route("/gh-callback")
@github_oauth.authorized_handler
def authorized(oauth_token):
	if not oauth_token:
		flash("authorization failed!")
		return redirect(url_for("index"))

	user = User.query.filter_by(github_access_token=oauth_token).first()
	if not user:
        db.add(User(oauth_token))
    else:
    	user.github_access_token = oauth_token
    db.commit()
    session["user_id"] = user.id # this should probably be uh... better?
    return redirect(url_for("index"))

# this may not actually be needed since we aren't using github-flask to make any requests...?
@github.access_token_getter
def token_getter():
    if g.user:
        return g.user.github_access_token

##############
# dev server #
##############

if __name__ == "__main__":
	init_db()
	app.run(host="10.0.0.31", use_reloader=False)
