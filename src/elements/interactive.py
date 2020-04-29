import os
import logging
import json
from elements.element import PipelineElement
from registry import register_element
from artifact import get_artifact_directory
from shutil import copy2

class InteractiveScoreElement(PipelineElement):
    '''Final score element.'''

    # The name of this pipeline element.
    name = 'interactive_score'

    def __init__(self, *args, **kwargs):
        # get train hash
        self._train_hash = kwargs['train_hash']
        
        # get train symlinks folder
        self._train_link_folder = os.path.join(get_artifact_directory(), self._train_hash)
        
        # get train bin symlink
        self._train_bin = os.path.join(self._train_link_folder, 'BIN')
        
        # get train checkpoint symlink
        self._checkpoint_path = os.path.join(self._train_link_folder, 'checkpoint_best.pt')
        
        # get test parameters json
        if 'test_cfg_path' in kwargs:
            self._cfg_path = kwargs['test_cfg_path']
        else:
            self._cfg_path = None
    

    def _read_json_db(self, folder):
        logger = logging.getLogger(__name__)
        
        if not folder:
            json_path = os.path.join(os.getcwd(), 'test_parameters_default.json')
        else:
            json_path = os.path.join(folder, "test_parameters.json")

            # Checking if it should use other parameters or default
            if not os.path.isfile(json_path):
                logger.debug(f"{json_path} not found!")
                json_path = os.path.join(os.getcwd(), 'test_parameters_default.json')
                logger.debug(f"Using {json_path}")
        copy2(json_path, get_artifact_directory())

        # Reading preprocess json
        with open(json_path, 'r') as f:
            parameters_dict = json.load(f)
            logger.debug("Parameters read successfully!")
        
        return parameters_dict
        
        
    def _fairseq_interactive(self):
        data_src = os.path.join(get_artifact_directory(), 'BPE', 'test.gr')
        data_path = self._checkpoint_path
        
        parameters_dict = self._read_json_db(self._cfg_path)
        beam = parameters_dict[0]['--beam']
        
        file_basename_wout_ext = os.path.basename(os.path.splitext(data_src)[0])
        file_out_name = os.path.join(get_artifact_directory(), file_basename_wout_ext + '.out')
        
        # traduzir com o interactive
        os.system(f'fairseq-interactive {self._train_bin} --path {data_path} --beam {beam} --remove-bpe < {data_src} | tee {file_out_name}')
        
        return file_basename_wout_ext
    
    
    def _fairseq_score(self, file_name):
        data_ref = os.path.join(get_artifact_directory(), "Preprocessed", "test.gi")
        file_out_name = os.path.join(get_artifact_directory(), f'{file_name}.out')
        file_hypo = os.path.join(get_artifact_directory(), f'{file_name}.h')
        # pegar as traduções
        os.system(f'grep ^H {file_out_name} | cut -f3- > {file_hypo}')

        # calcular o BLEU
        os.system(f'fairseq-score --sys {file_hypo} --ref {data_ref}')  


    def process(self, data=None):
        self._fairseq_score(self._fairseq_interactive())

register_element(InteractiveScoreElement)