# 🤖 RoverMind — Nano-Rabugento

> Um mini-GPT construído do zero que dá voz sarcástica e preguiçosa ao cérebro de
> um robô autônomo. Cada situação do robô vira uma frase com personalidade.

**nano-grump** é o "cérebro de linguagem" de um robô de dois cérebros: um corpo
(ESP32-WROOM-32) que navega e desvia de obstáculos, e um cérebro (ESP32-S3) que
comenta cada situação com o humor de quem preferia estar carregando a bateria.

Este repositório contém o **cérebro**: um modelo de linguagem de nível de
caractere, treinado do zero em PyTorch, construído peça por peça com finalidade
didática — entender cada camada de um Transformer, não apenas usá-lo.

```
<obstacle>   → "A barrier again. Alright."
<backup>     → "I walked right into that one. Retreating. Beep beep."
<explore>    → "Rolling along. I have no idea where I'm going."
<stuck>      → "I'm boxed in. This was absolutely intentional."
```

---

## 🎯 Para que serve

O robô físico detecta situações com seus sensores (obstáculo à frente, caminho
livre, preso num canto, etc.) e as representa por **marcadores**: `<obstacle>`,
`<clear>`, `<stuck>`… O nano-grump recebe um marcador e **gera uma frase** com a
personalidade do robô para aquela situação, que aparece no display e nos LEDs.

A separação é intencional:

```
        ROBÔ
          │
   ┌──────┴───────┐
   │              │
ESP32-WROOM    ESP32-S3
  CORPO         CÉREBRO
   │              │
sensores       nano-grump
motores        (linguagem)
navegação      personalidade
   │              │
   └──────┬───────┘
      comunicação
   (marcador → frase)
```

O corpo cuida de navegação e motores. O cérebro cuida de linguagem e
personalidade. A IA **não** controla os motores diretamente — ela apenas dá voz ao
que o robô está fazendo.

---

## 🧠 O que é o modelo

Um mini-GPT decoder-only, nível de caractere, montado do zero:

| Item | Valor |
|---|---|
| Parâmetros | 211.003 |
| Vocabulário | 59 caracteres |
| Contexto | 64 caracteres |
| Camadas | 4 blocos |
| Atenção | 4 cabeças (multi-head) |
| Embedding | 64 dimensões |
| Framework | PyTorch + CUDA |

O modelo aprende letra por letra a "falar como o robô". Todo o pipeline — do
tokenizer à geração — foi construído componente por componente, com demos
isolados para cada peça (embedding, posição, atenção, FFN, multi-cabeça).

Detalhes completos de arquitetura, treino e resultados estão em
[`MODEL_CARD.md`](MODEL_CARD.md).

---

## 📁 Estrutura do repositório

```
RoverMind-nanoGrump/
├── data/
│   └── robot_voice_final.txt   # dataset: 2491 frases com personalidade
├── tokenizer.py                # descobre o vocabulário → vocab.json
├── dataset_gen.py              # gera o dataset sintético por moldes
├── model.py                    # arquitetura do mini-GPT (multi-cabeça)
├── train.py                    # treino com val split + checkpoint
├── generate.py                 # geração com temperatura + top-k
├── vocab.json                  # vocabulário + metadados (gerado)
├── modelo_treinado.pt          # pesos treinados (gerado)
├── MODEL_CARD.md               # ficha técnica completa
│
├── 01_embedding_demo.py        # demos didáticos: cada peça isolada
├── 02_posicao_demo.py
├── 03_atencao_demo.py
├── 04_ffn_demo.py
└── 05_multihead_demo.py
```

---

## 🚀 Como executar

