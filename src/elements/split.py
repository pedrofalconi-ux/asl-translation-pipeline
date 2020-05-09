import random
from elements.element import PipelineElement
from registry import register_element

class SplitElement(PipelineElement):
    '''Splits the dataset into training and validation sets.

    How much of the input dataset is set aside for usage as validation is
    determined by the `val_percentage` parameter. Outputs data to `train` and
    `valid`.
    '''
    name = 'split'
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._val_percentage = float(kwargs['val_percentage'])
        except KeyError:
            raise ValueError('`split` requires a `val_percentage` parameter.')


    def process(self, data):
        val_line_count = round(len(data) * self._val_percentage)
        random.shuffle(data)

        return {
            'train': data[:-val_line_count],
            'valid': data[-val_line_count:]
        }

# Add element to the registry.
register_element(SplitElement)
