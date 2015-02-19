import github
from github.GithubException import GithubException

import json, datetime, os
import time
import dateutil.parser
from tabulate import tabulate
import humanize

gh = github.Github(os.environ["GHPN_USER"], os.environ["GHPN_PASS"])
VERSION = "0.0.5"

def date_handler(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, datetime.timedelta):
    	return obj.total_seconds()
    else:
        raise TypeError("Unserializable object {} of type {}".format(obj, type(obj)))

def logo_block(name=None):
	output = []
	output.append("#       __                         ")
	output.append("#      /\ \                        ")
	output.append("#    __\ \ \___   _____     ___    ")
	output.append("#  /'_ `\ \  _ `\/\ '__`\ /' _ `\  ")
	output.append("# /\ \_\ \ \ \ \ \ \ \/\ \/\ \/\ \ ")
	output.append("# \ \____ \ \_\ \_\ \ ,__/\ \_\ \_\\")
	output.append("#  \/____\ \/_/\/_/\ \ \/  \/_/\/_/")
	output.append("#    /\____/        \ \_\          ")
	output.append("#    \_/__/          \/_/          ")
	output.append("#")
	output.append("#   github parents night v%s" % (VERSION))
	if name:
		output += ["#", "# REPORT FOR: %s" % (name)]
	return "\n".join(output)

def section_header_block(header):
	h_len = "#"*(len(header)+4)
	return "%s\n# %s #\n%s\n" % (h_len, header, h_len)

def flatten_event_list(events):
	flat = {}
	# hacky hack if people have so many events
	# that they are all from one day...
	if (max(events, key=lambda x: x.created_at)-min(events, key=lambda x: x.created_at)).days <= 0:
		time_split = "%d-%m-%Y %H"
	else:
		time_split = "%d-%m-%Y"
	for e in events:
		d_key = e.created_at.strftime(time_split)
		if flat.get(d_key, None):
			flat[d_key].append(e)
		else:
			flat[d_key] = []
			flat[d_key].append(e)
	flatr = [[k, len(v)] for k, v in flat.items()]
	flatr.sort(key=lambda x: dateutil.parser.parse(x[0]))
	return flatr

def reduce_events(events, cutoff=25):
	pushes = []
	creates = []
	forks = []
	issues = []

	for e in events:
		if e.type == "PushEvent":
			pushes.append(e)
		elif e.type == "CreateEvent":
			creates.append(e)
		elif e.type == "ForkEvent":
			forks.append(e)
		elif e.type == "IssueCommentEvent" or e.type == "IssuesEvent":
			issues.append(e)

	if len(pushes) < cutoff:
		pushes = None
	else:
		pushes = flatten_event_list(pushes)

	if len(creates) < cutoff:
		creates = None
	else:
		creates = flatten_event_list(creates)

	if len(forks):
		forks = None
	else:
		forks = flatten_event_list(forks)

	if len(issues):
		issues = None
	else:
		issues = flatten_event_list(issues)

	return pushes, creates, forks, issues

class GHRepo(object):
	def __init__(
		self,
		name=None,
		is_forkd=None,
		total_commits=None,
		last_month_commits=None,
		stars=None,
		watchers=None,
		forks=None,
		language=None,
		languages=None,
		size=None,
		open_issues=None,
		last_updated=None,
		created_at=None,
		last_commit=None
	):
		self.name = name
		self.is_forkd = is_forkd
		self.total_commits = total_commits
		self.last_month_commits = last_month_commits
		self.stars = stars
		self.watchers = watchers
		self.forks = forks
		self.language = language
		self.languages = languages
		self.size = size
		self.open_issues = open_issues
		self.last_updated = last_updated
		self.created_at = created_at
		self.last_commit = last_commit

