# Projeto: Pipeline de Tradução EN → ASL (gloss) com Fairseq (LightConv) no Windows

> Objetivo: treinar e avaliar um modelo EN→ASL(gloss) no Windows, com preparação de dados, tokenização (SentencePiece), binarização (fairseq-preprocess) e avaliação (interactive + BLEU).

## 1) Resumo executivo (para abrir a apresentação)

- **Problema**: o corpus paralelo EN→ASL tinha ruídos importantes (linhas não-inglesas e “mojibake”) e o ASL possuía marcadores com pontuação/parênteses que “quebravam” a tokenização e o decoder.
- **Solução**: refizemos o dataset com **limpeza forte** (EN-only + correção de mojibake) e **canonicalização do ASL** (normalização de marcadores como `PRO-3(he)` e `wh-q(when)`), treinamos um LightConv e criamos avaliações para medir qualidade e generalização.
- **Resultado**: o modelo chegou a **epoch 40**, e fizemos várias rodadas de avaliação, incluindo teste “unseen” (sem frases do treino) para evitar vazamento e medir generalização real.

## 2) Linha do tempo (nossa trajetória)

### Fase A — Setup do repositório e execução no Windows

1. **Clone do repositório + ambiente**
   - Organização do workspace e definição de um venv dedicado ao Fairseq/treino (`.venv-lightconv`).
   - Ajustes para Windows/PowerShell:
     - Alguns comandos nativos escrevem logs em `stderr` (ex.: aviso do `tensorboardX`), o que pode “quebrar” scripts PowerShell quando `$ErrorActionPreference='Stop'`.

2. **Compatibilidade de runtime (PyTorch 2.6+ + Windows rename)**
   - Criamos um wrapper de compatibilidade que:
     - força `torch.load(..., weights_only=False)` (mudança de default no PyTorch 2.6),
     - corrige `rename` no Windows usando `os.replace` (para sobrescrita atômica de checkpoints).
   - Arquivo: `fairseq_compat_run.py`.

### Fase B — Diagnóstico do dataset e reinício do pipeline

3. **Problema 1: ASL com marcadores e pontuação “explodindo” tokens**
   - O target ASL tinha padrões do tipo `PRO-3(he)`, `wh-q(where)`, etc.
   - Isso gerava muitas subpieces “ruins” (ex.: `(`, `)`, `-3`, `wh-q(`), prejudicando o decoder.

4. **Solução: Canonicalização do ASL**
   - Implementamos canonicalização dos marcadores:
     - `PRO-3(he) → PRO_3_he`
     - `POSS-1(our) → POSS_1_our`
     - `wh-q(when) → WHQ_when`
   - Arquivo: `asl_pipeline/scripts/asl_prepare.py` (função `canonicalize_asl_markers`).

5. **Problema 2: Source “English” com mistura de línguas + mojibake**
   - Encontramos linhas em dinamarquês/alemão/sueco/norueguês e “mojibake” (ex.: `Â`, `Ã`, `â€...`).
   - Isso poluía o modelo e distorcia métricas.

6. **Solução: Filtro EN-only + fix de mojibake mantendo alinhamento**
   - Criamos/ajustamos um filtro de corpus paralelo que:
     - remove pares não-ingleses,
     - tenta corrigir mojibake,
     - mantém alinhamento (se cai EN, cai ASL correspondente).
   - Arquivo: `asl_pipeline/scripts/filter_parallel_by_lang.py`.

### Fase C — Rebuild do dataset (EN-only + canonicalização + SentencePiece)

7. **Dataset final usado no treino principal**
   - Diretório: `data/asl_100k_canon_enonly_clean/`
   - Conteúdo:
     - splits: `train.en/.asl`, `valid.en/.asl`, `test.en/.asl`
     - SentencePiece **separado**: `sp_en.model` e `sp_asl.model`
     - versões tokenizadas: `train.sp.en`, `train.sp.asl`, etc.

