import csv
import os
import subprocess

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

class GitSrcElement(PipelineElement):
    '''Reads `corpus.csv` from the given git repository.'''
    name = 'gitsrc'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'commit' not in kwargs:
            raise ValueError(f'`gitsrc` requires a `commit` parameter.')

        if any(x == kwargs['commit'] for x in ['master', 'dev']):
            raise ValueError(f'`commit` must be a SHA-1 hash, not a branch or tag name.')

        self._commit = kwargs['commit']
        self._remote = kwargs['remote'] if 'remote' in kwargs \
            else 'ssh://git@gitlab.lavid.ufpb.br/vlibras-deeplearning/corpus'

        self._folder = os.path.join(get_artifact_directory(), 'Source')

    def get_cache_key(self):
        return self._commit

    def process(self, data=[]):
        # create "Source" directory
        os.makedirs(self._folder, exist_ok=True)

        # fetch desired commit
        commands = [
            ['git', 'init'],
            ['git', 'remote', 'add', 'origin', self._remote],
            ['git', 'fetch', '-v', 'origin', self._commit],
            ['git', 'reset', '--hard', 'FETCH_HEAD'],
        ]

        for cmd in commands:
            subprocess.check_output(cmd, cwd=self._folder)

        # read file, return rows
        with open(os.path.join(self._folder, 'corpus.csv'), 'r') as fd:
            if data is None:
                data = []

            for row in csv.reader(fd):
                if row:
                    data.append(row[:2])

            return data

# Add element to the registry.
register_element(GitSrcElement)
