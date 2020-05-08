import glob
import logging
import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

logger = logging.getLogger(__name__)

class BinarizeElement(PipelineElement):
    '''fairseq-binarize step.'''
    name = 'binarize'

    _folder = None
    _dest_dir = None
    _prep_path = None
    _train_pref = None
    _valid_pref = None

    def __init__(self, *args, **kwargs):
        super().__init__(__file__, *args, **kwargs)

        # get artifact directory
        self._folder = get_artifact_directory()

        # create bin folder
        self._dest_dir = os.path.join(self._folder, 'BIN')
        os.makedirs(self._dest_dir, exist_ok=True)

        self._prep_path = os.path.join(self._folder, 'Preprocessed')
        self._train_pref = os.path.join(self._prep_path, 'train')
        self._valid_pref = os.path.join(self._prep_path, 'valid')


    def process(self, data=None):
        _, _, bin_files = next(os.walk(self._dest_dir))

        if bin_files:
            logger.warning('There are already files in the BIN folder. Skipping step...')
            return

        fairseq_preprocess_cmd = f'fairseq-preprocess -s gr -t gi --trainpref {self._train_pref} --validpref {self._valid_pref} --destdir {self._dest_dir}'
        logger.debug(f'Running: {fairseq_preprocess_cmd}')
        os.system(fairseq_preprocess_cmd)


# Add element to the registry.
register_element(BinarizeElement)