8. **Binarização (fairseq-preprocess)**
   - Diretório binarizado do treino: `data-bin/asl_100k_canon_enonly_clean/`
   - Dicionários fixos: `dict.en.txt`, `dict.asl.txt` (reutilizados em novos testes).

### Fase D — Treino LightConv e retomadas

9. **Treino principal (LightConv) até epoch 40**
   - Script de treino: `train_lightconv_asl_100k_canon_windows.ps1`
   - Modelo/arquitetura: `--arch lightconv_iwslt_de_en`
   - Hiperparâmetros principais:
     - `--lr 5e-4`, `--lr-scheduler inverse_sqrt`, `--warmup-updates 4000`
     - `--dropout 0.3`, `--label-smoothing 0.1`, `--weight-decay 0.0001`
     - `--max-tokens 512`, `--update-freq 1`
     - checkpoint: `--save-interval-updates 2000`, `--keep-interval-updates 10`, `--keep-best-checkpoints 1`
   - Checkpoints no disco D (restrição de espaço):
     - `D:\translation-pipeline-checkpoints\lightconv_asl_100k_canon_enonly_clean_invSqrt\checkpoint_last.pt`

10. **Logs de treino**
    - Treino inicial (até epoch 20): `logs/train_lightconv_asl_100k_canon_enonly_clean.log`
      - início: `2026-03-15 22:04`
    - Continuação/rodada até epoch 40: `logs/train_lightconv_asl_100k_canon_enonly_clean_ep40.log`
      - final: `2026-03-17 06:14` com `done training`.

> Observação prática: houve interrupções (sleep/desligamento), então a retomada foi feita via `checkpoint_last.pt` quando existente (o script adiciona `--restore-file` automaticamente).

### Fase E — Avaliação e métrica (interactive + BLEU)

11. **Avaliação qualitativa: 60 frases simples (interactive)**
    - Objetivo: demonstrar exemplos de tradução em frases curtas e “do dia a dia”.
    - Saída consolidada: `results/eval_epoch40_simple60/outputs_60.txt` e `outputs_60.csv`.

12. **BLEU no teste original (suspeita de vazamento/duplicação)**

- **Epoch 40 — test (original)**: `results/eval_epoch40_bleu_test/bleu_epoch40.txt`
  - BLEU (SP-space, tokenize=none): **94.59**
  - BLEU (detok, tokenize=13a): **96.79**

- **Epoch 40 — train**: `results/eval_epoch40_bleu_train/bleu_epoch40.txt`
  - BLEU (SP-space): **95.92**
  - BLEU (detok): **97.57**

- **Epoch 36 — test (proxy)**: `results/eval_epoch36_bleu_test/bleu_epoch36_test.txt`
  - BLEU (SP-space): **94.14**
  - BLEU (detok): **96.48**

13. **Métrica de overlap do split original (evidência de vazamento)**

No dataset `data/asl_100k_canon_enonly_clean/` (comparando EN do `test` com EN do `train/valid`):

- `test.en` tem **8802** sentenças únicas.
- overlap `test` vs `train` (únicas): **400** → **4.54%**
- overlap `test` vs `valid` (únicas): **39** → **0.44%**
- overlap `test` vs (`train ∪ valid`) (únicas): **435** → **4.94%**

Isso explica por que o BLEU do `test` original ficou “alto demais” para um cenário realmente não-visto.

14. **Criação de teste realmente não-visto (unseen) e queda de BLEU**

- Criamos um `test_unseen` amostrado do corpus grande, removendo frases do treino/val.
- Avaliação (epoch 40): `results/eval_epoch40_bleu_unseen_test/bleu_epoch40_unseen_test.txt`
  - BLEU (SP-space): **58.61**
  - BLEU (detok): **45.07**

**Interpretação**: ao remover vazamento e aumentar a dificuldade/distribuição do teste, a métrica cai para um patamar mais realista de generalização.

15. **Novo unseen “super-filtrado” (EN-only + ASCII-only + canonicalização)**