O projeto usa [`uv`](https://github.com/astral-sh/uv) para gerenciar o ambiente.

### Pré-requisitos

- Python ≥ 3.12
- `uv` instalado
- GPU NVIDIA com CUDA (opcional — roda em CPU, só mais devagar)

### Instalação

```bash
git clone https://github.com/<seu-usuario>/RoverMind-nanoGrump.git
cd RoverMind-nanoGrump
uv sync
```

O `uv sync` instala tudo do `pyproject.toml`, incluindo o PyTorch com CUDA.

### Pipeline completo

Rode nesta ordem. Cada passo depende do anterior.

**1. Gerar o dataset** (opcional — já vem pronto em `data/`)

```bash
uv run dataset_gen.py
```

Combina moldes e bancos de palavras para gerar ~2400 frases sintéticas
balanceadas por marcador.

**2. Construir o vocabulário**

```bash
uv run tokenizer.py
```

Descobre os 59 caracteres únicos do dataset e salva `vocab.json`.

**3. Treinar o modelo**

```bash
uv run train.py
```

Treina por 8000 passos com split treino/validação, salvando o melhor modelo em
`modelo_treinado.pt`. Na RTX 4050 leva poucos minutos.

**4. Fazer o robô falar**

```bash
uv run generate.py
```

Gera frases para cada marcador de situação. Esta é a saída final — o grump
falando.

### Explorar as peças (opcional)

Cada demo mostra uma peça do Transformer isoladamente, com números pequenos:

```bash
uv run 01_embedding_demo.py    # caractere → vetor
uv run 02_posicao_demo.py      # embedding de posição
uv run 03_atencao_demo.py      # self-attention (1 cabeça)
uv run 04_ffn_demo.py          # feed-forward
uv run 05_multihead_demo.py    # atenção multi-cabeça
```

---

## 🎛️ Ajustando a geração

Em `generate.py`, no topo, você pode mexer nos parâmetros:

```python
TEMPERATURA    = 0.75    # < 1 mais "certinho"; > 1 mais "criativo"
TOP_K          = 4       # quantos caracteres mais prováveis manter
N_POR_MARCADOR = 3       # quantas frases por marcador
```

A configuração padrão (`top_k=4`, `temp=0.75`) foi escolhida após comparar várias
combinações — é o equilíbrio entre frases limpas e variedade. Valores menores
deixam mais conservador (limpo, porém repetitivo); maiores deixam mais criativo
(variado, porém com mais palavras tortas).

---

## 🎭 Os 8 marcadores de situação

| Marcador | Situação | Energia |
|---|---|---|
| `<start>` | Ligou | Sonolento, relutante |
| `<explore>` | Explorando | Indiferente, filosófico |
| `<obstacle>` | Achou obstáculo | Irritado, sarcástico |
| `<turn_left>` | Virando à esquerda | Irônico sobre a decisão |
| `<turn_right>` | Virando à direita | Espelho do esquerdo |
| `<backup>` | Recuando | "Recuo estratégico" |
| `<stuck>` | Preso | Resignação existencial |
| `<clear>` | Caminho livre | Alívio irônico |

---

## 🗺️ Estado e próximos passos

**Versão atual: v2** — arquitetura multi-cabeça, dataset de 2491 frases, geração
com top-k. Modelo utilizável e demonstrável.

Próximos marcos:

1. **Refinar o dataset (v2.1)** — melhorar os marcadores `<clear>` e `<stuck>`,
   que ainda confundem vocabulário com `<obstacle>`.
2. **Embarcar no ESP32-S3** — exportar os pesos e rodar a inferência em C no
   hardware.
3. **Comunicação corpo ↔ cérebro** — o WROOM-32 envia o marcador, o S3 devolve a
   frase, exibida no display + LEDs.

---

## 📚 Filosofia do projeto

Este projeto segue um princípio: **entender antes de integrar**. Nada de caixas
pretas. Cada peça — tokenizer, embedding, atenção, FFN — foi construída e testada
isoladamente antes de virar parte do modelo. Os demos numerados são o registro
dessa jornada de aprendizado.

O objetivo não é só ter um robô que fala melhor — é entender, camada por camada,
como um Transformer aprende linguagem.

---

*nano-grump — um robô que preferiria estar carregando.* 🔋
