# RoverMind — nano-grump

[![Docs: CC BY-NC-SA 4.0](https://img.shields.io/badge/Docs-CC%20BY--NC--SA%204.0-534AB7.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Code: MIT](https://img.shields.io/badge/Code-MIT-0F6E56.svg)](https://opensource.org/license/mit)

> Um robô autônomo de dois cérebros que anda sozinho, desvia de obstáculos e
> **comenta cada situação com uma personalidade sarcástica** — gerada por um
> mini-GPT treinado do zero e rodando em C num microcontrolador.

O **corpo** (ESP32-WROOM-32) navega e lê sensores. O **cérebro** (ESP32-S3) roda o
**nano-grump**, um modelo de linguagem de nível de caractere que dá voz preguiçosa e
rabugenta ao robô. O corpo detecta uma situação, envia um marcador ao cérebro, e o
cérebro responde com uma frase exibida no display OLED — com olhos expressivos e
fala progressiva.

```
<obstacle>   → "A barrier again. Alright."
<backup>     → "Reversing out. Not defeat, just a tactical nap in motion."
<stuck>      → "I'm boxed in. This was absolutely intentional."
<clear>      → "Free to move. Enjoy it while it lasts."
```

Tudo construído **do zero, sem caixas pretas** — do tokenizer à atenção multi-cabeça,
do dataset ao firmware de inferência em C.

---

## Arquitetura de dois cérebros

```
                    ROBÔ
                      │
          ┌───────────┴────────────┐
          │                        │
   ESP32-WROOM-32              ESP32-S3
      CORPO                     CÉREBRO
          │                        │
   HC-SR04 (sensor)          nano-grump (LLM)
   SG90 (servo)              display OLED SH1106
   L298N (motores)           olhos + fala
   navegação                 personalidade
          │                        │
          └────────── UART ────────┘
        marcador de situação → frase sarcástica
```

O corpo cuida de navegação e motores. O cérebro cuida de linguagem e personalidade.
A IA **não** controla os motores — ela só dá voz ao que o robô faz. A comunicação é
por UART (o corpo envia o marcador, o cérebro gera e exibe).

---

## O modelo (nano-grump v2)

Um mini-GPT decoder-only, nível de caractere, montado peça por peça:

| Item | Valor |
|---|---|
| Parâmetros | ~215 mil |
| Vocabulário | 59 caracteres |
| Contexto | 128 caracteres |
| Camadas | 4 blocos |
| Atenção | 4 cabeças (multi-head) |
| Embedding | 64 dimensões |
| Melhor val loss | 1.40 |
| Framework | PyTorch + CUDA |

Detalhes completos de arquitetura, treino e resultados em [`MODEL_CARD.md`](MODEL_CARD.md).

---

## Estrutura do repositório

```
RoverMind-nanoGrump/
├── data/
│   └── robot_voice_final.txt   # dataset: 2491 frases com personalidade
│
│   # --- Pipeline do modelo (Python) ---
├── dataset_gen.py              # gera o dataset sintético por moldes
├── tokenizer.py                # descobre o vocabulário → vocab.json
├── model.py                    # arquitetura do mini-GPT (multi-cabeça)
├── train.py                    # treino com val split + checkpoint
├── generate.py                 # geração com temperatura + top-k
├── export.py                   # exporta os pesos → nano-grump.bin
│
│   # --- Firmware (C / Arduino) ---
├── firmware/
│   ├── firmware.ino            # cérebro: inferência + display + UART (S3)
│   └── partitions.csv          # layout da flash (partição "model")
├── robo_corpo.ino              # corpo: navegação + envio de marcadores (WROOM-32)
│
│   # --- Documentação ---
├── MODEL_CARD.md               # ficha técnica do modelo
├── README.md                   # este arquivo
│
│   # --- Demos didáticos (pasta demos/) ---
└── demos/
    ├── 01_embedding_demo.py    # caractere → vetor
    ├── 02_posicao_demo.py      # embedding de posição
    ├── 03_atencao_demo.py      # self-attention (1 cabeça)
    ├── 04_ffn_demo.py          # feed-forward
    └── 05_multihead_demo.py    # atenção multi-cabeça
```

---

## Pipeline completo

### Parte A — Treinar o modelo (no PC)

Requer Python ≥ 3.12, [`uv`](https://github.com/astral-sh/uv), e idealmente GPU CUDA.

```bash
uv sync                    # instala tudo (inclui PyTorch com CUDA)

uv run dataset_gen.py      # 1. gera o dataset (~2400 frases sintéticas)
uv run tokenizer.py        # 2. constrói o vocabulário (vocab.json)
uv run train.py            # 3. treina (8000 passos, salva o melhor modelo)
uv run generate.py         # 4. testa a geração no PC
```

### Parte B — Embarcar no ESP32-S3 (o cérebro)

```bash
uv run export.py           # 5. gera nano-grump.bin (~840 KB)
```

Grave o binário na partição de dados da flash (segure BOOT durante a conexão):

```bash
python -m esptool --chip esp32s3 --port COMxx \
  write-flash 0x110000 nano-grump.bin
```

Depois, no **Arduino IDE**:
- Abra `firmware/firmware.ino`
- Placa: **ESP32S3 Dev Module** · PSRAM: **OPI PSRAM** · Partition Scheme: **Custom**
- Faça o upload

### Parte C — Programar o corpo (ESP32-WROOM-32)

- Abra `robo_corpo.ino`
- Defina `MODO_SIMULACAO false` para o robô físico (ou `true` para o Wokwi)
- Placa: **ESP32 Dev Module** · Faça o upload (segure BOOT)

### Parte D — Ligar os dois

```
WROOM-32 GPIO17 (TX) ─────→ GPIO18 (RX) do S3
WROOM-32 GND ──────────────  GND do S3
```

Dois fios: dados (TX→RX) e o terra comum (essencial para a UART). Cada placa na sua
própria alimentação. Ligue, e o robô comenta cada situação sozinho.

> **Dica de gravação:** ao regravar qualquer um dos ESP32, desconecte o fio de dados
> TX→RX entre eles — a UART ativa pode interferir no upload.

---

## Os 8 marcadores de situação

| Marcador | Disparado quando | Olhos | Energia |
|---|---|---|---|
| `<start>` | Liga | feliz | Sonolento, relutante |
| `<explore>` | Andando em frente | curioso | Indiferente, filosófico |
| `<obstacle>` | Detecta obstáculo | alerta | Irritado, sarcástico |
| `<turn_left>` | Curva à esquerda | olha ← | Irônico |
| `<turn_right>` | Curva à direita | olha → | Irônico |
| `<backup>` | Recuando | preocupado | "Recuo estratégico" |
| `<stuck>` | Os dois lados bloqueados | travado | Resignação existencial |
| `<clear>` | Caminho livre após evasão | aliviado | Alívio irônico |

---

## Hardware

**Corpo (ESP32-WROOM-32):**

| Componente | Pino |
|---|---|
| HC-SR04 TRIG / ECHO | GPIO32 / GPIO33 |
| Servo SG90 | GPIO13 |
| L298N ENA/IN1/IN2 | GPIO23 / GPIO22 / GPIO21 |
| L298N IN3/IN4/ENB | GPIO19 / GPIO18 / GPIO5 |
| UART TX → cérebro | GPIO17 |

**Cérebro (ESP32-S3 N16R8):**

| Componente | Pino |
|---|---|
| OLED SH1106 CLK/MOSI | GPIO12 / GPIO11 |
| OLED CS/DC/RES | GPIO8 / GPIO9 / GPIO10 |
| UART RX ← corpo | GPIO18 |

Alimentação do corpo: 4×AA (~6V) → L298N → 5V regulado → VIN do ESP32. Todos os GNDs
unidos (incluindo o terra comum com o cérebro).

---

## Estado e backlog

**Funcionando:** modelo treinado, embarcado no S3, comunicação UART com o corpo, os
8 marcadores disparados pela navegação real, display com olhos e fala progressiva.

**Backlog:**
1. **Debounce de marcadores** — sincronizar a fala com o ritmo das ações (numa
   janela de tempo, só a última ação vale).
2. **Refinar dataset** — melhorar `<clear>` e `<stuck>` (marcadores mais fracos).
3. **Polimento do display** — animações dos olhos, indicador de "pensando".
4. **Autonomia de energia** — rodar de bateria, sem cabos USB.

---

## Filosofia do projeto

**Entender antes de integrar.** Nada de caixas pretas. Cada peça — tokenizer,
embedding, atenção, FFN, multi-cabeça, e a inferência em C — foi construída e testada
isoladamente antes de virar parte do todo. Os demos numerados são o registro dessa
jornada. O objetivo não é só um robô que fala: é entender, camada por camada, como um
Transformer aprende linguagem e como roda em hardware limitado.

---

*nano-grump — um robô que preferiria estar carregando.* 