- Objetivo: criar um teste a partir de `corpus_0001` que fosse:
  - EN-only (detecção de idioma),
  - sem caracteres estranhos (ASCII-only),
  - ASL canonicalizado,
  - e **sem overlap** com treino/val.

- Script: `asl_pipeline/scripts/make_unseen_test_from_corpus.py`
- Split gerado:
  - `data/asl_100k_canon_enonly_clean/test_unseen_enonly_ascii_canon.*`
- BLEU (epoch 40): `results/eval_epoch40_bleu_unseen_enonly_ascii_canon_test/bleu_epoch40_unseen_enonly_ascii_canon.txt`
  - BLEU (SP-space): **94.04**
  - BLEU (detok): **96.17**

**Nota importante para a apresentação**:
- Esse “unseen filtrado” é **mais “limpo”** (idioma/ASCII/canonicalização), mas pode acabar ficando **mais parecido** com o treino em termos de estilo e distribuição do corpus — por isso o BLEU volta a ficar alto.
- O `test_unseen` anterior (BLEU 45.07 detok) continua sendo o melhor “stress-test” de generalização.

## 3) Arquivos principais (o que cada um faz)

### Treino e compatibilidade

- `train_lightconv_asl_100k_canon_windows.ps1`
  - Script principal de treino no Windows (inclui resume automático via `checkpoint_last.pt`).
- `fairseq_compat_run.py`
  - Wrapper de compatibilidade para:
    - PyTorch 2.6+ (checkpoint load),
    - Windows checkpoint rename.

### Preparação/limpeza de dados

- `asl_pipeline/scripts/asl_prepare.py`
  - Prepara splits, treina SentencePiece, aplica SP e (opcionalmente) roda preprocess.
  - Inclui canonicalização do ASL (`canonicalize_asl_markers`).
- `asl_pipeline/scripts/filter_parallel_by_lang.py`
  - Filtra o corpus paralelo preservando alinhamento (EN-only) + corrige mojibake.
- `asl_pipeline/scripts/make_unseen_test_from_corpus.py`
  - Gera testes “unseen” garantindo disjunção de treino/val e (opcionalmente) aplica SP.

### Avaliação e resultados

- `results/eval_epoch40_simple60/`
  - Avaliação qualitative via `fairseq-interactive` com 60 frases.
- `results/eval_epoch40_bleu_test/` e `results/eval_epoch40_bleu_train/`
  - BLEU no test original e no train.
- `results/eval_epoch40_bleu_unseen_test/`
  - BLEU no teste unseen “difícil” (queda para patamar mais realista).

## 4) Como reproduzir (roteiro rápido)

> (Resumo de alto nível; os detalhes estão nos scripts.)

1. **Preparar dataset limpo**
   - Filtrar EN-only + consertar mojibake: `asl_pipeline/scripts/filter_parallel_by_lang.py`
   - Preparar splits + SentencePiece + canonicalização ASL: `asl_pipeline/scripts/asl_prepare.py`
   - Binarizar: `fairseq-preprocess` (gera `data-bin/...`)

2. **Treinar**
   - Rodar: `train_lightconv_asl_100k_canon_windows.ps1`
   - Checkpoints: em `D:\translation-pipeline-checkpoints\...\checkpoint_last.pt`

3. **Avaliar (interactive e BLEU)**
   - `fairseq-interactive` para exemplos qualitativos.
   - `fairseq-generate` + script de BLEU (em `results/eval_epoch40_bleu_test/compute_bleu_from_generate.py`).

## 5) Principais aprendizados

- **Dados mandam no resultado**: pequenas porcentagens de overlap train/test (~5%) podem inflar muito o BLEU.
- **Canonicalização no target** (ASL gloss) melhora a tokenização e reduz tokens “lixo” de pontuação.
- **Windows exige engenharia extra**: encoding, PowerShell/stderr e detalhes de filesystem podem quebrar checkpoints e avaliação.
- **Avaliar com múltiplos testes**: um `test` “limpo” e um `unseen` “difícil” ajudam a mostrar robustez + limites do modelo.
