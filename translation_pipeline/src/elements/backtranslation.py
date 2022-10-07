import logging
import random

import torch
from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)


class BackTranslationElement(PipelineElement):
    name = "back_translation"
    version = 2

    def __init__(self, *args, **kwargs):

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

        self._ratio = float(kwargs["ratio"]) if "ratio" in kwargs else None
        self._min_tokens = int(kwargs["min_tokens"]) if "min_tokens" in kwargs else None

        # Import TQDM.
        from tqdm import tqdm

        self._tqdm = tqdm

    def translate(self, texts, model, tokenizer, language=None):
        # Tokenize the texts
        gen_pipeline = pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else "cpu",
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
            language=self._lang,
        )
        en_texts = [text["generated_text"] for text in en_texts]
        # Translate from target language back to source language
        back_translated_texts = self.translate(
            en_texts,
            self.pt_model,
            self.pt_tokenizer,
            language="pt_BR",
        )
        return [text["generated_text"] for text in back_translated_texts]

    def process(self, data):
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

        for pt, gi in self._tqdm(sampled_data, desc="back_translating"):
            if not pt and not gi:
                continue
            try:
                new_pt = self.back_translate([pt])[0]
            except:
                continue
            # Do not update if the translated sentence is equal to the original
            if new_pt != pt:
                augmented_phrases.append((new_pt, gi))

        # Log a few random samples from the augmented_phrases
        logger.info(f"Generated {len(augmented_phrases)} new augmented phrases")
        for index in random.sample(range(len(augmented_phrases)), 3):
            logger.info(
                f"Sample {index} of the augmented phrases: {augmented_phrases[index]}."
            )

        random.shuffle(augmented_phrases)
        data.extend(augmented_phrases)
        return data


# Add element to the registry.
register_element(BackTranslationElement)
