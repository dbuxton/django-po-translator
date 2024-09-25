from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="django-po-translator",
    version="0.1.0",
    author="David Buxton",
    author_email="david@dbuxton.com",
    description="A Django extension for translating PO files using OpenAI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/django-po-translator",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=4.2",
        "polib",
        "openai",
        "pytest",
        "pytest-django",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Framework :: Django :: 4.2",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
