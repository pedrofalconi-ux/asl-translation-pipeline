import logging
import random

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

logger = logging.getLogger(__name__)


class AugmentationWordElement(PipelineElement):
    name = "augmentation_word"
    version = 1

    def __init__(self, *args, **kwargs):

        # Import TQDM.
        from tqdm import tqdm
        import nlpaug.augmenter.word as naw
        import nlpaug.flow as naf

        self._ratio = float(kwargs["ratio"]) if "ratio" in kwargs else None
        self._min_tokens = int(kwargs["min_tokens"]) if "min_tokens" in kwargs else None

        self.aug = naf.Sometimes([
            naw.RandomWordAug(action='delete', tokenizer=lambda x: x.split(" ")),
        ])

        self._tqdm = tqdm


    def process(self, data):
    
        logger.info(f"Number of tuples before augmentation {len(data)}.")
        augmented_phrases = []

        sampled_data = data.copy()

        # Do not apply back translation when sentence has less than `min_tokens` tokens
        if self._min_tokens:
            sampled_data = [
                t for t in sampled_data if len(t[0].split(" ")) > self._min_tokens
            ]

        # Only apply back translation on a subset of the data
        if self._ratio:
            random.shuffle(sampled_data)
            index = round(len(data) * self._ratio)
            sampled_data = sampled_data[:index]

        for gr, gi in self._tqdm(sampled_data, desc="augmentation_textual"):
            if not gr and not gi:
                continue
            
            new_gr = self.aug.augment(gr)[0]
    
            # Do not update if the translated sentence is equal to the original
            if  new_gr != gr:
                augmented_phrases.append((new_gr, gi))

        random.shuffle(augmented_phrases)
        data.extend(augmented_phrases)
        logger.info(f"Number of tuples before augmentation {len(data)}.")
        return data


# Add element to the registry.
register_element(AugmentationWordElement)
