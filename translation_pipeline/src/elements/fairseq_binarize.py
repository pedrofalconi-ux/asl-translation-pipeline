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
    dont_use_cache = True
    version = 2

    def __init__(self, *args, **kwargs):
        super().__init__(__file__, *args, **kwargs)

        # get artifact directory
        self._folder = get_artifact_directory()

        # create bin folder
        self._dest_dir = os.path.join(self._folder, 'BIN')
        os.makedirs(self._dest_dir, exist_ok=True)

        self._source_path = os.path.join(self._folder, 'BPE')
        self._train_pref = os.path.join(self._source_path, 'train')
        self._valid_pref = os.path.join(self._source_path, 'valid')


    def process(self, data=None):
        _, _, bin_files = next(os.walk(self._dest_dir))

        if bin_files:
            logger.warning('There are already files in the BIN folder. Skipping step...')
            return

        fairseq_preprocess_cmd = f'fairseq-preprocess -s gr -t gi --trainpref "{self._train_pref}" --validpref "{self._valid_pref}" --destdir "{self._dest_dir}"'
        logger.debug(f'Running: {fairseq_preprocess_cmd}')

        if os.system(fairseq_preprocess_cmd):
            raise Exception('Error running fairseq-preprocess')


# Add element to the registry.
register_element(BinarizeElement)
