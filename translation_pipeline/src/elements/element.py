class PipelineElement:
    """Base class for pipeline elements."""

    # The name of this pipeline element.
    name = "base-element"

    # Disable caching for the output of this element.
    dont_use_cache = False

    # Element version. Useful for invalidating cache.
    version = 1

    # Force element to pull from a specified cache key. Tucked away without
    # proper documentation since I don't want this being commonly used.
    _force_cache_key = None

    def __init__(self, *args, **kwargs):
        """Generic pipeline element constructor."""
        self._force_cache_key = kwargs.get("_force_cache_key")

    def __del__(self):
        pass

    def process(self, data):
        """The actual processing step. Receives the output from the previous
        element in `data` and returns the processed data for the next element.
        """
        raise NotImplementedError