class GHProfile(object):
	def __init__(
		self,
		username=None,
		name=None,
		user_since=None,
		last_active=None,
		followers=None,
		following=None,
		repos=None,
		location=None,
		push_activity=None,
		fork_activity=None,
		create_activity=None,
		issue_activity=None
	):
		self.username = username
		self.name = name
		self.user_since = user_since
		self.last_active = last_active
		self.followers = followers
		self.following = following
		self.repos = repos
		self.location = location
		self.push_activity = push_activity
		self.fork_activity = fork_activity
		self.create_activity = create_activity
		self.issue_activity = issue_activity

	@staticmethod
	def from_github(username):
		# this is where ALL the requests come from (at least they should)
		ro = gh.get_user(username)
		ro_repo_uris = ro.get_repos()
		ro_repos = []

		for r in ro_repo_uris:
			try:
				last_commit = r.get_commits()[0].sha # prob better way!
			except GithubException:
				last_commit = ""
			repo = GHRepo(
				name=r.name,
			    is_forkd=r.fork,
				total_commits=0,
				last_month_commits=None,
				stars=r.stargazers_count,
				watchers=r.watchers_count, # WRONG
				forks=r.forks_count,
				language=r.language,
				languages=r.get_languages(), # bytes
				size=r.size*1000, # kb i think
				open_issues=r.open_issues_count,
				last_updated=r.updated_at,
				created_at=r.created_at,
				last_commit=last_commit
			)
			tries = 0
			while True:
				try:
					commits = r.get_stats_contributors()
					if commits:
						repo.total_commits = sum(t.total for t in commits if t.author.login == username)
						break
					tries += 1
					if tries > 5:
						break
				except TypeError:
					break

			ro_repos.append(repo)

		pushes, creates, forks, issues = reduce_events(ro.get_events())

		return GHProfile(
			username=username,
			name=ro.name,
			user_since=ro.created_at,
			last_active=ro.updated_at,
			followers=ro.followers,
			following=ro.following,
			repos=ro_repos,
			location=ro.location,
			push_activity=pushes,
			fork_activity=forks,
			create_activity=creates,
			issue_activity=issues
		)

	@staticmethod
	def from_file(filename):
		with open(filename, "r") as f:
			# should handle datetime re-serialization...? (last_updated, created_at)
			profile = json.load(f)
			repos = [GHRepo(
				name=r["name"],
			    is_forkd=r["is_forkd"],
				total_commits=r["total_commits"],
				last_month_commits=r["last_month_commits"],
				stars=r["stars"],
				watchers=r["watchers"],
				forks=r["forks"],
				language=r["language"],
				languages=r["languages"],
				size=r["size"],
				open_issues=r["open_issues"],
				last_updated=dateutil.parser.parse(r["last_updated"]),
				created_at=dateutil.parser.parse(r["created_at"]),
				last_commit=r["last_commit"]
			) for r in profile["repos"]]

			return GHProfile(
				username=profile["username"],
				user_since=dateutil.parser.parse(profile["user_since"]),
				last_active=dateutil.parser.parse(profile["last_active"]),
				followers=profile["followers"],
				following=profile["following"],
				name=profile["name"],
				repos=repos,
				location=profile["location"],
				push_activity=profile["push_activity"],
				fork_activity=profile["fork_activity"],
				create_activity=profile["create_activity"],
				issue_activity=profile["issue_activity"]
			)

	def to_file(self, filename):
		with open(filename, "w") as f:
			profile = {
				"username": self.username,
				"name": self.name,
				"user_since": self.user_since,
				"last_active": self.last_active,
				"followers": self.followers,
				"following": self.following,
				"location": self.location,
				"push_activity": self.push_activity,
				"fork_activity": self.fork_activity,
				"create_activity": self.create_activity,
				"issue_activity": self.issue_activity,
				"repos": [r.__dict__ for r in self.repos]
			}
			json.dump(profile, f, default=date_handler)

	def get_lang_stats(self):
		langs = {}
		for r in self.repos:
			for k, v in r.languages.items():
				if not langs.get(k): langs[k] = {"bytes": 0, "used": 0}
				langs[k]["bytes"] += v
				langs[k]["used"] += 1
		lang_count = sum(langs[lang]["used"] for lang in langs)
		langs = [(lang, langs[lang]["used"], langs[lang]["bytes"], (langs[lang]["used"]/lang_count)*100) for lang in langs]
		langs.sort(key=lambda x: x[1], reverse=True)
		return langs

	def get_repos_footprint(self):
		return sum(r.size for r in self.repos), sum(r.size for r in self.repos if not r.is_forkd) or None

	def get_avg_repo_age(self):
		if len(self.repos) > 0:
			ages = [datetime.datetime.now()-r.created_at for r in self.repos]
			return sum(ages, datetime.timedelta(0))/len(ages)

	def get_repo_age_range(self):
		if len(self.repos) > 0:
			oldest = max([(r.name,  datetime.datetime.now()-r.created_at) for r in self.repos], key=lambda x: x[1])
			newest = min([(r.name, datetime.datetime.now()-r.created_at) for r in self.repos], key=lambda x: x[1])
			return (oldest[0], oldest[1]), (newest[0], newest[1])
		else:
			return None, None

	def get_stars(self):
		stars = [r.stars for r in self.repos if r.stars > 0]
		return sum(stars), len(stars)

	def get_forkers(self):
		forkers = [f.forks for f in self.repos if f.forks > 0]
		return sum(forkers), len(forkers)

	def get_active_repos(self):
		two_months_ago = datetime.datetime.now()-datetime.timedelta(weeks=3*2)
		repos = [[r.name, r.language, r.last_commit[:8], r.total_commits, r.last_updated, r.created_at] for r in self.repos if r.last_updated > two_months_ago]
		repos.sort(key=lambda x: x[4], reverse=True)
		for r in repos:
			r[4] = humanize.naturaltime(r[4])
			r[5] = humanize.naturaltime(r[5])
		return repos

	def get_inactive_repos(self):
		six_months_ago = datetime.datetime.now()-datetime.timedelta(weeks=3*6)
		repos = [[r.name, r.language, r.last_commit[:8], r.total_commits, r.last_updated, r.created_at] for r in self.repos if r.last_updated < six_months_ago]
		repos.sort(key=lambda x: x[4])
		for r in repos:
			r[4] = humanize.naturaltime(r[4])
			r[5] = humanize.naturaltime(r[5])
		return repos

	def get_popular_repos(self, fork_sort=False):
		repos = [(r.name, r.stars, r.forks, r.total_commits, humanize.naturaltime(r.last_updated)) for r in self.repos if r.stars > 0 or r.forks > 0]
		if not fork_sort:
			sorter=1
		else:
			sorter=2
		repos.sort(key=lambda x: x[sorter], reverse=True)
		return repos

	def get_total_commits(self):
		return sum(r.total_commits for r in self.repos if not r.is_forkd)

