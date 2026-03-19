# ASL pipeline — scripts

Este diretório contém scripts utilitários usados na POC EN → ASL(gloss) e no preparo/avaliação do corpus.

> Observação: os scripts aqui são “colados” no pipeline principal (em `translation_pipeline/`) apenas em alguns pontos. Em geral, use-os manualmente para preparar dados, limpar corpus e avaliar resultados.

## Pré-requisitos (geral)

- Python 3.10+.
- Dependendo do script:
  - `sentencepiece` (para tokenização/treino de subword)
  - `sacrebleu` (para BLEU)
  - `lingua-language-detector` **ou** `langid` (para detecção de idioma)
  - `fairseq` (somente se você for usar a opção `--run-fairseq-preprocess` no `asl_prepare.py`)

Dica (Windows): há um setup guiado em PowerShell no `setup_lightconv_windows.ps1`.

---

## 1) `asl_prepare.py`

Prepara um dataset paralelo EN/ASL(gloss) para treino:

- Lê um corpus paralelo a partir de:
  - um TSV (`--input` com `src\ttgt` por linha), ou
  - dois arquivos paralelos (`--src-file` / `--tgt-file`, 1 sentença por linha)
- (Opcional) normaliza texto (`--normalize`) e remove aspas/`;` (`--strip-quotes-semicolons`).
- (Opcional) canoniza marcadores comuns de glosa no target (`--tgt-canonicalize-markers`), por exemplo:
  - `PRO-3(he)` → `PRO_3_he`
  - `wh-q(when)` → `WHQ_when`
- Faz split train/valid/test embaralhando com `--seed`.
- Treina SentencePiece (modelo conjunto src+tgt por padrão; ou separado com `--sp-separate`).
- Aplica SentencePiece e escreve arquivos `*.sp.<lang>`.
- (Opcional) roda `fairseq-preprocess` (`--run-fairseq-preprocess`) para gerar `data-bin/...`.

### Exemplos

TSV (uma linha = `EN<TAB>ASL`):

```bash
python asl_pipeline/scripts/asl_prepare.py \
  --input data/meu_dataset.tsv --input-format tsv \
  --src-lang en --tgt-lang asl \
  --outdir data/asl_100k \
  --vocab-size 8000 --seed 42 \
  --normalize --strip-quotes-semicolons \
  --tgt-canonicalize-markers
```

Arquivos paralelos:

```bash
python asl_pipeline/scripts/asl_prepare.py \
  --src-file asl_pipeline/data/raw/sample.en \
  --tgt-file asl_pipeline/data/raw/sample.asl \
  --outdir data/asl_100k \
  --vocab-size 8000 --seed 42 \
  --normalize --strict-align
```

Gerar também `data-bin` via fairseq (se o fairseq estiver instalado nesse Python):

```bash
python asl_pipeline/scripts/asl_prepare.py \
  --src-file ... --tgt-file ... \
  --outdir data/asl_100k \
  --vocab-size 8000 \
  --run-fairseq-preprocess \
  --destdir data-bin/asl_100k
```

Notas práticas:

- Use `--limit` (e `--limit-mode`) para criar subconjuntos pequenos e iterar rápido.
- Se usar `--sp-separate`, o script treina um SentencePiece para EN e outro para ASL.

---

## 2) `filter_parallel_by_lang.py`

Filtra um corpus paralelo removendo linhas do **lado fonte** que não parecem estar em inglês, mantendo alinhamento (se remove a linha fonte, remove a linha alvo correspondente).

Principais modos:

- `--mode keep-en` (padrão): mantém apenas o que for classificado como inglês.
- `--mode drop-langs`: remove apenas idiomas listados em `--drop-langs`.

Detector:

- `--detector lingua` (padrão): usa `lingua` (mais robusto, mas pode exigir ajuste de `--min-en-confidence` para linhas curtas).
- `--detector langid`: alternativa mais simples.

Recursos úteis:

- `--fix-mojibake`: tenta reparar sequências do tipo `Ã`, `Â`, `â€™`, etc.
- Heurística adicional: se a linha contiver caracteres nórdico/germânicos (ÆØÅÄÖÜß etc.), ela é descartada.

