A Django app for translating PO files using OpenAI.

## Installation

```bash
pip install django-po-translator
```

## Usage

1. Add `'django_po_translator'` to your `INSTALLED_APPS` setting.

2. Run the management command:

```bash
python manage.py translate_po --folder /path/to/po/files --lang fr,es,de --api_key your_openai_api_key
```

For more options, run:

```bash
python manage.py translate_po --help
```

## License

This project is licensed under the MIT License.
