import os
from elements.element import PipelineElement
from registry import register_element
from artifact import get_artifact_directory
import logging


class ApplyBpeElement(PipelineElement):
    """ Apply BPE Step
        Executa o apply bpe do subword-nmt nos arquivos de treino e validação.
    """
    name = "ApplyBPE"


    def __init__(self, *args, **kwargs):
        """Kwargs:
           -src {string}: Source file extension ('gr' or 'gi').
           -tgt {string}: Target file extension ('gr' or 'gi').
           -train_hash {string}: Train folder hash value (when using ApplyBPE on Test Pipeline).
        """
        super().__init__(args, *kwargs)

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
        
        self._bpe_path = os.path.join(get_artifact_directory(), "BPE")
        self._preprocessed_path = os.path.join(get_artifact_directory(), "Preprocessed")
        self._bpe_code = os.path.join(self._bpe_path, "bpe_code")
        
        if 'train_hash' in kwargs:
            self._set_corp_list = ['test']
            train_hash = kwargs['train_hash']
            
            # create test bpe dir
            os.makedirs(os.path.dirname(self._bpe_code), exist_ok=True)
            
            # get path for folder with train symlink and folder with the original files
            train_link_dir = os.path.join(get_artifact_directory(), train_hash)
            train_original_dir = os.path.join(os.path.dirname(get_artifact_directory()), train_hash)
            
            # make symlink folder and populate it
            os.mkdir(train_link_dir)
            
            # create BIN symlink
            train_bin_src = os.path.join(os.getcwd(), train_original_dir, 'BIN')
            train_bin_dst = os.path.join(train_link_dir, 'BIN')
            os.symlink(train_bin_src, train_bin_dst)
            
            # create bpe-code symlink
            train_bpe_src = os.path.join(os.getcwd(), train_original_dir, 'BPE', 'bpe_code')
            print(train_bpe_src)
            train_bpe_dst = os.path.join(train_link_dir, 'bpe_code')
            self._bpe_code = train_bpe_dst
            os.symlink(train_bpe_src, train_bpe_dst)
            
            # create checkpoint-best symlink
            train_checkpoint_src = os.path.join(os.getcwd(), train_original_dir, 'Checkpoints', 'checkpoint_best.pt')
            print(train_checkpoint_src)
            train_checkpoint_dst = os.path.join(train_link_dir, 'checkpoint_best.pt')
            os.symlink(train_checkpoint_src, train_checkpoint_dst)
            
            # create train cfg file symlink
            train_cfg_src = os.path.join(os.getcwd(), train_original_dir, 'train_parameters.json')
            train_cfg_dst = os.path.join(train_link_dir, 'train_parameters.json')
            os.symlink(train_cfg_src, train_cfg_dst)
        else:
            self._set_corp_list = ['train', 'valid']
            
    def process(self, data=None):
        logger = logging.getLogger(__name__)   
            
        for set_corp in self._set_corp_list:
            for lang in [self._src, self._tgt]:
                file_to_apply_bpe_on = os.path.join(self._preprocessed_path, set_corp + "." + lang)
                output_file = os.path.join(self._bpe_path, set_corp + "." + lang)

                # Run apply bpe on set_corp files
                logger.debug(f'Running apply_bpe.py on {file_to_apply_bpe_on}')
                os.system(f"subword-nmt apply-bpe -c {self._bpe_code} < {file_to_apply_bpe_on} > {output_file}")

# Add element to the registry.
register_element(ApplyBpeElement)