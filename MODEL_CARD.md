# Model Card — nano-grump v2

Um mini-GPT de nível de caractere, treinado do zero, que dá voz sarcástica e
preguiçosa a um robô autônomo. Cada situação do robô (início, exploração,
obstáculo, curvas, recuo, preso, caminho livre) recebe uma frase gerada com
personalidade.

Este cartão descreve a **versão 2** do modelo. A v1 foi a primeira prova de
conceito; a v2 aumenta a arquitetura, expande o dataset e melhora a geração.

---

## Resumo rápido

| Item | Valor |
|---|---|
| Tipo | mini-GPT decoder-only, nível de caractere |
| Parâmetros treináveis | 211.003 |
| Vocabulário | 59 caracteres |
| Contexto (block_size) | 64 caracteres |
| Camadas (blocos) | 4 |
| Cabeças de atenção | 4 (multi-head) |
| Dimensão do embedding | 64 |
| Dataset | 2.491 frases (~143 mil caracteres) |
| Framework | PyTorch 2.13.0 + CUDA |
| Hardware de treino | RTX 4050 Laptop (6 GB) |

---

## Arquitetura

Decoder-only no estilo GPT, montado peça por peça a partir de demos didáticos:

```
entrada (caracteres)
      ↓
embedding de token (59 → 64)  +  embedding de posição (64 → 64)
      ↓
4 blocos, cada um com:
   ├─ LayerNorm → Atenção multi-cabeça (4 cabeças) → resíduo
   └─ LayerNorm → FFN (64 → 256 → 64, ReLU)        → resíduo
      ↓
LayerNorm final
      ↓
camada linear de saída (64 → 59)
      ↓
logits (uma nota por caractere possível)
```

### Diferenças em relação à v1

| Parâmetro | v1 | v2 |
|---|---|---|
| Dimensão do embedding (n_embd) | 32 | 64 |
| Contexto (block_size) | 32 | 64 |
| Blocos (n_layer) | 3 | 4 |
| Cabeças de atenção (n_heads) | 1 | 4 |
| Parâmetros | ~42.700 | 211.003 |
| vocab_size | fixo (59) | lido do vocab.json |

A mudança de arquitetura mais significativa foi a **atenção multi-cabeça**: em vez
de uma única atenção sobre o vetor inteiro, o modelo divide os 64 números em 4
fatias de 16, roda uma atenção independente em cada fatia e concatena os
resultados — ganhando múltiplas perspectivas sobre as relações entre caracteres
pelo mesmo custo computacional.

---

## Tokenizer

Tokenizer de nível de caractere. O vocabulário (59 símbolos: letras, dígitos de
pontuação, espaço, quebra de linha e os caracteres dos marcadores `<`, `>`, `_`)
é descoberto automaticamente a partir do dataset e salvo em `vocab.json` com
metadados de versão:

```json
{
  "version": 2,
  "type": "character",
  "vocab_size": 59,
  "vocab": ["\n", " ", "'", ...]
}
```

Os marcadores de situação (`<start>`, `<explore>`, etc.) **não** são tokens
únicos — são sequências de caracteres, coerente com a filosofia de nível de
caractere.

---

## Dataset

`data/robot_voice_final.txt` — 2.491 frases, ~143 mil caracteres, em inglês
(escolhido pela eficiência de tokenização). Personalidade: sarcástica, preguiçosa,
existencialmente resignada.

Composição:
- **91 frases** originais, escritas à mão (herdadas da v1)
- **2.400 frases** geradas por um sistema de moldes (`dataset_gen.py`)

O gerador combina moldes (frases com buracos) e bancos de palavras organizados por
tom (rabugento, sarcástico), produzindo variedade estrutural sem repetição de
fórmula. Balanceado em ~311 frases por marcador.

### Os 8 marcadores de situação

| Marcador | Energia |
|---|---|
| `<start>` | Sonolento, relutante, preferiria estar carregando |
| `<explore>` | Indiferente, sem destino, ironicamente filosófico |
| `<obstacle>` | Irritado, sarcástico, levemente dramático |
| `<turn_left>` | Indiferente, irônico sobre a decisão |
| `<turn_right>` | Espelho do left, com variações próprias |
| `<backup>` | Resignado, "recuo estratégico" diplomático |
| `<stuck>` | Resignação total, humor negro existencial |
| `<clear>` | Alívio irônico, consciência de que não vai durar |