### Exemplo

```bash
python asl_pipeline/scripts/filter_parallel_by_lang.py \
  --src-file asl_pipeline/data/raw/subset_100k.filtered.en.txt \
  --tgt-file asl_pipeline/data/raw/subset_100k.filtered.asl.txt \
  --out-src asl_pipeline/data/raw/subset_100k.filtered.en.langclean.txt \
  --out-tgt asl_pipeline/data/raw/subset_100k.filtered.asl.langclean.txt \
  --detector lingua --mode keep-en --min-en-confidence 0.60 --fix-mojibake
```

---

## 3) `make_unseen_test_from_corpus.py`

Cria um novo `test_unseen` a partir de um corpus grande, garantindo que as sentenças do teste não apareçam (match exato após normalização) no `train`/`valid` atuais.

O objetivo é reduzir “vazamento” de frases semelhantes do treino para o teste e tornar a avaliação mais realista.

Funcionalidades:

- Amostragem determinística com `--seed`.
- (Opcional) filtra para manter apenas frases classificadas como inglês (`--en-only`) com `lingua` ou `langid`.
- (Opcional) remove pares com caracteres fora de ASCII imprimível (`--ascii-only`).
- (Opcional) canoniza marcadores no ASL antes de amostrar (`--canonicalize-asl`).
- (Opcional) aplica SentencePiece nos arquivos gerados se você fornecer `--spm-en` e `--spm-asl`.

### Exemplo

```bash
python asl_pipeline/scripts/make_unseen_test_from_corpus.py \
  --corpus-en asl_pipeline/data/raw/corpus_0001.clean.en.txt \
  --corpus-asl asl_pipeline/data/raw/corpus_0001.clean.asl.txt \
  --train-en data/asl_100k_canon_enonly_clean/train.en \
  --train-asl data/asl_100k_canon_enonly_clean/train.asl \
  --valid-en data/asl_100k_canon_enonly_clean/valid.en \
  --valid-asl data/asl_100k_canon_enonly_clean/valid.asl \
  --out-en  data/asl_100k_canon_enonly_clean/test_unseen.en \
  --out-asl data/asl_100k_canon_enonly_clean/test_unseen.asl \
  --size 8828 --seed 42 \
  --en-only --detector lingua --min-en-confidence 0.70 \
  --spm-en  data/asl_100k_canon_enonly_clean/sp_en.model \
  --spm-asl data/asl_100k_canon_enonly_clean/sp_asl.model
```

---

## 4) `eval_bleu.py`

Calcula BLEU usando `sacrebleu` dado um arquivo de hipóteses (`--sys`) e um ou mais arquivos de referência (`--ref`).

### Exemplo

```bash
python asl_pipeline/scripts/eval_bleu.py \
  --sys results/minhas_hyps.asl \
  --ref data/asl_100k_canon_enonly_clean/test.asl
```

Se tiver múltiplas referências:

```bash
python asl_pipeline/scripts/eval_bleu.py \
  --sys results/minhas_hyps.asl \
  --ref data/ref1.asl --ref data/ref2.asl
```

---

## 5) `setup_lightconv_windows.ps1`

Script PowerShell “one-shot” para Windows que:

- Encontra Python via `py -<versão>`.
- Cria/usa uma venv (`.venv-lightconv` por padrão).
- Instala `sentencepiece` e dependências.
- Instala `torch`.
- Valida toolchain MSVC para compilar `fairseq==0.12.2`.
- Instala `fairseq==0.12.2`.
- Roda `asl_prepare.py --run-fairseq-preprocess` para gerar `data-bin/asl`.

### Exemplos

Rodar com defaults:

```powershell
pwsh -File asl_pipeline/scripts/setup_lightconv_windows.ps1
```

Forçar recriar venv e rebuild do `data-bin`:

```powershell
pwsh -File asl_pipeline/scripts/setup_lightconv_windows.ps1 -RecreateVenv -ForceRebuildDataBin
```

CPU-only torch:

```powershell
pwsh -File asl_pipeline/scripts/setup_lightconv_windows.ps1 -CpuOnlyTorch
```
