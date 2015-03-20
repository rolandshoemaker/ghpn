import zlib, datetime, time, json, humanize
from redis import StrictRedis

from libghpn import GHProfileStats
from common import compress, decompress, get_logger

from github3 import GitHubError

STATS_CACHE_LENGTH = 5400

cache = StrictRedis(host="localhost", db=0)
logger = get_logger(logger_name="ghpn-redis-worker")

def run():
    logger.info("redis worker started")
    while True:
        username, token, user_id = cache.blpop("ghpn-work")[1].decode("utf-8").split(" ")
        if not cache.get("ghpn-cooldown:%s" % (username)):
            ghps = GHProfileStats(token=token)
            cache.set("ghpn-working:"+username, 1)
            DEBUG = {"username": username, "start_rl": ghps._debug_request_counter(), "start_t": time.time()}
            try:
                profile = ghps.get(username, json_errors=True)
                DEBUG["request_t"] = time.time()-DEBUG["start_t"]
                DEBUG["num_requests"] = ghps._debug_request_counter()-DEBUG["start_rl"]
            except GitHubError:
                if ghps._debug_remaining_requests()["resources"]["core"]["remaining"] == 0:
                    expiration = int((datetime.datetime.utcfromtimestamp(ghps._debug_remaining_requests()["resources"]["core"]["reset"])-datetime.datetime.utcnow()).total_seconds())
                    cache.setex("ghpn-cooldown:%s" % (user_id), expiration, ghps._debug_remaining_requests()["resources"]["core"]["reset"])
                    logger.info("github rate limit hit for %s, set cooldown! reset in %s." % (username, humanize.naturaldelta(expiration)))
                    # cache.rpush("ghpn-work", username)
                    # clear ghpn-work list so we dont randomly process old users in the queue when rate limit resets.
                else:
                    logger.error("error man hmm")
                cache.delete("ghpn-working:%s" % (username))
                continue
            
            if not isinstance(profile, GHProfileStats):
                expire = 60
                compressed_profile = compress(json.dumps(profile))
                logger.warn("processing error|req_userid=%d|username=%s|took=%.4f|requests=%d|rps=%.2f|error=%s" % (user_id, username, DEBUG["request_t"], DEBUG["num_requests"], DEBUG["num_requests"]/DEBUG["request_t"], profile["error"]))
            else:
                expire = STATS_CACHE_LENGTH
                compressed_profile = compress(profile.to_json())
                logger.info("processed user|req_userid=%d|username=%s|took=%.4f|requests=%d|rps=%.2f" % (user_id, username, DEBUG["request_t"], DEBUG["num_requests"], DEBUG["num_requests"]/DEBUG["request_t"]))
            cache.setex("ghpn:%s" % (username), expire, compressed_profile)
            cache.delete("ghpn-working:%s" % (username))

if __name__ == "__main__":
    run()
