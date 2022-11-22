from elements.element import PipelineElement
from registry import register_element


class ConvertToJSONLElement(PipelineElement):
    name = "convert_to_jsonl"
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process(self, data):
        data_tuples = [{"translation": {"pt": row[0], "gi": row[1]}} for row in data]
        return data_tuples


# Add element to the registry.
register_element(ConvertToJSONLElement)
