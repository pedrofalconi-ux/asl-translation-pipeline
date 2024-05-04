import csv
import logging
from elements.element import PipelineElement
from registry import register_element
from utils import get_file_md5_hash, resolve_relative_path

logger = logging.getLogger(__name__)

class CsvSrcElement(PipelineElement):
    """Reads from a `.csv` file."""

    name = "csvsrc"
    dont_use_cache = True

    _fd = None
    _reader = None
    _path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "path" not in kwargs:
            raise ValueError("`csvsrc` requires a `path` parameter.")

        self._path = resolve_relative_path(kwargs["path"])

    def get_cache_key(self):
        # Cache key is the MD5 hash of the file itself. This way, even if the
        # path changes we can still get a cache hit if the file itself is the
        # same.
        return get_file_md5_hash(self._path)

    def process(self, data=[]):
        if data is None:
            data = []

        with open(self._path, "r", newline="") as fd:
            for row in csv.reader(fd):
                if row:
                    data.append(row[:2])

        logger.info(f'Found {len(data)} valid entries in corpus.')
        return data


# Add element to the registry.
register_element(CsvSrcElement)
