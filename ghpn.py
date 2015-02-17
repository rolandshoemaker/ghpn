import github
from github.GithubException import GithubException

import json, datetime, os
from time import sleep
import dateutil.parser
from tabulate import tabulate
import humanize

VERSION = "0.0.1"

def date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
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
	def __init__(self, username=None, name=None, user_since=None, last_active=None, followers=None, following=None, repos=None):
		self.username = username
		self.name = name
		self.user_since = user_since
		self.last_active = last_active
		self.followers = followers
		self.following = following
		self.repos = repos

	@staticmethod
	def from_github(username):
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
						repo.total_commits = sum(t.total for t in commits)
						break
					tries += 1
					if tries > 5:
						break
				except TypeError:
					break

			ro_repos.append(repo)
		return GHProfile(username=username, name=ro.name, user_since=ro.created_at, last_active=ro.updated_at, followers=ro.followers, following=ro.following, repos=ro_repos)

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
			return GHProfile(username=profile["username"], user_since=dateutil.parser.parse(profile["user_since"]), last_active=dateutil.parser.parse(profile["last_active"]), followers=profile["followers"], following=profile["following"], name=profile["name"], repos=repos)

	def to_file(self, filename):
		with open(filename, "w") as f:
			profile = {
				"username": self.username,
				"name": self.name,
				"user_since": self.user_since,
				"last_active": self.last_active,
				"followers": self.followers,
				"following": self.following,
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
		ages = [datetime.datetime.now()-r.created_at for r in self.repos]
		return sum(ages, datetime.timedelta(0))/len(ages)

	def get_repo_age_range(self):
		oldest = max([(r.name,  datetime.datetime.now()-r.created_at) for r in self.repos], key=lambda x: x[1])
		newest = min([(r.name, datetime.datetime.now()-r.created_at) for r in self.repos], key=lambda x: x[1])
		return (oldest[0], oldest[1]), (newest[0], newest[1])

	def get_stars(self):
		stars = [r.stars for r in self.repos if r.stars > 0]
		return sum(stars), len(stars)

	def get_forkers(self):
		forkers = [f.forks for f in self.repos if f.forks > 0]
		return sum(forkers), len(forkers)

	def get_active_repos(self):
		repos = [[r.name, r.language, r.last_commit[:8], r.total_commits, r.last_updated, r.created_at] for r in self.repos]
		repos.sort(key=lambda x: x[4], reverse=True)
		for r in repos:
			r[4] = humanize.naturaltime(r[4])
			r[5] = humanize.naturaltime(r[5])
		return repos

	def get_inactive_repos(self):
		six_months_ago = datetime.datetime.now()-datetime.timedelta(weeks=4*6)
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

class GHProfileStats(object):
	def __init__(
		self,
		username=None,
		name=None,
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
		num_inactive_repos=None
	):
		self.username = username
		self.name = name
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

	# @staticmethod
	# def new(username):
		# if username in chache:
		#	return GHProfileStats.from_cache(username)
		# else:
		# return GHProfileStats.from_profile(GHProfile.from_github(username))

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
			num_inactive_repos=len(profile.get_inactive_repos())
		)

	def print_header(self):
		print("REPORT FOR: %s\n" % (self.name))
		print_section_header("User info")
		print("    Github username: %s" % (self.username))
		print("    User since: %s [%s]" % (self.user_since.strftime("%d-%m-%Y"), humanize.naturaltime(datetime.datetime.now()-self.user_since)))
		print("    Last active: %s" % (humanize.naturaltime(self.last_active)))
		print("    Followers: %d [following %d]" % (self.followers, self.following))
		print("    Github footprint: %s [%s minus forks]" % (humanize.naturalsize(self.footprint), humanize.naturalsize(self.footprint_minus_forks)))
		print()
		print_section_header("Repositories")
		print("    Repos: %s [%d forks, %d inactive for >6 months] " % (self.repo_num, self.forked_repo_num, self.num_inactive_repos))
		print("    Stars: %d [over %d repos]" % (self.stars[0], self.stars[1]))
		print("    Forkers: %d [over %d repos]" % (self.forkers[0], self.forkers[1]))
		print("    Oldest repo: %s [%s]" % (self.oldest_repo[0], humanize.naturaltime(self.oldest_repo[1]).replace("ago", "old")))
		print("    Newest repo: %s [%s]" % (self.newest_repo[0], humanize.naturaltime(self.newest_repo[1]).replace("ago", "old")))
		print("    Average repo age: %s" % (humanize.naturaltime(self.avg_repo_age).replace("ago", "old")))
		print("    Languages used: %s" % (len(self.langs)))

	def print_lang_breakdown(self):
		print_section_header("Language breakdown")
		table = [(l[0], l[1], humanize.naturalsize(l[2], gnu=True), int(l[3]/4)*"|", "{:3.2f}%".format(l[3])) for l in self.langs]
		for t in tabulate(table, tablefmt="simple", headers=["", "times used", "footprint", " "*25, ""], stralign="right").split("\n"):
			print("    %s" % (t))

	def print_active_repos(self):
		print_section_header("Recently active repos")
		for t in tabulate(self.active_repos, tablefmt="simple", headers=["", "language", "last commit", "total commits", "last updated", "created"]).split("\n"):
			print("    %s" % (t))

	def print_inactive_repos(self):
		print_section_header("Inactive repos")
		for t in tabulate(self.inactive_repos, tablefmt="simple", headers=["", "language", "last commit", "total commits", "last updated", "created"]).split("\n"):
			print("    %s" % (t))

	def print_popular_repos(self):
		print_section_header("Popular repos")
		for t in tabulate(self.popular_repos, tablefmt="simple", headers=["", "stars", "forkers", "total commits", "last updated"]).split("\n"):
			print("    %s" % (t))

	def print_issue_breakdown(self):
		pass

gh = github.Github(os.environ["GHPN_USER"], os.environ["GHPN_PASS"])
# GHProfile.from_github("rolandshoemaker").to_file("rolandshoemaker.json")
# roland = GHProfile.from_github("rolandshoemaker")
roland = GHProfile.from_file("rolandshoemaker.json")

stats = GHProfileStats.from_ghprofile(roland)

print_logo()
print()
stats.print_header()
print()
stats.print_lang_breakdown()
print()
stats.print_popular_repos()
print()
stats.print_active_repos()
print()
stats.print_inactive_repos()
print()
