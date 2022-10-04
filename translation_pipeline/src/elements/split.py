import random

from elements.element import PipelineElement
from registry import register_element


class SplitElement(PipelineElement):
    """Splits the dataset into training and validation sets.

    How much of the input dataset is set aside for usage as validation is
    determined by the `val_percentage` parameter. Outputs data to `train` and
    `valid`.

    Parameters:
    val_percentage - Percentage to use as validation set (e.g.: ".3").
    shuffle - Whether to shuffle the data before splitting.
    duplicate - Whether training and validation data should be the same.
    """

    name = "split"
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._val_percentage = float(kwargs["val_percentage"])
        except KeyError:
            raise ValueError("`split` requires a `val_percentage` parameter.")

        self._shuffle = "shuffle" in kwargs
        self._duplicate = "duplicate" in kwargs
        self._transformers = "transformers" in kwargs

    def process(self, data):
        val_line_count = round(len(data) * self._val_percentage)

        if self._shuffle:
            random.shuffle(data)

        if self._transformers:
            if self._duplicate:
                train_tuples = [
                    {"translation": {"pt": row[0], "gi": row[1]}} for row in data
                ]
                val_tuples = [
                    {"translation": {"pt": row[0], "gi": row[1]}} for row in data
                ]
            else:
                train_tuples = [
                    {"translation": {"pt": row[0], "gi": row[1]}}
                    for row in data[:-val_line_count]
                ]
                val_tuples = [
                    {"translation": {"pt": row[0], "gi": row[1]}}
                    for row in data[-val_line_count:]
                ]
        else:
            if self._duplicate:
                train_tuples = data
                val_tuples = data
            else:
                train_tuples = data[:-val_line_count]
                val_tuples = data[-val_line_count:]
        return {"train": train_tuples, "valid": val_tuples}


# Add element to the registry.
register_element(SplitElement)
