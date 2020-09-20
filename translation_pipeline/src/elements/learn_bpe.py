import logging
import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

class LearnBpeElement(PipelineElement):
    ''' Learn BPE Step
        Concatena gr e gi preprocessados e executa o learn bpe do subword-nmt na saída.
    '''
    name = 'learn_bpe'
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        '''Kwargs:
           -src {string}: Source file extension ('gr' or 'gi').
           -tgt {string}: Target file extension ('gr' or 'gi').
           -bpe_tokens {int}: Number of merges(BPE).
        '''
        super().__init__(*args, **kwargs)

        # set src to src argument if it's given, else set to default(gr)
        if 'src' in kwargs:
            self._src = kwargs['src']
        else:
            self._src = 'gr'

        # set tgt to tgt argument if it's given, else set to default(gi)
        if 'tgt' in kwargs:
            self._tgt = kwargs['tgt']
        else:
            self._tgt = 'gi'

        # set bpe tokens
        if 'bpe_tokens' in kwargs:
            self._bpe_tokens = kwargs['bpe_tokens']
        else:
            self._bpe_tokens = 10000

        # set BPE folder
        self._bpe_path = os.path.join(get_artifact_directory(), 'BPE')

        # set preprocessed path
        self._preprocessed_path = os.path.join(get_artifact_directory(), 'Preprocessed')

        # set train concat corpus
        self._train_concat_corpus = os.path.join(self._bpe_path, f'train.{self._src}-{self._tgt}')
        os.makedirs(os.path.dirname(self._train_concat_corpus), exist_ok=True)

        # set bpe_code
        self._bpe_code = os.path.join(self._bpe_path, 'bpe_code')


    def process(self, data=None):
        logger = logging.getLogger(__name__)

        logger.info(f'bpe_tokens {self._bpe_tokens}')
        logger.info(f'source language {self._src}')
        logger.info(f'target language {self._tgt}')

        # set path to files
        preprocessed_train_gr_file = os.path.join(self._preprocessed_path, 'train.' + self._src)
        preprocessed_train_gi_file = os.path.join(self._preprocessed_path, 'train.' + self._tgt)

        if os.path.isfile(self._train_concat_corpus):
            logger.warning(f'File {self._train_concat_corpus} already exists. Skipping...')
            return

        # concatenation of preprocessed gr and gi to a single train file
        os.system(f'cat {preprocessed_train_gr_file} {preprocessed_train_gi_file} > {self._train_concat_corpus}')

        # run learn bpe using the concatenated file, with 'bpe_tokens'(number) merge operations
        logger.debug(f'Running learn_bpe.py on {self._train_concat_corpus}')
        os.system(f'subword-nmt learn-bpe -s {self._bpe_tokens} < {self._train_concat_corpus} > {self._bpe_code}')

# Add element to the registry.
register_element(LearnBpeElement)
