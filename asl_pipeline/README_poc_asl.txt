POC simples: treinar LightConv (Fairseq) com seu dataset EN -> ASL (glosas)

Objetivo
- Fluxo mínimo para treinar um modelo conv (LightConv se disponível) usando Fairseq e avaliar BLEU.

Dependências recomendadas (instalar num venv/conda):
- Python 3.8+
- pip install sentencepiece sacrebleu
- Fairseq + torch (seguir instruções do fairseq para a versão compatível): https://github.com/facebookresearch/fairseq
  Exemplo (pode variar por plataforma):
    pip install fairseq
    pip install torch

Passos rápidos (resumido)
1) Preparar os arquivos paralelos (um por linha):
   - Fonte (inglês): data/raw/all.en
   - Alvo (glosa ASL): data/raw/all.asl
   Alternativamente, combine em um TSV src\ttgt por linha: data/raw/all.tsv

2) Rodar o script de preparação para split + treinar e aplicar SentencePiece (vocab 8000 por padrão):

```bash
python asl_pipeline/scripts/asl_prepare.py --src-file data/raw/all.en --tgt-file data/raw/all.asl --outdir data/asl --vocab-size 8000 --seed 42 --run-fairseq-preprocess
```

Este script faz:
- Split train/valid/test (80/10/10)
- Treina SentencePiece (joint) e aplica aos splits
- (opcional) chama `fairseq-preprocess` para criar `data-bin/asl`

3) Treinar com fairseq (exemplo de comando):

```bash
# Se fairseq-preprocess foi executado e gerou data-bin/asl
fairseq-train data-bin/asl \
  --arch lightconv --encoder-layers 6 --decoder-layers 6 \
  --optimizer adam --lr 0.0005 --max-epoch 30 \
  --save-dir checkpoints/asl_lightconv \
  --patience 5 --adam-betas '(0.9,0.98)'
```

Notas:
- O `--arch lightconv` pressupõe que sua versão do fairseq contém a implementação `lightconv`. Se não, troque por `--arch transformer` com modelos pequenos (d_model=256).
- Ajuste batch-size/learning-rate conforme GPU/memória disponível.

4) Inferência (exemplo com fairseq-generate / fairseq-interactive):

```bash
# gerar em modo batch
fairseq-generate data-bin/asl --path checkpoints/asl_lightconv/checkpoint_best.pt --batch-size 32 --beam 5 --remove-bpe
```

Se você usou SentencePiece com BPE, ao gerar pode precisar remover os tokens de subword (por exemplo, usando o processor do sentencepiece para decodificar).

5) Avaliar BLEU usando `asl_pipeline/scripts/eval_bleu.py` (usa sacrebleu):

```bash
# suponha que você tenha escrito as hipoteses em out.hyp (uma sentença por linha)
python asl_pipeline/scripts/eval_bleu.py --sys out.hyp --ref data/asl/test.asl
```

Dicas e problemas comuns
- Se o fairseq não reconhecer `lightconv`, treine com `transformer` para um caminho mais padrão.
- 5.000 sentenças é pouco — aumente com augmentation/backtranslation se possível.
- Padronize convenções de gloss (CAPS, separadores) antes do treino para consistência.

Próximos passos sugeridos
- Criar um pequeno pipeline JSON em `data/pipelines/` que automatize esses comandos.
- Fazer fine-tuning com transferência se houver um modelo-base compatível.
- Automatizar a decodificação do SentencePiece (separar tokens) durante inferência.

Se quiser, eu posso:
- Gerar o pipeline JSON mínimo para `data/pipelines/asl_mvp.json`.
- Adaptar o script para automaticamente executar `fairseq-train` (se fairseq estiver instalado) e capturar saída de checkpoints.
