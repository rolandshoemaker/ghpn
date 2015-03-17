def read_log(filename):
	with open(filename, "r") as f:
		lines = f.readlines()
	
	return [l.strip() for l in lines]

def only_success(log_lines):
	return [l for l in log_lines if "processed user" in l]

def only_errors(log_lines):
	return [l for l in log_lines if "processing error" in l]

def get_stats(line):
	unparsed_variables = {}
	for e in line.split("|")[1:]:
		e = e.split("=")
		unparsed_variables[e[0]] = e[1]
	return {
		"timestamp": " ".join(line.split(" ")[:2]), # should be a datetime prob...?
		"requests": int(unparsed_variables["requests"]),
		"took": int(unparsed_variables["took"]),
		"rps": float(unparsed_variables["rps"])
	}

def print_stats(log_lines):
	stats = {"entries": []}
	for entry in log_lines:
		stats["entries"].append(get_stats(entry))
	total_requests = sum([e["requests"] for e in stats["entries"]])
	avg_requests = sum([e["requests"] for e in stats["entries"]]) / len(stats["entries"])
	avg_took = sum([e["took"] for e in stats["entries"]]) / len(stats["entries"])
	avg_rps = sum([e["rps"] for e in stats["entries"]]) / len(stats["entries"])
	print("users processed: %d" % (len(stats["entries"])))
	print("total requests: %d" % (total_requests))
	print("    average requests: %d" % (avg_requests))
	print("    average request time: %.6fs" % (avg_took))
	print("    average rps: %.4f" % (avg_rps))

print_stats(only_success(read_log("ghpn-reigns.log")))
