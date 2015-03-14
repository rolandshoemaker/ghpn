import zlib, logging, multiprocessing

LOG_FILE_NAME = "ghpn-reigns.log"

def compress(stuff):
	return zlib.compress(bytes(stuff.encode("utf-8")))

def decompress(stuff):
	return zlib.decompress(stuff).decode("utf-8")

def get_logger(logger_name=None, log_level="info"):
	if multiprocessing.current_process().name == "MainProcess":
		if not logger_name:
			# something bad
			pass
		logger = logging.getLogger(logger_name)
	else:
		logger = multiprocessing.get_logger()
	if log_level == "debug":
		logger.setLevel(logging.DEBUG)
	elif log_level == "info":
		logger.setLevel(logging.INFO)
	elif log_level == "warn":
		logger.setLevel(logging.WARN)
	elif log_level == "error":
		logger.setLevel(logging.ERROR)
	elif log_level == "critical":
		logger.setLevel(logging.CRITICAL)

	fh = logging.FileHandler(LOG_FILE_NAME)
	formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
	fh.setFormatter(formatter)
	logger.addHandler(fh)

	return logger
