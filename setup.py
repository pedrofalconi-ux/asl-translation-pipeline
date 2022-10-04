import os

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="translation-pipeline",
    version="1.0.0",
    author="LAViD-UFPB",
    author_email="vlibras@lavid.ufpb.br",
    description="VLibras (LAViD-UFPB) pipeline module for integrating corpus pre-processing, translation, augmentation and model training.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://www.vlibras.gov.br/",
    entry_points={
        "console_scripts": [
            "translation-pipeline=translation_pipeline.src.cli:main",
        ],
    },
    include_package_data=True,
    install_requires=[
        "tqdm",
    ],
    packages=setuptools.find_packages(),
    classifiers=[
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Development Status :: 5 - Production/Stable",
        "Topic :: Text Processing :: Linguistic",
        "Natural Language :: Portuguese (Brazilian)",
    ],
)
