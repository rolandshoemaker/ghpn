import github
from github.GithubException import GithubException

import json, datetime, os
import time
import dateutil.parser
from tabulate import tabulate
import humanize

VERSION = "0.0.1"

def date_handler(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, datetime.timedelta):
    	return obj.total_seconds()
    else:
        raise TypeError("Unserializable object {} of type {}".format(obj, type(obj)))

def print_logo():
	print("#       __                         ")
	print("#      /\ \                        ")
	print("#    __\ \ \___   _____     ___    ")
	print("#  /'_ `\ \  _ `\/\ '__`\ /' _ `\  ")
	print("# /\ \_\ \ \ \ \ \ \ \/\ \/\ \/\ \ ")
	print("# \ \____ \ \_\ \_\ \ ,__/\ \_\ \_\\")
	print("#  \/____\ \/_/\/_/\ \ \/  \/_/\/_/")
	print("#    /\____/        \ \_\          ")
	print("#    \_/__/          \/_/          ")
	print("#")
	print("# github parents night v%s" % (VERSION))

def print_section_header(header):
	h_len = "#"*(len(header)+4)
	print("%s\n# %s #\n%s\n" % (h_len, header, h_len))

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
	def __init__(self, username=None, name=None, user_since=None, last_active=None, followers=None, following=None, repos=None, location=None):
		self.username = username
		self.name = name
		self.user_since = user_since
		self.last_active = last_active
		self.followers = followers
		self.following = following
		self.repos = repos
		self.location = location

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

		return GHProfile(
			username=username,
			name=ro.name,
			user_since=ro.created_at,
			last_active=ro.updated_at,
			followers=ro.followers,
			following=ro.following,
			repos=ro_repos,
			location=ro.location
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
				location=profile["location"]
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
		return sum(r.size for r in self.repos), sum(r.size for r in self.repos if not r.is_forkd)

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
		total_commits=None
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

	@staticmethod
	def get(username):
		if username in chache:
			return GHProfileStats.from_cache(username)
		else:
			return GHProfileStats.from_profile(GHProfile.from_github(username))

	@staticmethod
	def from_cache(username):
		pass

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
			forked_repo_num=len([r for r in roland.repos if r.is_forkd]),
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
			total_commits=profile.get_total_commits()
		)

	def print_header(self):
		print("REPORT FOR: %s\n" % (self.name or self.username))
		print_section_header("User info")
		print("    Github username: %s" % (self.username))
		if self.location:
			print ("    Location: %s" % (self.location))
		print("    User since: %s [%s]" % (self.user_since.strftime("%d-%m-%Y"), humanize.naturaltime(datetime.datetime.now()-self.user_since)))
		print("    Last active: %s" % (humanize.naturaltime(self.last_active)))
		print("    Followers: %d [following %d]" % (self.followers, self.following))
		if self.footprint > 0:
			print("    Github footprint: %s [%s minus forks]" % (humanize.naturalsize(self.footprint, gnu=True), humanize.naturalsize(self.footprint_minus_forks, gnu=True)))
		print()
		print_section_header("Repositories")
		if self.forked_repo_num > 0 or self.num_inactive_repos > 0:
			extra = []
			if self.forked_repo_num > 0:
				extra.append("%d forks" % (self.forked_repo_num))
			elif self.num_inactive_repos > 0:
				extra.append("%d inactive for >6 months" % (self.num_inactive_repos))
			extra_repo = " [%s]" % (", ".join(extra))
		else:
			extra_repo = ""
		print("    Repos: %s%s" % (self.repo_num, extra_repo))
		print("    Total commits: %d" % (self.total_commits))
		print("    Stars: %d [over %d repos]" % (self.stars[0], self.stars[1]))
		print("    Forkers: %d [over %d repos]" % (self.forkers[0], self.forkers[1]))
		if self.repo_num > 0:
			print("    Oldest repo: %s [%s]" % (self.oldest_repo[0], humanize.naturaltime(self.oldest_repo[1]).replace("ago", "old")))
			print("    Newest repo: %s [%s]" % (self.newest_repo[0], humanize.naturaltime(self.newest_repo[1]).replace("ago", "old")))
		if self.avg_repo_age:
			print("    Average repo age: %s" % (humanize.naturaltime(self.avg_repo_age).replace("ago", "old")))
		if len(self.langs) > 0:
			print("    Languages used: %s" % (len(self.langs)))

	def print_lang_breakdown(self):
		if len(self.langs) > 0:
			print_section_header("Language breakdown")
			table = [(l[0], humanize.naturalsize(l[2], gnu=True), l[1], int(l[3]/4)*"|", "{:3.2f}%".format(l[3])) for l in self.langs]
			for t in tabulate(table, tablefmt="simple", headers=["", "footprint", "times used", " "*25, ""], stralign="right").split("\n"):
				print("    %s" % (t))

	def print_active_repos(self):
		if len(self.active_repos) > 0:
			print_section_header("Recently active repositories")
			for t in tabulate(self.active_repos, tablefmt="simple", headers=["", "language", "last commit", "total commits", "last updated", "created"]).split("\n"):
				print("    %s" % (t))

	def print_inactive_repos(self):
		if len(self.inactive_repos) > 0:
			print_section_header("Inactive repositories")
			for t in tabulate(self.inactive_repos, tablefmt="simple", headers=["", "language", "last commit", "total commits", "last updated", "created"]).split("\n"):
				print("    %s" % (t))

	def print_popular_repos(self):
		if len(self.popular_repos) > 0:
			print_section_header("Popular repositories")
			for t in tabulate(self.popular_repos, tablefmt="simple", headers=["", "stars", "forkers", "total commits", "last updated"]).split("\n"):
				print("    %s" % (t))

