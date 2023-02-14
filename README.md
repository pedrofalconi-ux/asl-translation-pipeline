<div align="center">
  <a href="https://www.vlibras.gov.br/">
    <img
      alt="VLibras"
      src="https://www.librasol.com.br/wp-content/uploads/2015/04/avatar.png"
       height="304"
       width="187"
    />
  </a>
</div>

# translation-pipeline

![Licença](https://img.shields.io/badge/license-LGPLv3-blue.svg)
![VLibras](https://img.shields.io/badge/vlibras%20suite-2022-green.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAUCAYAAAC9BQwsAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA3XAAAN1wFCKJt4AAAAB3RJTUUH4wIHCiw3NwjjIgAAAQ9JREFUOMuNkjErhWEYhq/nOBmkDNLJaFGyyyYsZzIZKJwfcH6AhcFqtCvFDzD5CQaTFINSlJJBZHI6J5flU5/P937fube357m63+d+nqBEagNYA9pAExgABxHxktU3882hjqtd9d7/+lCPsvpDZNA+MAXsABNU6xHYQ912ON2qC2qQ/X+J4XQXEVe/jwawCzwNAZp/NCLiDVgHejXgKIkVdGpm/FKXU/BJDfytbpWBLfWzAjxVx1Kuxwno5k84Jex0IpyzdN46qfYSjq18bzMHzQHXudifgQtgBuhHxGvKbaPg0Klaan7GdqE2W39LOq8OCo6X6kgdeJ4IZKUKWq1Y+GHVjF3gveTIe8BiCvwBEZmRAXuH6mYAAAAASUVORK5CYII=)

---

## Table of Contents
- [Getting Started](#getting-started)
- [Pipeline Elements](#pipeline-elements)
- [Contributors](#contributors)
- [License](#license)

## Getting Started
### Introduction
This repository contains the implementation of a generic data processing pipeline, plus several elements which allow it to be used for corpus pre-processing, translation, augmentation and finally, model training.

### Prerequisites
- Python >= 3.6
- Other packages, depending on which elements are used:
  - For `csvsrc` and `filesrc`: `rhash` binary installed and available in `$PATH`
  - For `translate`: `tqdm` installed via pip (and the relevant `vlibras-translate` dependencies. See that repository for more details)
  - For `learn_bpe`: `subword-nmt` available in `$PATH`.
  - For `binarize`, `train` and `interactive_score`: `fairseq` installed via pip and its commands available in `$PATH`.

- To run the pipeline locally, the steps are as follows:
  - Optionally, create and activate a virtualenv:
    ```bash
    $ virtualenv venv && source venv/bin/activate

    # or, if you don't want to install `virtualenv`:
    $ python3 -m venv venv && source venv/bin/activate
    ```
  - Or use conda to create the environment needed (we recommend this method)
    ```bash
    $ conda create -n pipeline python=3.8
    $ conda activate pipeline
    ```
  - Install the required dependencies:
    ```bash
    $ pip install -r requirements.txt
    ```

  - During development, it is also useful to run code-style and linting tools before commiting and/or creating a merge request:
    Install dev dependencies:
    ```bash
    $ pip install -r requirements-dev.txt
    ```
    Run linter and formatting on all source files:
    ```bash
    $ pre-commit run --all-files
    ```

### Cloning and Installation
This git repository uses submodules. As such, either manually initialize them yourself after cloning or pass `--recurse-submodules` to the `git clone` call.

Installation can be done by running `pip install . -e` from this directory to install as an editable pip package.

This project requires git-lfs to work properly when cloned. Ensure that git lfs is installed before you proceed.

```bash
$ apt-get -qq install build-essential git git-lfs
$ git lfs install
```

### Usage
#### Programatically
Import the `execute` function from `cli.py` and use it as follows:
```python
artifact_hash = execute('<PIPELINE JSON>', '<USER COMMENT>')
```

#### Via CLI
The `cli.py` file also acts as an entry point. Usage is as follows:
```
usage: translation-pipeline [-h] [-p PIPELINE] [-c CORPUS] [-t TRAIN_HASH] [-m MESSAGE]

optional arguments:
  -h, --help            show this help message and exit
  -p PIPELINE, --pipeline PIPELINE
                        Path to the pipeline JSON file.
  -c CORPUS, --corpus CORPUS
                        Path to the corpus CSV file.
  -t TRAIN_HASH, --train-hash TRAIN_HASH
                        Train artifact hash, if running a test pipeline.
  -m MESSAGE, --message MESSAGE
                        Execution message.
```
Note that `-p` and `-c` are not optional, and while `-m` is optional when invoking the pipeline from the CLI, if it is omitted, the script will prompt you to type an execution message manually before starting the pipeline.

### Artifacts
While the pipeline is executing, relevant files will be written to `artifacts/tmp`. Once the pipeline finishes, a hash is calculated taking into consideration all the data that passed through the pipeline, and the `tmp` folder will be renamed according to that hash.

Said artifact hash will be printed to the screen after the pipeline finishes, logged to the relevant log file in `logs` and saved to the `execution_log.csv` file.

## Pipeline Elements
### The Basics
Data travels in the pipeline through elements. An element can be a source of data (for example, `csvsrc`), a data processor (for example, `translate`) or a sink for data (for example, `filedest`). See the `src/elements` folder for implementation examples.

### Caching
Element outputs get cached to avoid wasting time regenerating data that we already have after sequential executions of the same pipeline. Each element is allowed to define its own cache key, which MUST depend ONLY on variables that would cause the output of the `process()` call to change when called with the same data.

For example, the only thing that can cause the output of `csvsrc` to change is if the contents of the file that `path` points to changes. As such, its cache key ONLY changes if the contents of the file change.

If no cache key function is defined for an element, a key will be automatically generated by hashing the parameters dictionary. This behaviour covers most cases.

## Contributors
* Samuel de Moura - <samuel.moura@lavid.ufpb.br> / <samueldemouramoreira@gmail.com>

## License
This project is licensed under the LGPLv3 License - see the [LICENSE](LICENSE.md) file for details.
