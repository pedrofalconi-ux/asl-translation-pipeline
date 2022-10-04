from elements.element import PipelineElement
from registry import register_element


class SentenceSplitElement(PipelineElement):
    """Splits paragraphs into different sentences."""

    name = "sentence_split"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Whether to discard sentences if they can't be evenly split. If this
        # flag is not set, the original un-split sentences will be kept.
        self._discard_uneven_splits = "discard_uneven_splits" in kwargs

        # Whether to duplicate split sentences. That is, append both the split
        # sentences and the original sentence to the output.
        self._duplicate = "duplicate" in kwargs

    def _split_sentences(self, sentences, sep):
        """For each sentence in `sentences`, separate it by `sep`, and concatenate
        `sep` back into the string whenever necessary to maintain the original
        sentence as it was originally.
        """
        output = []
        for sentence in sentences:
            split = sentence.split(sep)
            for i, split_sentence in enumerate(split):
                if not split_sentence:
                    continue

                if i < len(split) - 1:
                    output.append(f"{split_sentence.strip()} {sep}")
                else:
                    output.append(f"{split_sentence.strip()}")

        return output

    def process(self, data):
        output = []

        for gr, gi in data:
            gr_splitted = [gr]
            gi_splitted = [gi]

            for separator in ["[PONTO]", "[INTERROGAÇÃO]", "[EXCLAMAÇÃO]"]:
                gr_splitted = self._split_sentences(gr_splitted, separator)
                gi_splitted = self._split_sentences(gi_splitted, separator)

            if len(gr_splitted) != len(gi_splitted):
                # Mismatch during separation.
                if not self._discard_uneven_splits:
                    # Output original sentences if 'discard_uneven_splits' is
                    # not defined. Otherwise, discard original sentence pair
                    # and the splits.
                    output.append((gr, gi))
            else:
                for new_gr, new_gi in zip(gr_splitted, gi_splitted):
                    output.append((new_gr, new_gi))

                if self._duplicate and len(gr_splitted) > 1:
                    output.append((gr, gi))

        return output


# Add element to the registry.
register_element(SentenceSplitElement)