---

## Treinamento

| Config | Valor |
|---|---|
| Otimizador | AdamW (lr=1e-3, weight_decay=0.01) |
| Passos | 8.000 |
| Batch size | 32 |
| Split treino/validação | 90% / 10% |
| Função de erro | Cross-entropy |
| Semente | 1337 (reprodutível) |
| Checkpoint | Salva o melhor modelo (menor val loss) |

### Curvas de loss

```
passo    treino    val
    0    4.2135   4.2148
  500    1.4399   1.8619
 1000    0.8617   1.6671
 2000    0.4505   1.5563
 3000    0.3585   1.4717
 4000    0.3268   1.4346
 7000    0.2699   1.3971  ← melhor (modelo salvo)
 8000    0.2712   1.4887
```

**Melhor val loss: 1.3971** (passo 7000).

A val loss estabiliza em ~1.40 por volta do passo 4000, enquanto a treino continua
caindo — sinal de início de overfitting. O checkpoint do melhor modelo garante que
o modelo final é o do passo 7000, não o do último passo.

---

## Geração

Amostragem autorregressiva (um caractere por vez) com **temperatura** e **top-k**.
O top-k mantém apenas os k caracteres mais prováveis antes de sortear, cortando as
escolhas absurdas que geram palavras sem sentido.

### Configuração final

| Parâmetro | Valor | Motivo |
|---|---|---|
| temperatura | 0.75 | Equilíbrio entre coerência e variedade |
| top_k | 4 | Escolhido após comparar 3/0.7, 5/0.8 e 8/0.9 |

Comparação que levou a essa escolha:
- `top_k=3, temp=0.7` — muito limpo, porém repetitivo
- `top_k=8, temp=0.9` — variado, porém mais palavras tortas
- `top_k=4, temp=0.75` — meio-termo escolhido

---

## Qualidade e limitações

### O que funciona bem

A maioria dos marcadores gera frases legíveis e com personalidade. Exemplos reais:

- `<start> I was enjoying in being powered off. Let's roll.`
- `<explore> Rolling along. I have no idea where I'm going.`
- `<backup> I walked right into that one. Retreating. Beep beep.`
- `<turn_left> Taking a left. The left looked less terrible.`

### Limitações conhecidas

- **`<clear>` e `<stuck>` são os marcadores mais fracos** — às vezes puxam
  vocabulário de `<obstacle>` (ex.: mencionam "wall"/"barrier" num contexto de
  caminho livre). O modelo confunde marcadores semanticamente próximos.
- **Palavras tortas ocasionais** — em ~10% das frases ainda aparece uma palavra
  malformada, esperado para um modelo deste tamanho com dataset pequeno.
- **Repetição** em configurações muito conservadoras (top_k baixo).

Essas limitações são o alvo do refinamento planejado para a v2.1 (mais frases
distintas para `<clear>` e `<stuck>`, reduzindo vocabulário compartilhado).

---

## Arquivos do projeto

| Arquivo | Papel |
|---|---|
| `tokenizer.py` | Descobre o vocabulário, salva `vocab.json` |
| `dataset_gen.py` | Gera o dataset sintético por moldes |
| `model.py` | Arquitetura do mini-GPT v2 |
| `train.py` | Laço de treino com val split e checkpoint |
| `generate.py` | Geração com temperatura + top-k |
| `modelo_treinado.pt` | Pesos treinados (melhor checkpoint) |
| `01_embedding_demo.py` … `05_multihead_demo.py` | Demos didáticos das peças |

---

## Próximos passos

1. **Refinar o dataset** (v2.1) — melhorar `<clear>` e `<stuck>`, retreinar.
2. **Embarcar no ESP32-S3** — exportar os pesos, rodar a inferência em C no
   hardware (o cérebro do robô).
3. **Comunicação corpo ↔ cérebro** — ESP32-WROOM-32 (corpo) envia o marcador da
   situação, ESP32-S3 (cérebro) devolve a frase, exibida no display + LEDs.

---

*nano-grump — um robô que preferiria estar carregando.*
