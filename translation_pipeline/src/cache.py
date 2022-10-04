import logging
import os
import pickle

logger = logging.getLogger(__name__)

BASE_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache")
os.makedirs(BASE_CACHE_DIR, exist_ok=True)


def read_from_cache(key):
    cache_file_path = os.path.join(BASE_CACHE_DIR, key)

    try:
        with open(cache_file_path, "rb") as cache_file:
            return pickle.loads(cache_file.read())
    except Exception as ex:
        logger.debug(f"Failed to read cache key `{key}`: {ex}")
        return None


def write_to_cache(key, data):
    cache_file_path = os.path.join(BASE_CACHE_DIR, key)

    try:
        with open(cache_file_path, "wb") as cache_file:
            pickle.dump(data, cache_file)
    except Exception as ex:
        logger.error(f"Failed to write to cache key `{key}`: {ex}")
