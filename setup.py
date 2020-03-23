import os
import setuptools

# TODO: Install rhash dependency

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='translation-pipeline',
    version='0.0.1',
    author='LAVID-UFPB',
    author_email='vlibras@lavid.ufpb.br',
    description='VLibras (LAVID-UFPB) pipeline module for integrating corpus pre-processing, translation, augmentation and model training.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://www.vlibras.gov.br/',
    include_package_data=True,
    install_requires=[
        'tqdm',
    ],
    packages=setuptools.find_packages(),
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: POSIX :: Linux',
        # 'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Development Status :: 3 - Alpha',
        # 'Development Status :: 5 - Production/Stable',
        'Topic :: Text Processing :: Linguistic',
        'Natural Language :: Portuguese (Brazilian)',
    ],
)
