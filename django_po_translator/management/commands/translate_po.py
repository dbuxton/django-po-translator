import logging
import os
from typing import List, Optional, Tuple

import polib
from django.conf import settings
from django.core.management.base import BaseCommand
from openai import OpenAI


class Command(BaseCommand):
    help = "Translate PO files using OpenAI"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--folder", required=True, help="Input folder containing .po files")
        parser.add_argument(
            "--lang", required=True, help="Comma-separated language codes to filter .po files"
        )
        parser.add_argument("--fuzzy", action="store_true", help="Remove fuzzy entries")
        parser.add_argument(
            "--model", default="gpt-4o-mini", help="OpenAI model to use for translations"
        )
        parser.add_argument("--api_key", help="OpenAI API key")
        parser.add_argument(
            "--folder-language", action="store_true", help="Set language from directory structure"
        )
        parser.add_argument(
            "--refresh_all", action="store_true", help="Re-do all existing translations"
        )
        parser.add_argument(
            "--fix-newlines", action="store_true", help="Fix newlines in translations"
        )
        parser.add_argument("--fix-braces", action="store_true", help="Fix braces in translations")

    def handle(self, *args, **options) -> None:
        # Set up logging
        logging.basicConfig(level=logging.INFO)

        # Initialize OpenAI client
        api_key = options["api_key"] or settings.OPENAI_API_KEY
        client = OpenAI(api_key=api_key)

        # Create a configuration object
        self.client = client
        self.model = options["model"]
        self.fuzzy = options["fuzzy"]
        self.folder_language = options["folder_language"]
        self.refresh_all = options["refresh_all"]
        self.fix_braces = options["fix_braces"]
        self.fix_newlines = options["fix_newlines"]

        languages = [lang.strip() for lang in options["lang"].split(",")]
        folders_to_process = self.get_folders_to_process(options["folder"])
        for folder in folders_to_process:
            self.scan_and_process_po_files(folder, languages)

    def scan_and_process_po_files(self, input_folder: str, languages: List[str]) -> None:
        """Scans and processes .po files in the given input folder."""
        for root, _, files in os.walk(input_folder):
            for file in filter(lambda f: f.endswith(".po"), files):
                po_file_path = os.path.join(root, file)
                logging.info(f"Discovered .po file: {po_file_path}")
                self.process_po_file(po_file_path, languages)

    def process_po_file(self, po_file_path: str, languages: List[str]) -> None:
        """Processes an individual .po file."""
        if self.fuzzy:
            self.disable_fuzzy_translations(po_file_path)
        try:
            po_file = polib.pofile(po_file_path)
            file_lang = self.get_file_language(po_file, po_file_path, languages)
            if not file_lang:
                return

            texts_to_translate = self.get_texts_to_translate(po_file)
            self.process_translations(texts_to_translate, file_lang, po_file, po_file_path)
            po_file.save(po_file_path)
            logging.info(f"Finished processing .po file: {po_file_path}")
        except Exception as e:
            logging.error(f"Error processing file {po_file_path}: {e}")

    def disable_fuzzy_translations(self, po_file_path: str) -> None:
        """Disables fuzzy translations in a .po file by removing the 'fuzzy' flags from entries."""
        try:
            po_file = polib.pofile(po_file_path)
            for entry in po_file:
                if "fuzzy" in entry.flags:
                    entry.flags.remove("fuzzy")
            po_file.save(po_file_path)
            logging.info(f"Fuzzy translations disabled in file: {po_file_path}")
        except Exception as e:
            logging.error(f"Error while disabling fuzzy translations in file {po_file_path}: {e}")

    def get_file_language(
        self, po_file: polib.POFile, po_file_path: str, languages: List[str]
    ) -> Optional[str]:
        """Gets the language of the .po file, inferring from folder structure if necessary."""
        file_lang = po_file.metadata.get("Language", "")
        if file_lang in languages:
            return file_lang

        if self.folder_language:
            folder_parts = po_file_path.split(os.sep)
            inferred_lang = next((part for part in folder_parts if part in languages), None)
            if inferred_lang:
                logging.info(f"Inferred language for .po file: {po_file_path} as {inferred_lang}")
                return inferred_lang

        logging.warning(f"Skipping .po file due to language mismatch: {po_file_path}")
        return None

    def get_texts_to_translate(self, po_file: polib.POFile) -> List[Tuple[str, Optional[str]]]:
        """Gets the texts to translate from a .po file."""
        return [
            (entry.msgid, entry.msgctxt)
            for entry in po_file
            if (
                (not entry.msgstr and entry.msgid and "fuzzy" not in entry.flags)
                or (entry.msgid and self.refresh_all)
                or (
                    self.fix_newlines
                    and (
                        entry.msgid.startswith("\n") != entry.msgstr.startswith("\n")
                        or entry.msgid.endswith("\n") != entry.msgstr.endswith("\n")
                    )
                )
                or (self.fix_braces and "{" in entry.msgid and "{" not in entry.msgstr)
            )
        ]

    def process_translations(
        self,
        texts: List[Tuple[str, Optional[str]]],
        target_language: str,
        po_file: polib.POFile,
        po_file_path: str,
    ) -> None:
        """Processes translations one by one."""
        for index, (text, ctx) in enumerate(texts):
            logging.info(f"Translating text {index + 1}/{len(texts)} in file {po_file_path}")
            surrounding = self.get_surrounding_texts(texts, index)
            translation_request = self.create_translation_request(
                text, ctx, surrounding, target_language
            )
            translated_text = self.perform_translation(translation_request)
            if translated_text:
                self.update_po_entry(po_file, text, translated_text)
            else:
                logging.error(f"No translation returned for text: {text}")

    def get_surrounding_texts(
        self, texts: List[Tuple[str, Optional[str]]], index: int
    ) -> List[str]:
        """Gets the surrounding texts for context."""
        prev = texts[index - 1] if index > 0 else None
        _next = texts[index + 1] if index < len(texts) - 1 else None
        return [f'"{s[0]}"' for s in [prev, _next] if s and s[0]]

    def create_translation_request(
        self, text: str, ctx: Optional[str], surrounding: List[str], target_language: str
    ) -> str:
        """Creates a translation request."""
        context = f'\n- The msgctx of the string you have been asked to translate is "{ctx}". Remember, you shouldn\'t translate this but it might help with ambiguity of the text.'
        return f"""You are an expert translator, translating items in a `.po` file to localize a software application.
- You must always choose the most likely translation based on limited context, or if you have doubts, return the original English text.
- Do not wrap your translation in quotes or other formatting.
- Ensure that variable names, links etc are preserved verbatim.
- All items in braces must be preserved verbatim.
- Don't include any context on how you arrived at your translation
- If you can't translate with confidence, set the `failed` key in your response to `true`
- For context, the surrounding texts in the file are {', '.join(surrounding)}. Don't translate these; just use them as hints as to meaning of ambiguous words.{context}
- Put the finished translation into the key `translation` in your JSON response
- Make sure that the JSON you produce is correct; in particular you must make sure that newlines are formatted as \\n not as actual newlines.
- If the text you are translating begins and/or ends with a newline, make sure that the translation does too.

Please translate the following text from English into language with ISO-code `{target_language}`:"""