gh = github.Github(os.environ["GHPN_USER"], os.environ["GHPN_PASS"])

# debug, debug, debug, benching?
# debug imports
import requests
from random import randrange
import sys
import zlib
ts = "https://api.github.com/user/"
test_users = ['skilygui', 'pajikos', 'maddychennupati', 'Priceless1024', 'TesterTestowy', 'polo04rail', 'ebujan', 'alzhao', 'danacn', 'hsiw9uvh5p8', 'b23a2d7e7a', 'kongko', 'jiangxinghe', 'ksvbka', 'irispanda50', 'zerjioang', 'umas63', 'lynnwalker1129', 'hargrel', 'vtsuei2', 'dannyhunter2', 'MonicaPH', 'kevindennill', 'lmm523', 'hmartens']
# while len(test_users) <=25:
# 	r = requests.get(ts+str(randrange(0, 10000901)))
# 	if r:
# 		print(r.json()["login"])
# 		test_users.append(r.json()["login"])

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

	print_logo()
	print()
	stats.print_header()
	print()
	if len(stats.langs) > 0:
		stats.print_lang_breakdown()
		print()
	if len(stats.popular_repos) > 0:
		stats.print_popular_repos()
		print()
	if len(stats.active_repos) > 0:
		stats.print_active_repos()
		print()
	if len(stats.inactive_repos) > 0:
		stats.print_inactive_repos()
		print()

	print_section_header("DEBUG")
	print("    requests took:        %.2fs" % (DEBUG_INFO["requests_took"]))
	print("    num requests made:    %d" % (DEBUG_INFO["num_requests_made"]))
	print("    stats size:           %s" % (humanize.naturalsize(DEBUG_INFO["profile_stats_size"])))
	print("    stats size (zlib'd):  %s [took %.4fs-ish]\n" % (humanize.naturalsize(DEBUG_INFO["profile_stats_gz_size"]), c_t))
def avg(l):
	return sum(l) / len(l)

print_section_header("RUN STATS")
print("  Average collection period:   %.2fs" % (avg([d["requests_took"] for d in debugs])))
print("  Average requests:            %.2d" % (avg([d["num_requests_made"] for d in debugs])))
print("  Average size:                %s" % (humanize.naturalsize(avg([d["profile_stats_size"] for d in debugs]))))
print("  Average size (zlib'd):       %s" % (humanize.naturalsize(avg([d["profile_stats_gz_size"] for d in debugs]))))

# roland = GHProfile.from_github("dannyhunter2")
# stats = GHProfileStats.from_ghprofile(roland)

# print_logo()
# print()
# stats.print_header()
# print()
# if len(stats.langs) > 0:
# 	stats.print_lang_breakdown()
# 	print()
# if len(stats.popular_repos) > 0:
# 	stats.print_popular_repos()
# 	print()
# if len(stats.active_repos) > 0:
# 	stats.print_active_repos()
# 	print()
# if len(stats.inactive_repos) > 0:
# 	stats.print_inactive_repos()
# 	print()
