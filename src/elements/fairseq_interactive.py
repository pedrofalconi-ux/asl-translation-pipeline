import json
import logging
import os
from shutil import copy2

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

logger = logging.getLogger(__name__)

class InteractiveScoreElement(PipelineElement):
    '''Final score element.'''
    name = 'interactive_score'
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(__file__, *args, **kwargs)

        # get train hash
        self._train_hash = kwargs['train_hash']

        # get train symlinks folder
        self._train_link_folder = os.path.join(get_artifact_directory(), self._train_hash)

        # get train bin symlink
        self._train_bin = os.path.join(self._train_link_folder, 'BIN')

        # get train checkpoint symlink
        self._checkpoint_path = os.path.join(self._train_link_folder, 'checkpoint_best.pt')

        # get test parameters json
        self._cfg_path = kwargs['parameters']


    def _read_parameters_json(self, json_path):
        '''Reads the train configuration file.'''
        with open(json_path, 'r') as json_file:
            parameters_dict = json.load(json_file)
            logger.info(f'Using test parameters: {parameters_dict}')

        return parameters_dict


    def _fairseq_interactive(self):
        data_src = os.path.join(get_artifact_directory(), 'BPE', 'test.gr')
        data_path = self._checkpoint_path

        file_basename_wout_ext = os.path.basename(os.path.splitext(data_src)[0])
        file_out_name = os.path.join(get_artifact_directory(), file_basename_wout_ext + '.out')

        parameters_dict = self._read_parameters_json(self._cfg_path)
        str_parameters = ''
        for key, value in parameters_dict[0].items():
            str_parameters += f' {key} {value}'

        # traduzir com o interactive
        os.system(f'fairseq-interactive {self._train_bin} --path {data_path} {str_parameters} --remove-bpe < {data_src} | tee {file_out_name}')

        return file_basename_wout_ext


    def _fairseq_score(self, file_name):
        data_ref = os.path.join(get_artifact_directory(), 'Preprocessed', 'test.gi')
        file_out_name = os.path.join(get_artifact_directory(), f'{file_name}.out')
        file_hypo = os.path.join(get_artifact_directory(), f'{file_name}.h')

        # pegar as traduções
        os.system(f'grep ^H {file_out_name} | cut -f3- > {file_hypo}')

        # calcular o BLEU
        os.system(f'fairseq-score --sys {file_hypo} --ref {data_ref}')


    def process(self, data=None):
        self._fairseq_score(self._fairseq_interactive())


register_element(InteractiveScoreElement)
