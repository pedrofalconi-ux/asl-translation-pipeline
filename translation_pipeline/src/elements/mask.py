from elements.element import PipelineElement
from globalstore import add_to_store, fetch_from_store
from registry import register_element
from utils import add_submodule_to_sys_path


class MaskingElement(PipelineElement):
    """Takes a list of (GR, GI) tuples and masks all the sentences."""

    name = "mask"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Import TQDM.
        from tqdm import tqdm

        self._tqdm = tqdm

        # Check for vlibras-translate.
        self._tr = fetch_from_store("vlibras-translation-instance")
        if not self._tr:
            # Module wasn't loaded. Import it and save to the global store.
            add_submodule_to_sys_path("vlibras-translate")

            from vlibras_translate import translation

            self._tr = translation.Translation()

            add_to_store("vlibras-translation-instance", self._tr)

    def process(self, data):
        output = []

        for line in self._tqdm(data, desc="masking"):
            gr, gi = line

            # FIXME: should we pass intensifier_on_right here? also, what about
            # wout_bpe in the constructor?
            gr_masked, gi_masked = self._tr.preprocess_specialist(gr, gi)

            output.append((gr_masked, gi_masked))

        return output


# Add element to the registry.
register_element(MaskingElement)
