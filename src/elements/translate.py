from globalstore import add_to_store, fetch_from_store
from utils import add_submodule_to_sys_path
from elements.element import PipelineElement
from registry import register_element

class TranslationElement(PipelineElement):
    '''Translates a (PT, GI) tuple to a (GR, GI) tuple.'''
    name = 'translate'

    def __init__(self, *args, **kwargs):
        super().__init__(args, *kwargs)

        self._tr = fetch_from_store('vlibras-translation-instance')
        if self._tr:
            # Module is already loaded, we're done.
            return

        # Module wasn't loaded. Import it and save to the global store.
        add_submodule_to_sys_path('vlibras-translate')

        from vlibras_translate import translation
        self._tr = translation.Translation()

        add_to_store('vlibras-translation-instance', self._tr)

    def process(self, data):
        output = []

        for line in data:
            # FIXME: Should we really strip() here?
            pt = line[0].strip()
            gi = line[1].strip()

            output.append((self._tr.rule_translation(pt), gi))

        return output

# Add element to the registry.
register_element(TranslationElement)