class GHProfileStats(object):
	def __init__(
		self,
		username=None,
		name=None,
		location=None,
		user_since=None,
		last_active=None,
		repo_num=None,
		forked_repo_num=None,
		langs=None,
		footprint=None,
		footprint_minus_forks=None,
		stars=None,
		forkers=None,
		followers=None,
		following=None,
		oldest_repo=None,
		newest_repo=None, 
		avg_repo_age=None,
		popular_repos=None,
		active_repos=None,
		inactive_repos=None,
		num_inactive_repos=None,
		total_commits=None,
		push_activity=None,
		fork_activity=None,
		create_activity=None,
		issue_activity=None
	):
		self.username = username
		self.name = name
		self.location = location
		self.user_since = user_since
		self.last_active = last_active
		self.repo_num = repo_num
		self.forked_repo_num = forked_repo_num
		self.langs = langs
		self.footprint = footprint
		self.footprint_minus_forks = footprint_minus_forks
		self.stars = stars
		self.forkers = forkers
		self.followers = followers
		self.following = following
		self.oldest_repo = oldest_repo
		self.newest_repo = newest_repo 
		self.avg_repo_age = avg_repo_age
		self.popular_repos = popular_repos
		self.active_repos = active_repos
		self.inactive_repos = inactive_repos
		self.num_inactive_repos = num_inactive_repos
		self.total_commits = total_commits
		self.push_activity = push_activity
		self.fork_activity = fork_activity
		self.create_activity = create_activity
		self.issue_activity = issue_activity

	@staticmethod
	def get(username):
		return GHProfileStats.from_ghprofile(GHProfile.from_github(username))

	@staticmethod
	def from_ghprofile(profile, repo_limit=10):
		footprint, footprint_minus_forks = profile.get_repos_footprint()
		oldest, newest = profile.get_repo_age_range()
		return GHProfileStats(
			username=profile.username,
			name=profile.name,
			location=profile.location,
			user_since=profile.user_since,
			last_active=profile.last_active,
			repo_num=len(profile.repos),
			forked_repo_num=len([r for r in profile.repos if r.is_forkd]),
			langs=profile.get_lang_stats(),
			footprint=footprint,
			footprint_minus_forks=footprint_minus_forks,
			stars=profile.get_stars(),
			forkers=profile.get_forkers(),
			followers=profile.followers,
			following=profile.following,
			oldest_repo=oldest,
			newest_repo=newest, 
			avg_repo_age=profile.get_avg_repo_age(),
			popular_repos=profile.get_popular_repos()[:repo_limit],
			active_repos=profile.get_active_repos()[:repo_limit],
			inactive_repos=profile.get_inactive_repos()[:repo_limit],
			num_inactive_repos=len(profile.get_inactive_repos()),
			total_commits=profile.get_total_commits(),
			push_activity=profile.push_activity,
			fork_activity=profile.fork_activity,
			create_activity=profile.create_activity,
			issue_activity=profile.issue_activity
		)

	@staticmethod
	def from_json(stats_json):
		stats_json = json.loads(stats_json)

		oldest, newest = stats_json["oldest_repo"], stats_json["newest_repo"]
		oldest[1] = datetime.timedelta(seconds=oldest[1])
		newest[1] = datetime.timedelta(seconds=newest[1])

		return GHProfileStats(
			username=stats_json["username"],
			name=stats_json["name"],
			location=stats_json["location"],
			user_since=dateutil.parser.parse(stats_json["user_since"]),
			last_active=dateutil.parser.parse(stats_json["last_active"]),
			repo_num=stats_json["repo_num"],
			forked_repo_num=stats_json["forked_repo_num"],
			langs=stats_json["langs"],
			footprint=stats_json["footprint"],
			footprint_minus_forks=stats_json["footprint_minus_forks"],
			stars=stats_json["stars"],
			forkers=stats_json["forkers"],
			followers=stats_json["followers"],
			following=stats_json["following"],
			oldest_repo=oldest,
			newest_repo=newest, 
			avg_repo_age=datetime.timedelta(seconds=stats_json["avg_repo_age"]),
			popular_repos=stats_json["popular_repos"],
			active_repos=stats_json["active_repos"],
			inactive_repos=stats_json["inactive_repos"],
			num_inactive_repos=stats_json["num_inactive_repos"],
			total_commits=stats_json["total_commits"],
			push_activity=stats_json["push_activity"],
			fork_activity=stats_json["fork_activity"],
			create_activity=stats_json["create_activity"],
			issue_activity=stats_json["issue_activity"]
		)

	def to_json(self):
		return json.dumps(self.__dict__, default=date_handler)

	def user_block(self):
		output = []
		output.append(section_header_block("User info"))
		output.append("    Github username: %s" % (self.username))
		if self.name:
			output.append("    Name: %s" % (self.name))
		if self.location:
			output.append("    Location: %s" % (self.location))
		output.append("    User since: %s [%s]" % (self.user_since.strftime("%d-%m-%Y"), humanize.naturaltime(datetime.datetime.now()-self.user_since)))
		output.append("    Last active: %s" % (humanize.naturaltime(self.last_active)))
		output.append("    Followers: %d [following %d]" % (self.followers, self.following))
		if self.footprint > 0:
			if self.footprint_minus_forks:
				extra = " [%s minus forks]" % humanize.naturalsize(self.footprint_minus_forks, gnu=True)
			else:
				extra = ""
			output.append("    Github footprint: %s%s" % (humanize.naturalsize(self.footprint, gnu=True), extra))
		return "\n".join(output)

	def repo_block(self):
		output = []
		output.append(section_header_block("Repositories"))
		if self.forked_repo_num > 0 or self.num_inactive_repos > 0:
			extra = []
			if self.forked_repo_num > 0:
				extra.append("%d forks" % (self.forked_repo_num))
			elif self.num_inactive_repos > 0:
				extra.append("%d inactive for >6 months" % (self.num_inactive_repos))
			extra_repo = " [%s]" % (", ".join(extra))
		else:
			extra_repo = ""
		output.append("    Repos: %s%s" % (self.repo_num, extra_repo))
		output.append("    Total commits: %d" % (self.total_commits))
		output.append("    Stars: %d [over %d repos]" % (self.stars[0], self.stars[1]))
		output.append("    Forkers: %d [over %d repos]" % (self.forkers[0], self.forkers[1]))
		if self.repo_num > 0:
			output.append("    Oldest repo: %s [%s]" % (self.oldest_repo[0], humanize.naturaltime(self.oldest_repo[1]).replace("ago", "old")))
			output.append("    Newest repo: %s [%s]" % (self.newest_repo[0], humanize.naturaltime(self.newest_repo[1]).replace("ago", "old")))
		if self.avg_repo_age:
			output.append("    Average repo age: %s" % (humanize.naturaltime(self.avg_repo_age).replace("ago", "old")))
		if len(self.langs) > 0:
			output.append("    Languages used: %s" % (len(self.langs)))
		return "\n".join(output)

	def lang_breakdown_block(self):
		output = []
		if len(self.langs) > 0:
			output.append(section_header_block("Language breakdown"))
			table = [(l[0], humanize.naturalsize(l[2], gnu=True), l[1], int(l[3]/4)*"|", "{:3.2f}%".format(l[3])) for l in self.langs]
			for t in tabulate(table, tablefmt="simple", headers=["", "footprint", "times used", " "*25, ""], stralign="right").split("\n"):
				output.append("    %s" % (t))
			return "\n".join(output)

	def active_repos_block(self):
		output = []
		if len(self.active_repos) > 0:
			output.append(section_header_block("Recently active repositories"))
			for t in tabulate(self.active_repos, tablefmt="simple", headers=["", "language", "last commit", "total commits", "last updated", "created"]).split("\n"):
				output.append("    %s" % (t))
			return "\n".join(output)

	def inactive_repos_block(self):
		output = []
		if len(self.inactive_repos) > 0:
			output.append(section_header_block("Inactive repositories"))
			for t in tabulate(self.inactive_repos, tablefmt="simple", headers=["", "language", "last commit", "total commits", "last updated", "created"]).split("\n"):
				output.append("    %s" % (t))
			return "\n".join(output)

	def popular_repos_block(self):
		output = []
		if len(self.popular_repos) > 0:
			output.append(section_header_block("Popular repositories"))
			for t in tabulate(self.popular_repos, tablefmt="simple", headers=["", "stars", "forkers", "total commits", "last updated"]).split("\n"):
				output.append("    %s" % (t))
			return "\n".join(output)

	@staticmethod
	def construct_event_graph_block(header, event_tuples, height=15):
		if event_tuples:
			output = []
			line_length = len(event_tuples)
			# if line_length < 10:
			#	modi = 15
			# elif line_length > 75:
			#	modi = 1
			# else:
			#	modi = 2
			modi = 2
			e_max = max(event_tuples, key=lambda x: x[1])[1]
			def trans(value, event_max=e_max, graph_max=height):
				return ((graph_max)*(value)/(event_max))

			output.append(section_header_block(header))
			table = ""
			for row in range(height, 0, -1):
				table += "        "
				for col in range(line_length):
					if trans(event_tuples[col][1]) > row:
						table += "#"*modi
					else:
						table += " "*modi
				table += "| "
				if row == height:
					table += "%d\n" % (e_max)
				elif row == 1:
					table += "%d\n" % (row)
				else:
					table += "\n"
			output.append(table+"        "+"-"*(modi*line_length)+"/")
			output.append(str("    {: <%d} {: >%d}" % ((modi*line_length/2)+4, (modi*line_length/2)+4)).format(event_tuples[0][0], event_tuples[-1][0]))
			return "\n".join(output)

	def get_all_blocks(self):
		name = self.name or self.username
		blocks = [
			logo_block(name=name),
			self.user_block(),
			self.repo_block(),
			self.lang_breakdown_block(),
			self.popular_repos_block(),
			self.construct_event_graph_block("Push chart", self.push_activity),
			self.active_repos_block(),
			self.inactive_repos_block(),
			self.construct_event_graph_block("New repository chart", self.create_activity),
			self.construct_event_graph_block("Issue comments chart", self.issue_activity),
			self.construct_event_graph_block("Fork chart", self.fork_activity)
		]
		return [b for b in blocks if b]

