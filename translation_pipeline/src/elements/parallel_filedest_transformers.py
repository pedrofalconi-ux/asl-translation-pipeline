import json
import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element


class ParallelFileDestTransformersElement(PipelineElement):
    """Writes out GR and GI files."""

    name = "parallel_filedest_transformers"
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._json_path = kwargs["json_path"]
            self._complete_gr_path = os.path.join(
                get_artifact_directory(), self._json_path
            )
            os.makedirs(os.path.dirname(self._complete_gr_path), exist_ok=True)
        except KeyError:
            raise ValueError("`csvdest` requires a `json_path` parameter.")

    def process(self, data):
        with open(self._complete_gr_path, "w") as self._json_fd:
            for row in data:
                json.dump(row, self._json_fd, ensure_ascii=False)
                self._json_fd.write("\n")


# Add element to the registry.
register_element(ParallelFileDestTransformersElement)
