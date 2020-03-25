import os
import logging
import glob
from elements.element import PipelineElement
from registry import register_element
from artifact import get_artifact_directory

class BinarizeElement(PipelineElement):
    """ Binarize Step """
    name = "binarize"
    _folder = None
    _dest_dir = None
    _prep_path = None
    _train_pref = None
    _valid_pref = None

    def __init__(self, *args, **kwargs):
        super().__init__(args, *kwargs)
        # get artifact directory
        self._folder = get_artifact_directory()
        # create bin folder
        self._dest_dir = os.path.join(self._folder, 'BIN')
        os.mkdir(self._dest_dir)
        
        self._prep_path = os.path.join(self._folder, "Preprocessed")
        self._train_pref = os.path.join(self._prep_path, "train")
        self._valid_pref = os.path.join(self._prep_path, "valid")

    def process(self, data=None):     
        logger = logging.getLogger(__name__)
        _, _, bin_files = next(os.walk(self._dest_dir))

        if bin_files:
            logger.warn('There are already files in BIN folder. Skipping step...')
            return
            
        logger.debug("Running fairseq-preprocess")
        fairseq_preprocess_cmd = f'fairseq-preprocess -s gr -t gi --trainpref {self._train_pref} --validpref {self._valid_pref} --destdir {self._dest_dir}'
        os.system(fairseq_preprocess_cmd)
    
# Add element to the registry.
register_element(BinarizeElement)
