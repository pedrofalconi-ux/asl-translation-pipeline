import logging
import os
import random

import torch
from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)


class BackTranslationElement(PipelineElement):

    name = "back_translation"
    version = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        en_model_name = "Helsinki-NLP/opus-mt-ROMANCE-en"
        self.en_tokenizer = AutoTokenizer.from_pretrained(en_model_name)
        self.en_model = AutoModelForSeq2SeqLM.from_pretrained(en_model_name)
        pt_model_name = "Helsinki-NLP/opus-mt-en-ROMANCE"
        self.pt_tokenizer = AutoTokenizer.from_pretrained(pt_model_name)
        self.pt_model = AutoModelForSeq2SeqLM.from_pretrained(pt_model_name)

        if "lang" not in kwargs:
            self._lang = "en"
        else:
            self._lang = kwargs["lang"]

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Import TQDM.
        from tqdm import tqdm

        self._tqdm = tqdm

    def translate(self, texts, model, tokenizer, task, language=None):
        # Tokenize the texts
        gen_pipeline = pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer,
            device=self._device,
        )

        template = (
            lambda text: f"{text}" if language == "en" else f">>{language}<< {text}"
        )
        src_texts = [template(text) for text in texts]

        tokenizer_kwargs = {"truncation": True, "max_length": 512}
        translated_texts = gen_pipeline(src_texts, **tokenizer_kwargs)

        return translated_texts

    def back_translate(self, texts):
        # Translate from source to target language
        en_texts = self.translate(
            texts,
            self.en_model,
            self.en_tokenizer,
            task="translate Portuguese to English: ",
            language=self._lang,
        )
        en_texts = [text["generated_text"] for text in en_texts]
        # Translate from target language back to source language
        back_translated_texts = self.translate(
            en_texts,
            self.pt_model,
            self.pt_tokenizer,
            task="translate English to Portuguese: ",
            language="pt_BR",
        )
        return [text["generated_text"] for text in back_translated_texts]

    def process(self, data):
        augmented_phrases = []
        for pt, gi in self._tqdm(data, desc="back_translating"):
            if not pt and not gi:
                continue
            try:
                new_pt = self.back_translate([pt])[0]
            except:
                continue
            # Do not update if the translated sentence is equal to the original
            if new_pt != pt:
                augmented_phrases.append((new_pt, gi))

        random.shuffle(augmented_phrases)
        data.extend(augmented_phrases)
        return data


# Add element to the registry.
register_element(BackTranslationElement)
