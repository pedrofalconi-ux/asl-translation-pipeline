# Entendendo a pipeline de tradução do projeto VLibras e como adaptar para uma POC Inglês → ASL

## Objetivo deste documento

Este documento explica:

1. como este repositório organiza a pipeline de tradução;
2. onde o modelo LightConv entra;
3. onde existe tradução por regras;
4. como o dataset atual é consumido;
5. como trocar o dataset atual por um dataset paralelo Inglês → ASL para uma POC;
6. quais partes do pipeline atual provavelmente **não** servem para Inglês → ASL sem adaptação.

---

## Resumo executivo

A ideia principal do repositório é esta:

- uma pipeline é definida em JSON, por exemplo em [translation_pipeline/data/pipelines/train.json](../translation_pipeline/data/pipelines/train.json) e [translation_pipeline/data/pipelines/test.json](../translation_pipeline/data/pipelines/test.json);
- o executor lê esse JSON, instancia cada elemento e passa os dados de um passo para o outro;
- os artefatos intermediários e finais ficam em `artifacts/<hash>`;
- a pipeline atual do VLibras **não treina diretamente Português → GI**;
- ela primeiro gera uma representação intermediária por **regras** (`translate`), produzindo `GR`, e depois treina um modelo **GR → GI** com Fairseq;
- o modelo padrão configurado é **LightConv** via Fairseq.

Para uma POC de **Inglês → ASL**, o caminho mais simples é:

- **não usar** `translate`;
- **não usar** as augmentations atuais;
- provavelmente **não usar** `preprocess` e `cleanup` do jeito atual;
- treinar direto com `csvsrc -> split -> parallel_filedest -> learn_bpe -> apply_bpe -> binarize -> train`.

Se o seu lado ASL for **texto/glossas**, isso é viável com poucas mudanças de configuração.
Se o seu lado ASL for **vídeo, pose, avatar script ou markup não textual**, então esta pipeline não cobre o problema completo.

---

## 1. Como a pipeline é executada

### 1.1 Ponto de entrada

