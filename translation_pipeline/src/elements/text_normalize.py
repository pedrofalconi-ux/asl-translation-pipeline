from elements.element import PipelineElement
from registry import register_element
from utils import get_file_md5_hash
from tqdm.auto import tqdm

from vlibras_preprocessing.preprocessor import TextProcessor 

class TextNormalizeElement(PipelineElement):
    name = 'text_normalize'
    version = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._processor = TextProcessor()

    def process(self, data):
        transformed_data = []

        for pt, gi in tqdm(data): 
            new_pt = self._processor.process(pt)
            transformed_data.append((new_pt, gi))
        return transformed_data
   
# Add element to the registry.
register_element(TextNormalizeElement)
