import json
from typing import Generator, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import polib
import pytest

from django_po_translator.management.commands.translate_po import Command


@pytest.fixture
def mock_openai() -> Generator[MagicMock, None, None]:
    with patch("django_po_translator.management.commands.translate_po.OpenAI") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(
            {"translation": "Hola!", "failed": False}
        )
        yield mock


@pytest.fixture
def mock_pofile() -> Generator[MagicMock, None, None]:
    with patch("polib.pofile") as mock:
        mock_po = MagicMock(spec=polib.POFile)
        mock_po.metadata = {"Language": "es"}
        mock_entry = MagicMock(spec=polib.POEntry)
        mock_entry.msgid = "Hi!"
        mock_entry.msgstr = ""
        mock_entry.flags = []
        mock_po.__iter__.return_value = [mock_entry]
        mock.return_value = mock_po
        yield mock


def test_get_texts_to_translate(mock_pofile: MagicMock) -> None:
    command = Command()
    command.refresh_all = False
    command.fix_newlines = False
    command.fix_braces = False

    mock_pofile.__iter__.return_value = [polib.POEntry(msgid="Hi!", msgstr="", flags=[])]
    texts_to_translate = command.get_texts_to_translate(mock_pofile)
    assert texts_to_translate == [("Hi!", None)]


def test_process_translations(mock_openai: MagicMock, mock_pofile: MagicMock) -> None:
    command = Command()
    command.client = mock_openai.return_value
    command.model = "gpt-4o-mini"
    texts_to_translate: List[Tuple[str, Optional[str]]] = [("Hi!", None)]

    mock_entry = MagicMock(spec=polib.POEntry)
    mock_entry.msgid = "Hi!"
    mock_entry.msgstr = ""
    mock_pofile.return_value.__iter__.return_value = [mock_entry]

    command.process_translations(texts_to_translate, "es", mock_pofile.return_value, "dummy_path")
    assert mock_entry.msgstr == "Hola!"


def test_get_surrounding_texts() -> None:
    command = Command()
    texts: List[Tuple[str, Optional[str]]] = [("Hello", None), ("Hi!", None), ("Goodbye", None)]
    surrounding_texts = command.get_surrounding_texts(texts, 1)
    assert surrounding_texts == ['"Hello"', '"Goodbye"']


def test_create_translation_request() -> None:
    command = Command()
    surrounding_texts = ['"Hello"', '"Goodbye"']
    request = command.create_translation_request("Hi!", None, surrounding_texts, "es")
    assert "translate the following text from English into language with ISO-code `es`" in request
    assert "Hi!" in request
    assert "Hello" in request
    assert "Goodbye" in request
