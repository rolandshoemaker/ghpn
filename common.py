import zlib

def compress(stuff):
	return zlib.compress(bytes(stuff.encode("utf-8")))

def decompress(stuff):
	return zlib.decompress(stuff).decode("utf-8")