def testing():
	# debug, debug, debug, benching?
	# debug imports
	import requests
	from random import randrange
	import sys
	import zlib
	ts = "https://api.github.com/user/"
	test_users = [] # ['skilygui', 'pajikos', 'maddychennupati', 'Priceless1024', 'TesterTestowy', 'polo04rail', 'ebujan', 'alzhao', 'danacn', 'hsiw9uvh5p8', 'b23a2d7e7a', 'kongko', 'jiangxinghe', 'ksvbka', 'irispanda50', 'zerjioang', 'umas63', 'lynnwalker1129', 'hargrel', 'vtsuei2', 'dannyhunter2', 'MonicaPH', 'kevindennill', 'lmm523', 'hmartens']
	while len(test_users) <=25:
		r = requests.get(ts+str(randrange(200000, 10000901)))
		if r:
			print(r.json()["login"])
			test_users.append(r.json()["login"])
	print(test_users)

	debugs = []
	for tu in test_users:
		print(tu+"\n")
		start_t = time.time()
		start_l = gh.rate_limiting[0]

		roland = GHProfile.from_github(tu)
		# roland = GHProfile.from_github("rolandshoemaker")
		# GHProfile.from_github("rolandshoemaker").to_file("rolandshoemaker.json")
		# roland = GHProfile.from_file("rolandshoemaker.json")
		stats = GHProfileStats.from_ghprofile(roland)

		c_s = time.time()
		zlibd = sys.getsizeof(zlib.compress(bytes(json.dumps(stats.__dict__, default=date_handler).encode("utf-8"))))
		c_t = time.time()-c_s
		DEBUG_INFO = {
			"requests_took": time.time()-start_t,
			"num_requests_made": start_l-gh.rate_limiting[0],
			"profile_stats_size": sys.getsizeof(json.dumps(stats.__dict__, default=date_handler)),
			"profile_stats_gz_size": zlibd
		}
		debugs.append(DEBUG_INFO)

		section_header_block("DEBUG")
		print("    requests took:        %.2fs" % (DEBUG_INFO["requests_took"]))
		print("    num requests made:    %d" % (DEBUG_INFO["num_requests_made"]))
		print("    stats size:           %s" % (humanize.naturalsize(DEBUG_INFO["profile_stats_size"])))
		print("    stats size (zlib'd):  %s [took %.4fs-ish]\n" % (humanize.naturalsize(DEBUG_INFO["profile_stats_gz_size"]), c_t))

	def avg(l):
		return sum(l) / len(l)

	section_header_block("RUN STATS")
	print("  Average collection period:   %.2fs" % (avg([d["requests_took"] for d in debugs])))
	print("  Average requests:            %.2d" % (avg([d["num_requests_made"] for d in debugs])))
	print("  Average size:                %s" % (humanize.naturalsize(avg([d["profile_stats_size"] for d in debugs]))))
	print("  Average size (zlib'd):       %s" % (humanize.naturalsize(avg([d["profile_stats_gz_size"] for d in debugs]))))

def run():
	import sys
	roland = GHProfile.from_github(sys.argv[1])
	stats = GHProfileStats.from_ghprofile(roland)

	print("\n\n".join(stats.get_all_blocks()))

if __name__ == "__main__":
	run()
