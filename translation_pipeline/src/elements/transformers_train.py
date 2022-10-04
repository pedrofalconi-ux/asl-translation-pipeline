import json
import logging
import os
from shutil import copy2

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element
from utils import get_file_md5_hash, resolve_relative_path

logger = logging.getLogger(__name__)


class TransformersElement(PipelineElement):
    """Train Fairseq Step
    Cria a pasta de checkpoint e executa o fairseq train com os parâmetros de treino.
    """

    name = "transformers-trainer"
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(__file__, *args, **kwargs)

        self._artifact_folder_path = get_artifact_directory()
        try:
            self._train_parameters_path = resolve_relative_path(kwargs["parameters"])
        except KeyError:
            raise ValueError(f"`{self.name}` requires a `parameters` parameter.")

    def _read_parameters_json(self, json_file_path):
        """Reads the train configuration file."""
        with open(json_file_path, "r") as json_file:
            parameters_dict = json.load(json_file)
            logger.info(f"Using train parameters: {parameters_dict}")

        return parameters_dict

    def get_cache_key(self):
        """Generate a new artifact when hyperparams have been changed."""
        return get_file_md5_hash(self._train_parameters_path)

    def process(self, data=None):
        # Set up paths and folders.
        splits_folder = os.path.join(self._artifact_folder_path, "Preprocessed")
        checkpoint_folder = os.path.join(self._artifact_folder_path, "Checkpoints")
        parameters_dict = self._read_parameters_json(self._train_parameters_path)
        os.makedirs(checkpoint_folder, exist_ok=True)

        # Copy train parameters JSON to the artifact folder.
        copy2(self._train_parameters_path, self._artifact_folder_path)

        train_file_path = os.path.join(splits_folder, "train.json")
        valid_file_path = os.path.join(splits_folder, "valid.json")

        str_parameters = f"train --output_dir {checkpoint_folder} --train_file {train_file_path} --validation_file {valid_file_path}"
        for key, value in parameters_dict[0].items():
            str_parameters += f" {key} {value}"

        # Run Fairseq training
        logger.debug(f"Running: {str_parameters}")

        if os.system(str_parameters):
            raise Exception("Error running transformers training")


# Add element to the registry.
register_element(TransformersElement)
