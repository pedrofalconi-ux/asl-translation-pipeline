import json
import os
from shutil import copy2
from elements.element import PipelineElement
from registry import register_element
from artifact import get_artifact_directory
import logging


class TrainElement(PipelineElement):
    """ Train Fairseq Step
        Cria a pasta de checkpoint e executa o fairseq train com os parâmetros de treino.
    """
    name = "Train"
    

    def __init__(self, *args, **kwargs):
        super().__init__(args, *kwargs)
        self._train_folder_path = get_artifact_directory()

        # train_parameters_path is optional. It should be the path to an alternative 'train_parameters.json'.
        if 'train_parameters_path' in kwargs:
            self._train_parameters_path = kwargs['train_parameters_path']
        else:
            self._train_parameters_path = None


    def _read_json_db(self, folder, process):
        """Reads the train configuration file.
           Returns the path to it and the content(parameters).
        """
        logger = logging.getLogger(__name__)
        
        # Checking if it should use the default folder
        if not folder:
            json_path = os.path.join(os.getcwd(), f'{process}_parameters_default.json')
        else:
            json_path = os.path.join(folder, f"{process}_parameters.json")
            
            # Checking if the file exists, if not, use the default folder
            if not os.path.isfile(json_path):
                logger.debug(f"{json_path} not found!")
                json_path = os.path.join(os.getcwd(), f'{process}_parameters_default.json')
                logger.debug(f"Using {json_path}")

        # Reading preprocess json
        with open(json_path, 'r') as f:
            parameters_dict = json.load(f)
            logger.debug("Parameters read successfully!")

        return parameters_dict, json_path


    def process(self, data=None):
        logger = logging.getLogger(__name__)

        # set BIN folder path
        train_BIN_path = os.path.join(self._train_folder_path, "BIN")

        # set checkpoints folder path
        checkpoints_results_folder = os.path.join(self._train_folder_path, "Checkpoints")
        os.makedirs(checkpoints_results_folder, exist_ok=True)

        # get train parameters and configuration json path, then copy into train folder
        parameters_dict, json_path = self._read_json_db(self._train_parameters_path, "train")
        copy2(json_path, os.path.join(self._train_folder_path, "train_parameters.json"))   

        # copy the dictionaries from BIN to the Checkpoints folder
        for lang in ['gr', 'gi']:
            copy2(os.path.join(train_BIN_path, f'dict.{lang}.txt') , os.path.join(checkpoints_results_folder, f"dict.{lang}.txt"))

        # set the parameters string for fairseq
        str_parameters = f"fairseq-train '{train_BIN_path}' --save-dir '{checkpoints_results_folder}' --tensorboard-logdir '{checkpoints_results_folder}'"

        # Adding train parameters
        for key, value in parameters_dict[0].items() :
            # Do not remove these spaces
            str_parameters += f' {key} {value}'

        # Run Fairseq training
        logger.debug("Running fairseq-train")
        os.system(str_parameters)


# Add element to the registry.
register_element(TrainElement)