A entrada principal está em [translation_pipeline/src/cli.py](../translation_pipeline/src/cli.py#L15-L89).

- `execute()` executa uma pipeline em memória;
- `main()` aceita argumentos de linha de comando;
- o CLI substitui os placeholders `CORPUS_PATH` e `TRAIN_HASH` no JSON.

Observação importante: o placeholder `COMMIT_HASH` aparece em [translation_pipeline/data/pipelines/train.json](../translation_pipeline/data/pipelines/train.json#L2), mas **não** é substituído automaticamente em [translation_pipeline/src/cli.py](../translation_pipeline/src/cli.py#L84-L85). Ou seja, do jeito que está, esse valor precisa ser preenchido manualmente antes de executar a pipeline de treino atual.

### 1.2 Como o JSON vira um grafo de execução

A classe central está em [translation_pipeline/src/pipeline.py](../translation_pipeline/src/pipeline.py#L15-L154).

Ela faz 3 coisas principais:

1. faz o parse da lista JSON em [translation_pipeline/src/pipeline.py](../translation_pipeline/src/pipeline.py#L110-L114);
2. instancia os elementos da pipeline em [translation_pipeline/src/pipeline.py](../translation_pipeline/src/pipeline.py#L115-L127);
3. processa os elementos encadeados em [translation_pipeline/src/pipeline.py](../translation_pipeline/src/pipeline.py#L147-L154).

Bifurcações como `train` e `valid` são suportadas pelo parser. Isso é exatamente o que acontece no `split` do treino.

### 1.3 Registro dos elementos

Os elementos são registrados em [translation_pipeline/src/registry.py](../translation_pipeline/src/registry.py) e instanciados por meio do `ElementStub` em [translation_pipeline/src/element_stub.py](../translation_pipeline/src/element_stub.py).

O `ElementStub` também cuida de:

- cache por elemento;
- encadeamento entre passos;
- bifurcação de saída.

Veja [translation_pipeline/src/element_stub.py](../translation_pipeline/src/element_stub.py#L23-L88).

### 1.4 Artefatos e cache

Os artefatos temporários são escritos em `artifacts/tmp` e depois renomeados para um hash final.

Isso está em [translation_pipeline/src/artifact.py](../translation_pipeline/src/artifact.py#L20-L52).

Na prática, cada execução gera uma pasta versionada, o que é útil para:

- reaproveitar BPE e binários;
- guardar checkpoints;
- guardar resultados de teste;
- referenciar um treino anterior por `TRAIN_HASH`.

---

## 2. Como a pipeline atual do VLibras funciona

## 2.1 Pipeline de treino atual

A definição está em [translation_pipeline/data/pipelines/train.json](../translation_pipeline/data/pipelines/train.json#L2-L25).

Fluxo atual, simplificado:

1. `gitsrc commit=COMMIT_HASH`
2. `translate`
3. `cleanup`
4. `preprocess ...`
5. `split shuffle,val_percentage=.3`
6. branch `train`
   - `counter`
   - augmentations
   - `parallel_filedest train.gr/train.gi`
7. branch `valid`
   - `parallel_filedest valid.gr/valid.gi`
8. `learn_bpe`
9. `apply_bpe`
10. `binarize`
11. `train`

### 2.1.1 Origem do dataset de treino atual

O treino atual **não** usa o `-c/--corpus` do CLI.
Ele começa com `gitsrc`, definido em [translation_pipeline/src/elements/gitsrc.py](../translation_pipeline/src/elements/gitsrc.py#L11-L56).

Esse elemento:

- clona/faz fetch de um repositório remoto de corpus;
- faz checkout de um commit específico;
- lê `corpus.csv`;
- devolve as duas primeiras colunas de cada linha.

O remoto default está em [translation_pipeline/src/elements/gitsrc.py](../translation_pipeline/src/elements/gitsrc.py#L27-L30).

### 2.1.2 O que entra e sai do `translate`

O passo `translate` está em [translation_pipeline/src/elements/translate.py](../translation_pipeline/src/elements/translate.py#L13-L141).

Ele faz isto:

- recebe pares `(PT, GI)`;
- chama `rule_translation(pt)` em [translation_pipeline/src/elements/translate.py](../translation_pipeline/src/elements/translate.py#L54);
- devolve `(GR, GI)`.

Ou seja:

- `PT` = texto fonte original do corpus atual;
- `GR` = uma representação gerada por regras;
- `GI` = alvo ouro do treinamento.

**Conclusão importante:** o modelo neural padrão desta pipeline aprende **GR → GI**, não **PT → GI**.

### 2.1.3 Limpeza e pré-processamento

Depois da tradução por regras, entram `cleanup` e `preprocess`.

#### `cleanup`

Arquivo: [translation_pipeline/src/elements/cleanup.py](../translation_pipeline/src/elements/cleanup.py#L12-L129)

Ele corrige coisas específicas do domínio atual, por exemplo:

- `VÍRGULA`;
- `FUTURO` / `PASSADO`;
- marcadores de pontuação como `[PONTO]`, `[INTERROGAÇÃO]`, `[EXCLAMAÇÃO]`;
- normalização de espaços e intensificadores.

#### `preprocess`

Arquivo: [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L13-L189)

As transformações configuráveis incluem:

- `replace_context_markers` em [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L54-L71);
- `move_intensifiers_to_the_right` em [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L73-L75);
- `replace_directionality_syntax` em [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L77-L83);
- `spell_out_numbers` em [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L85-L89);
- `parse_every_spelled_number` em [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L115-L133).

Boa parte disso é claramente orientada ao ecossistema VLibras e ao português.

### 2.1.4 Split, escrita paralela, BPE e treino

Os próximos passos são mais genéricos:

- `split` separa treino e validação em [translation_pipeline/src/elements/split.py](../translation_pipeline/src/elements/split.py#L8-L64);
- `parallel_filedest` grava os pares paralelos em [translation_pipeline/src/elements/parallel_filedest.py](../translation_pipeline/src/elements/parallel_filedest.py#L8-L39);
- `learn_bpe` aprende BPE em [translation_pipeline/src/elements/learn_bpe.py](../translation_pipeline/src/elements/learn_bpe.py#L10-L91);
- `apply_bpe` aplica BPE em [translation_pipeline/src/elements/apply_bpe.py](../translation_pipeline/src/elements/apply_bpe.py#L13-L111);
- `binarize` chama `fairseq-preprocess` em [translation_pipeline/src/elements/fairseq_binarize.py](../translation_pipeline/src/elements/fairseq_binarize.py#L13-L46);
- `train` chama `fairseq-train` em [translation_pipeline/src/elements/fairseq_train.py](../translation_pipeline/src/elements/fairseq_train.py#L13-L68).

---

## 2.2 Pipeline de teste atual

A definição está em [translation_pipeline/data/pipelines/test.json](../translation_pipeline/data/pipelines/test.json#L2-L9).

Fluxo atual:

1. `csvsrc path=CORPUS_PATH`
2. `translate`
3. `cleanup`
4. `preprocess ...`
5. `parallel_filedest test.gr/test.gi`
6. `apply_bpe train_hash=TRAIN_HASH`
7. `interactive_score ...`
8. `results corpus_file=CORPUS_PATH`

### 2.2.1 Leitura do CSV de teste

O `csvsrc` está em [translation_pipeline/src/elements/csvsrc.py](../translation_pipeline/src/elements/csvsrc.py#L7-L43).

Ele simplesmente:

- lê o CSV informado;
- pega as 2 primeiras colunas;
- retorna uma lista de pares.

### 2.2.2 Inferência Fairseq

`interactive_score` está em [translation_pipeline/src/elements/fairseq_interactive.py](../translation_pipeline/src/elements/fairseq_interactive.py#L11-L87).

Ele:

- reutiliza o `TRAIN_HASH` para localizar BPE, binários e checkpoint;
- chama `fairseq-interactive` em [translation_pipeline/src/elements/fairseq_interactive.py](../translation_pipeline/src/elements/fairseq_interactive.py#L66-L68);
- extrai hipóteses e calcula BLEU com `fairseq-score` em [translation_pipeline/src/elements/fairseq_interactive.py](../translation_pipeline/src/elements/fairseq_interactive.py#L83-L85).

### 2.2.3 Relatório final

`results` está em [translation_pipeline/src/elements/results.py](../translation_pipeline/src/elements/results.py#L12-L142).

Ele:

- monta um CSV com PT, GR, GI ouro e GI gerado;
- usa `sacrebleu` e `meteor` em [translation_pipeline/src/elements/results.py](../translation_pipeline/src/elements/results.py#L39-L40) e [translation_pipeline/src/elements/results.py](../translation_pipeline/src/elements/results.py#L129-L138);
- aplica `postprocess` do submódulo VLibras em [translation_pipeline/src/elements/results.py](../translation_pipeline/src/elements/results.py#L45-L47).

---

## 3. O que é o LightConv

## 3.1 Conceito

LightConv = **Lightweight Convolution**, uma arquitetura seq2seq baseada em convoluções leves, popularizada no trabalho *Pay Less Attention with Lightweight and Dynamic Convolutions*.

Na prática, dentro do Fairseq, é um modelo encoder-decoder que usa camadas convolucionais leves em vez de depender apenas de self-attention.

## 3.2 Onde o LightConv está neste repositório

Dentro deste repositório, o nome `lightconv` aparece apenas em [translation_pipeline/data/fairseq-params/train_parameters_default.json](../translation_pipeline/data/fairseq-params/train_parameters_default.json#L3):

- `"--arch": "lightconv_iwslt_de_en"`

Também aparecem hiperparâmetros compatíveis com essa arquitetura, por exemplo:

- número de camadas em [translation_pipeline/data/fairseq-params/train_parameters_default.json](../translation_pipeline/data/fairseq-params/train_parameters_default.json#L26-L27);
- kernels do encoder/decoder em [translation_pipeline/data/fairseq-params/train_parameters_default.json](../translation_pipeline/data/fairseq-params/train_parameters_default.json#L37-L38).

## 3.3 Onde o código do LightConv realmente está

O código **não está neste repositório**.
Ele vem do pacote `fairseq`, listado em [requirements.txt](../requirements.txt#L1).

Este repositório apenas monta a linha de comando `fairseq-train` em [translation_pipeline/src/elements/fairseq_train.py](../translation_pipeline/src/elements/fairseq_train.py#L60-L68) e passa o JSON de parâmetros.

No código do Fairseq, a implementação do LightConv fica no módulo `fairseq.models.lightconv`.
A arquitetura nomeada `lightconv_iwslt_de_en` também é registrada lá.

Em outras palavras:

- **neste repositório**: LightConv aparece como configuração;
- **no Fairseq**: LightConv é a implementação do modelo.

---

## 4. Onde existe tradução por regras

A parte principal de tradução por regras está em [translation_pipeline/src/elements/translate.py](../translation_pipeline/src/elements/translate.py#L13-L141).

O ponto crítico é [translation_pipeline/src/elements/translate.py](../translation_pipeline/src/elements/translate.py#L54), que chama:

- `tr_instance.rule_translation(pt)`

Essa instância vem do submódulo `vlibras-translate`, carregado via [translation_pipeline/src/utils.py](../translation_pipeline/src/utils.py#L28-L44).

Além disso, há várias regras indiretas em:

- [translation_pipeline/src/elements/cleanup.py](../translation_pipeline/src/elements/cleanup.py#L12-L129)
- [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L13-L189)
- augmentations em [translation_pipeline/src/elements](../translation_pipeline/src/elements)

Ou seja, o repositório mistura:

1. **regras linguísticas / normalização**;
2. **geração de pares adicionais (augmentation)**;
3. **treino neural**.

---

## 5. Quais partes são específicas do VLibras / Português

Para uma POC Inglês → ASL, estas partes estão fortemente acopladas ao domínio atual.

### 5.1 `translate`

Arquivo: [translation_pipeline/src/elements/translate.py](../translation_pipeline/src/elements/translate.py#L13-L141)

É específico porque depende de `rule_translation()` do projeto VLibras.

**Para Inglês → ASL, a recomendação é remover este passo da pipeline.**

### 5.2 `cleanup`

Arquivo: [translation_pipeline/src/elements/cleanup.py](../translation_pipeline/src/elements/cleanup.py#L12-L129)

É específico porque mexe com tokens como:

- `VÍRGULA`;
- `FUTURO`;
- `PASSADO`;
- `[PONTO]`, `[INTERROGAÇÃO]`, `[EXCLAMAÇÃO]`.

**Para Inglês → ASL, eu não usaria esse passo sem revisar linha por linha.**

### 5.3 `preprocess`

Arquivo: [translation_pipeline/src/elements/preprocess.py](../translation_pipeline/src/elements/preprocess.py#L13-L189)

É específico porque lida com:

- homônimos do português;
- marcadores de contexto do VLibras;
- sintaxe de directionalidade do conjunto atual;
- conversão de números por biblioteca do submódulo VLibras.

**Para Inglês → ASL, eu desabilitaria esse passo inicialmente.**

### 5.4 Augmentations

A pipeline atual usa várias augmentations no branch de treino:

- directionalidade em [translation_pipeline/src/elements/augmentation_directionality.py](../translation_pipeline/src/elements/augmentation_directionality.py#L22-L276)
- intensidade em [translation_pipeline/src/elements/augmentation_intensity.py](../translation_pipeline/src/elements/augmentation_intensity.py#L28-L155)
- lugares em [translation_pipeline/src/elements/augmentation_places.py](../translation_pipeline/src/elements/augmentation_places.py#L18-L271)
- negação em [translation_pipeline/src/elements/augmentation_negation.py](../translation_pipeline/src/elements/augmentation_negation.py#L18-L343)
- famosos em [translation_pipeline/src/elements/augmentation_famosos.py](../translation_pipeline/src/elements/augmentation_famosos.py#L13-L108)

Esses módulos são muito ligados a padrões como:

- pronomes do português em [translation_pipeline/src/elements/augmentation_directionality.py](../translation_pipeline/src/elements/augmentation_directionality.py#L46-L59);
- intensificadores do português em [translation_pipeline/src/elements/augmentation_intensity.py](../translation_pipeline/src/elements/augmentation_intensity.py#L31-L54);
- marcadores `&PAÍS`, `&ESTADO`, `&CIDADE` em [translation_pipeline/src/elements/augmentation_places.py](../translation_pipeline/src/elements/augmentation_places.py#L65-L76) e [translation_pipeline/src/elements/augmentation_places.py](../translation_pipeline/src/elements/augmentation_places.py#L204-L217);
- negação com `NÃO_` em [translation_pipeline/src/elements/augmentation_negation.py](../translation_pipeline/src/elements/augmentation_negation.py#L123-L177);
- nomes com `&FAMOSO` em [translation_pipeline/src/elements/augmentation_famosos.py](../translation_pipeline/src/elements/augmentation_famosos.py#L87-L105).

**Para Inglês → ASL, eu removeria todas essas augmentations na primeira POC.**

### 5.5 Relatório `results`

Arquivo: [translation_pipeline/src/elements/results.py](../translation_pipeline/src/elements/results.py#L12-L142)

Esse relatório assume o universo atual porque:

- rotula colunas como `PT`, `GR` e `GI`;
- usa `postprocess` do submódulo VLibras.

Para a POC, ele pode até funcionar parcialmente, mas os nomes e o pós-processamento não são ideais.

---

## 6. Como substituir o dataset atual pelo seu dataset Inglês → ASL

## 6.1 O ponto mais importante

Hoje o treino oficial usa `gitsrc` e busca um corpus remoto.

Se você quer usar **o seu dataset local**, o ideal é **não editar o fluxo atual do VLibras** logo de cara.
Em vez disso, crie uma **pipeline nova**, paralela à atual, usando `csvsrc`.

## 6.2 Formato mínimo esperado do dataset

O elemento [translation_pipeline/src/elements/csvsrc.py](../translation_pipeline/src/elements/csvsrc.py#L7-L43) lê apenas as **duas primeiras colunas**.

Então o seu CSV deve ser, no mínimo:

- coluna 1 = sentença em inglês;
- coluna 2 = sentença alvo em ASL textual/gloss.

Exemplo:

```csv
I like pizza,I LIKE PIZZA
She is going home,SHE GO HOME
Can you help me,YOU HELP ME CAN
```

Recomendação prática:

- use **sem cabeçalho** na primeira POC;
- garanta UTF-8;
- garanta que a coluna 2 seja realmente texto, não vídeo ou JSON complexo.

## 6.3 Pipeline mínima recomendada para treino Inglês → ASL

Sugestão de JSON para uma POC simples:

```json
[
  "csvsrc path=CORPUS_PATH",
  "split shuffle,val_percentage=.1",
  {
    "train": [
      "parallel_filedest gr_path=Preprocessed/train.gr,gi_path=Preprocessed/train.gi"
    ],
    "valid": [
      "parallel_filedest gr_path=Preprocessed/valid.gr,gi_path=Preprocessed/valid.gi"
    ]
  },
  "learn_bpe bpe_tokens=4000",
  "apply_bpe",
  "binarize",
  "train parameters=data/fairseq-params/train_parameters_default.json"
]
```

### Por que isso funciona mesmo usando nomes `gr` e `gi`

Porque, nesta pipeline, `gr` e `gi` são apenas **rótulos de arquivo/extensão**.

Você pode reinterpretar assim:

- `gr` = **source** (agora inglês)
- `gi` = **target** (agora ASL)

Não é bonito semanticamente, mas para uma POC é o caminho com menos alterações de código.

## 6.4 Pipeline mínima recomendada para teste Inglês → ASL

```json
[
  "csvsrc path=CORPUS_PATH",
  "parallel_filedest gr_path=Preprocessed/test.gr,gi_path=Preprocessed/test.gi",
  "apply_bpe train_hash=TRAIN_HASH",
  "interactive_score train_hash=TRAIN_HASH,parameters=data/fairseq-params/test_parameters_default.json"
]
```

Eu **não incluiria `results`** na primeira POC, porque ele ainda está muito acoplado a PT/GR/GI e ao pós-processamento do VLibras.

## 6.5 O que mudar no dataset atual

Em termos práticos, para usar seu dataset:

1. salve o CSV paralelo inglês → ASL em algum caminho local;
2. use uma pipeline iniciando com `csvsrc path=CORPUS_PATH`;
3. remova `gitsrc`;
4. remova `translate`;
5. remova `cleanup`;
6. remova `preprocess`;
7. remova as augmentations;
8. mantenha `split`, `parallel_filedest`, `learn_bpe`, `apply_bpe`, `binarize` e `train`.

---

## 7. O que você provavelmente precisa mudar por regras

## 7.1 Se você quer só uma POC neural texto → texto

Se o seu alvo ASL estiver em forma de gloss textual, **você pode não precisar de regra nenhuma** no início.

Nesse cenário, use apenas:

- leitura do CSV;
- split;
- BPE;
- binarização;
- treino LightConv.

## 7.2 Se você quer preservar uma camada simbólica intermediária

A pipeline atual foi desenhada em torno da ideia:

- entrada linguística original → `translate` por regras → representação intermediária → modelo neural.

Se você quiser algo análogo para Inglês → ASL, teria que criar um novo `translate` que faça algo como:

- English → representação intermediária ASL-like

Mas isso **já é um novo projeto linguístico**, não só troca de dataset.

## 7.3 Se o seu lado ASL usa convenções diferentes

Exemplos de convenções que quebram a pipeline atual:

- negação sem `NÃO_`;
- ausência de marcadores como `&CIDADE` ou `&FAMOSO`;
- ordem sintática diferente da esperada em `preprocess`;
- ausência dos tokens especiais usados em `cleanup`.

Nesses casos, as regras atuais não ajudam; elas atrapalham.

---

## 8. LightConv para a sua POC: manter ou trocar?

## 8.1 Manter LightConv

Para uma POC rápida, faz sentido manter o arquivo de parâmetros atual em [translation_pipeline/data/fairseq-params/train_parameters_default.json](../translation_pipeline/data/fairseq-params/train_parameters_default.json).

Motivos:

- já está integrado ao fluxo de treino;
- exige pouca mudança no código;
- resolve seu objetivo de validar a troca de dataset.

## 8.2 Quando trocar depois

Você pode revisar depois:

- `--arch`
- dimensões de embedding;
- número de camadas;
- `max-tokens`;
- `dropout`;
- beam size em [translation_pipeline/data/fairseq-params/test_parameters_default.json](../translation_pipeline/data/fairseq-params/test_parameters_default.json#L2-L4).

Para a primeira POC, eu não mexeria nisso antes de validar que:

1. o dataset entra corretamente;
2. o treino roda de ponta a ponta;
3. a inferência gera saídas coerentes.

---

## 9. Existe alternativa com Hugging Face / Transformers?

Sim. O repositório também tem um caminho alternativo com Transformers, por exemplo:

- [translation_pipeline/src/elements/transformers_train.py](../translation_pipeline/src/elements/transformers_train.py)
- [translation_pipeline/src/elements/transformers_results.py](../translation_pipeline/src/elements/transformers_results.py)
- parâmetros em [translation_pipeline/data/huggingface-params](../translation_pipeline/data/huggingface-params)

Mas esse caminho está mais acoplado ao domínio atual do que parece, porque ainda usa:

- chaves `pt` e `gi` em [translation_pipeline/src/elements/convert_to_jsonl.py](../translation_pipeline/src/elements/convert_to_jsonl.py#L13);
- `source_lang = pt` e `target_lang = gi` em [translation_pipeline/data/huggingface-params/bart.json](../translation_pipeline/data/huggingface-params/bart.json#L7-L9), [translation_pipeline/data/huggingface-params/t5-small.json](../translation_pipeline/data/huggingface-params/t5-small.json#L6-L8) e [translation_pipeline/data/huggingface-params/byt5.json](../translation_pipeline/data/huggingface-params/byt5.json#L6-L8);
- prefixo `translate Portuguese to Gloss` em [translation_pipeline/src/elements/transformers_results.py](../translation_pipeline/src/elements/transformers_results.py#L59).

**Conclusão:** para a sua POC, o caminho Fairseq/LightConv é mais direto do que o caminho Transformers.

---

## 10. Observações importantes sobre Windows

Seu ambiente atual é Windows, mas o repositório tem sinais claros de foco em Linux:

- classificação POSIX/Linux em [setup.py](../setup.py#L29);
- o `learn_bpe` usa `cat` em [translation_pipeline/src/elements/learn_bpe.py](../translation_pipeline/src/elements/learn_bpe.py#L81);
- o `apply_bpe` usa `os.symlink` várias vezes em [translation_pipeline/src/elements/apply_bpe.py](../translation_pipeline/src/elements/apply_bpe.py#L62-L84).

Então, para rodar a POC com menos dor, a recomendação prática é:

- usar Linux ou WSL2;
- evitar rodar treino completo no Windows puro.

---

## 11. Plano de ação recomendado para a sua task

### Opção recomendada: POC mínima e segura

1. preparar um CSV paralelo Inglês → ASL textual;
2. criar uma nova pipeline de treino baseada em `csvsrc`;
3. remover todos os passos específicos do VLibras (`translate`, `cleanup`, `preprocess`, augmentations);
4. manter o treino Fairseq com LightConv;
5. rodar treino;
6. pegar o hash do artefato;
7. rodar teste com uma pipeline mínima;
8. só depois decidir se vale adaptar regras e relatórios.

### O que eu faria primeiro, sem complicar

- **Treino:** `csvsrc -> split -> parallel_filedest -> learn_bpe -> apply_bpe -> binarize -> train`
- **Teste:** `csvsrc -> parallel_filedest -> apply_bpe(train_hash) -> interactive_score`

---

## 12. Resposta direta às suas perguntas

### “O que é o LightConv?”

É a arquitetura neural seq2seq usada no treino Fairseq desta pipeline.
Neste repositório ela aparece como configuração em [translation_pipeline/data/fairseq-params/train_parameters_default.json](../translation_pipeline/data/fairseq-params/train_parameters_default.json#L3), mas a implementação real está no pacote `fairseq`.

### “Onde ele está?”

- no repositório: só na configuração de treino;
- no código real do modelo: dentro do Fairseq, fora deste repositório.

### “Como eu troco o dataset atual pelo meu dataset?”

Não reutilize o `gitsrc` do treino atual.
Crie uma pipeline nova começando com `csvsrc path=CORPUS_PATH` e alimente seu CSV paralelo.

### “Tem parte de tradução por regras que eu preciso mudar?”

Se a sua POC for Inglês → ASL textual, o mais seguro é **não usar nenhuma das regras atuais** no começo.
A principal regra está em `translate`, e ela é específica do VLibras.

### “O que eu realmente preciso mexer para começar?”

O mínimo:

- trocar a origem de dados para `csvsrc`;
- remover `translate`;
- remover `cleanup`;
- remover `preprocess`;
- remover augmentations;
- manter apenas o pipeline neural.

---

## Conclusão

Este repositório não é apenas um “trainer de tradução”.
Ele foi montado para o fluxo específico do VLibras, com:

- coleta de corpus por git;
- tradução intermediária por regras;
- normalizações específicas do domínio;
- augmentations linguísticas específicas;
- treino neural Fairseq.

Por isso, para uma POC de **Inglês → ASL**, a melhor estratégia é **simplificar**.

Em vez de adaptar todo o ecossistema VLibras de uma vez, use só o miolo realmente genérico:

- leitura de CSV paralelo;
- split;
- BPE;
- binarização;
- treino LightConv;
- inferência Fairseq.

Isso reduz muito o risco e te permite validar rapidamente se o seu dataset paralelo já sustenta uma prova de conceito.
