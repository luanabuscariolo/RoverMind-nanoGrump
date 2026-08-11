# Model Card — nano-grump

Um modelo de linguagem minúsculo, construído e treinado do zero, que dá voz a
um robô autônomo de personalidade sarcástica, preguiçosa e engraçada. Projetado
para rodar embarcado em um microcontrolador **ESP32-S3**.

---

## Visão geral

| | |
|---|---|
| **Nome** | nano-grump |
| **Tipo** | GPT decoder-only (autorregressivo) |
| **Tarefa** | Gerar frases curtas em inglês conforme a situação do robô |
| **Idioma** | Inglês |
| **Personalidade** | Sarcástico, preguiçoso, com humor seco |
| **Alvo de execução** | ESP32-S3 (inferência em C) |
| **Status** | Protótipo funcional |

---

## Arquitetura

| Item | Valor | Descrição |
|---|---|---|
| Tipo | GPT decoder-only | Gera um token por vez, olhando só o passado (máscara causal) |
| Tokenização | Nível de caractere | Cada token é um único caractere |
| `vocab_size` | 59 | Caracteres únicos do dataset |
| `n_embd` | 32 | Dimensão do embedding (tamanho do vetor de cada token) |
| `block_size` | 32 | Janela de contexto (máximo de caracteres olhados por vez) |
| `n_layer` | 3 | Blocos de atenção + FFN empilhados |
| Cabeças de atenção | 1 | Self-attention single-head |
| Normalização | LayerNorm (pre-norm) | Aplicada antes de cada sub-camada |
| Conexões residuais | Sim | Atalhos que preservam o sinal ao longo da profundidade |
| FFN | 32 → 128 → 32, ReLU | Expansão 4× com ativação ReLU |
| **Parâmetros treináveis** | **~42.700** | Tamanho total do modelo |

## Treino

| Item | Valor |
|---|---|
| Framework | PyTorch (CUDA) |
| Otimizador | AdamW |
| Taxa de aprendizado | 1e-3 |
| Função de perda | Cross-entropy |
| `batch_size` | 32 |
| Passos | 3.000 |
| Erro final (loss) | ~0,70 |
| Hardware | NVIDIA RTX 4050 Laptop GPU (6 GB) |

## Dataset

| Item | Valor |
|---|---|
| Conteúdo | Frases sarcásticas de robô, em inglês |
| Situações (marcadores) | 8: `<start>`, `<explore>`, `<obstacle>`, `<turn_left>`, `<turn_right>`, `<backup>`, `<stuck>`, `<clear>` |
| Nº de frases | 91 |
| Tamanho | ~5.972 caracteres |
| Formato | Uma frase por linha: `<marcador> frase` |

---

## Como funciona

O robô (ESP32 WROOM-32) detecta uma situação com seus sensores e envia o
**marcador** correspondente ao cérebro (ESP32-S3). O modelo recebe o marcador
como contexto inicial e **gera uma frase**, um caractere de cada vez
(geração autorregressiva com amostragem), até uma quebra de linha.

```
<obstacle>  →  "Oh look, a wall. Groundbreaking discovery. Turning."
```

---

## Limitações conhecidas

Todas as escolhas abaixo foram **deliberadas** para o modelo caber e rodar em um
microcontrolador. São trade-offs de engenharia, não defeitos.

- **Tamanho minúsculo (~42 mil parâmetros).** Para comparação, o GPT-2 menor tem
  124 milhões. A capacidade limitada causa erros ocasionais de grafia
  ("palavras tortas").
- **Nível de caractere.** O modelo soletra letra por letra; forma palavras
  corretas com menos confiança do que um modelo em nível de palavra.
- **Contexto curto (32 caracteres).** Frases longas podem perder o começo.
- **Dataset pequeno (91 frases).** Pouca variedade limita a generalização —
  a principal causa dos erros de grafia.
- **Raso (3 blocos, 1 cabeça).** Propositalmente simples para caber no ESP32-S3.

## Melhorias possíveis

- Expandir o dataset (mais frases e mais variadas) — maior alavanca de qualidade.
- Treinar por mais passos.
- Aumentar levemente a capacidade (`n_embd`, `n_layer`), respeitando o limite do chip.

---

## Resumo em uma frase

> GPT decoder-only de nível de caractere, treinado do zero: ~42 mil parâmetros,
> 3 blocos, embedding de dimensão 32, contexto de 32, vocabulário de 59.
> Treinado em PyTorch (AdamW, cross-entropy) sobre um dataset próprio de frases
> sarcásticas. Deliberadamente minúsculo para rodar em um ESP32-S3.
