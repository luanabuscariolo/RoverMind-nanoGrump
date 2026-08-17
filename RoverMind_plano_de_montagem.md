# RoverMind (nano-grump) — Plano de Montagem e Conexões

> Documento de referência completo para montar o robô autônomo de dois cérebros:
> um **corpo** (ESP32-WROOM-32) que navega e um **cérebro** (ESP32-S3) que gera
> falas sarcásticas com o modelo nano-grump e as mostra num display OLED.
> Atualizado com a alimentação por bateria **Li-ion 2S (7,4 V)**.
>
> Serve para replicar o projeto do zero ou para refazer a montagem.

---

## 1. Visão geral da arquitetura

O robô tem **duas placas** que dividem tarefas:

- **Corpo — ESP32-WROOM-32:** lê o sensor ultrassônico, move o servo, controla os
  motores pela ponte H e decide para onde ir. Quando acontece uma situação
  (obstáculo, curva, etc.), envia um **marcador** de texto pela UART.
- **Cérebro — ESP32-S3:** recebe o marcador, roda o modelo de linguagem nano-grump
  (inferência em C) e mostra a frase gerada no display OLED, com "olhos" expressivos.

As duas placas conversam por **UART** (um fio de dados + GND comum), a 9600 baud.

---

## 2. Lista de componentes (BOM)

### Processamento
| Item | Especificação | Função |
|---|---|---|
| ESP32-WROOM-32 | DevKit, USB CP2102 | Corpo (navegação) |
| ESP32-S3 | N16R8 (16 MB flash, 8 MB PSRAM) | Cérebro (LLM + display) |

### Movimento e sensores
| Item | Especificação | Função |
|---|---|---|
| Ponte H L298N | módulo com regulador 5 V | Aciona os 2 motores |
| Motor DC TT | 3–6 V, com caixa de redução | Tração (2×) |
| Rodas | para motor TT | 2× |
| Roda boba (caster) | esférica ou giratória | Apoio dianteiro/traseiro |
| Chassi 2WD | acrílico ou similar | Estrutura |
| Servo SG90 | micro servo 9 g | Gira o sensor (varredura) |
| Sensor HC-SR04 | ultrassônico | Mede distância |
| Suporte pan/tilt | bracket p/ SG90 + HC-SR04 | Segura o sensor no servo |

### Interface
| Item | Especificação | Função |
|---|---|---|
| Display OLED | Keyestudio KS0056, 1.3", **SH1106, SPI** | Mostra a fala do robô |

### Alimentação (uma bateria + conversores)
| Item | Especificação | Função |
|---|---|---|
| Bateria Li-ion 2S | **7,4 V** (14500, 500 mAh) | Fonte única do robô |
| — 2ª bateria igual | 7,4 V | Reserva (troca quando a 1ª acabar) |
| Conversor **step-up (boost)** | **XL6009**, 5–35 V, 4 A | Eleva 7,4 V → ~9 V p/ os motores |
| Conversor **step-down (buck)** | **LM2596**, 1,25–30 V, 3 A | Abaixa 7,4 V → 5 V p/ a lógica |
| Capacitor eletrolítico | **1000 µF, 25 V** | Pulmão no barramento de 5 V |
| Carregador de Li-ion | próprio para 2S / do carrinho | Recarga segura (uma por vez) |

### Passivos e diversos
| Item | Especificação | Função |
|---|---|---|
| Protoboard | 400 ou 830 pontos | Barramentos VCC/GND |
| Jumpers | macho-macho e macho-fêmea | Ligações |
| Fio para GND comum | — | Une todos os terras (bateria, conversores, tudo) |

---

## 3. Alimentação (a parte mais importante — leia com atenção)

### 3.1 A ideia: UMA bateria, DOIS conversores
A bateria (7,4 V) alimenta dois caminhos em paralelo, cada um com seu conversor —
um eleva a tensão para os motores, o outro abaixa para a lógica.

- **XL6009 (boost) → ~9 V → motores** (entrada 12V do L298N). Mantém o torque firme
  mesmo com a bateria descarregando (boost só sobe, nunca desce).
- **LM2596 (buck) → 5,0 V → lógica** (os dois ESP32) + **servo** + **HC-SR04**.
  Fonte de 5 V limpa e forte (3 A), muito melhor que o regulador interno do L298N.
- **Capacitor 1000 µF** no barramento de 5 V, como pulmão contra os picos do servo.
- **Display → 3,3 V do S3.**

> ⚠️ **AJUSTE OS MÓDULOS ANTES DE CONECTAR AS CARGAS.** Boost e buck vêm de fábrica
> numa tensão qualquer. Ligue cada um só com a bateria, meça a saída com o multímetro
> e gire o trimpot (parafuso azul) até a tensão certa (buck = 5,0 V; boost = ~9 V).
> Só depois conecte os ESP32/motores. Pular isto pode queimar os ESP32.

> Por que ~9 V no boost e não menos? Boost só eleva. Para a saída ficar constante, o
> alvo precisa ser maior que a bateria cheia (8,4 V). Com ~9 V, os motores recebem
> ~7 V firmes. Se quiser poupar os motores, ajuste para ~8 V (recebem ~6 V, nominal).

### 3.2 Ligações de energia
| De | Para |
|---|---|
| Bateria **+ (7,4 V)** | entrada **IN+** do XL6009 **e** IN+ do LM2596 |
| Bateria **– (GND)** | **barramento GND comum** (e IN− dos dois módulos) |
| XL6009 **OUT+** (~9 V) | Terminal **12V / VMS** do L298N |
| XL6009 **OUT−** | GND comum |
| LM2596 **OUT+** (5,0 V) | **VIN** do WROOM, **5V** do S3, **VCC** do servo, **VCC** do HC-SR04 |
| LM2596 **OUT−** | GND comum |
| Jumper de 5 V do L298N | **colocado** (só para a lógica interna do L298N) |
| Capacitor **1000 µF** | entre o **5 V** e o **GND** (perna longa = +) |

### 3.3 Aterramento comum (essencial)
**Todos os GND no mesmo barramento** da protoboard: bateria, XL6009, LM2596, L298N,
WROOM, S3, servo, HC-SR04 e display. Sem GND comum, a UART e os sinais para o L298N
não têm referência e nada funciona de forma confiável.

### 3.4 Autonomia (trade-off da fonte única)
Com uma bateria só (500 mAh) alimentando tudo, a autonomia fica menor que com duas
baterias dividindo (some a isso a pequena perda dos conversores). A vantagem é a
simplicidade: uma bateria, uma recarga. A **2ª Li-ion** fica de reserva para troca
rápida quando a primeira enfraquecer.

### 3.5 Segurança com Li-ion
- Nunca deixe descarregar abaixo de ~6 V no pack (3 V por célula).
- Carregue **só com carregador de Li-ion** apropriado.
- Se **esquentar, inchar ou cheirar**, desconecte imediatamente.
- Nunca curto-circuite os terminais.

---

## 4. Mapa de pinos — CORPO (ESP32-WROOM-32)

| Componente | Pino do periférico | ESP32-WROOM | Observação |
|---|---|---|---|
| HC-SR04 | TRIG | **GPIO32** | saída digital |
| HC-SR04 | ECHO | **GPIO33** | ligado direto (ver nota abaixo) |
| Servo SG90 | PWM (laranja) | **GPIO13** | sinal |
| L298N | ENA | **GPIO23** | velocidade motor A (PWM) |
| L298N | IN1 | **GPIO22** | direção motor A |
| L298N | IN2 | **GPIO21** | direção motor A |
| L298N | IN3 | **GPIO19** | direção motor B |
| L298N | IN4 | **GPIO18** | direção motor B |
| L298N | ENB | **GPIO5** | velocidade motor B (PWM) |
| UART → cérebro | **TX2 = GPIO17** | | vai para o RX do S3 |
| Alimentação | VIN | **5 V do buck (LM2596)** | |
| Alimentação | GND | GND comum | |

**Motores na saída do L298N:**
- Motor esquerdo → **OUT1 / OUT2**
- Motor direito → **OUT3 / OUT4**
- (se um motor girar ao contrário, basta inverter seus dois fios)

> **Nota sobre o ECHO (sem divisor de tensão):** por decisão do projeto, o ECHO vai
> ligado direto no GPIO33, sem os resistores de divisão. O ECHO do HC-SR04 pode
> emitir 5 V, acima dos 3,3 V que o ESP32 espera — funciona, mas a longo prazo é
> desgaste no pino. Fica registrado como escolha consciente; se um dia quiser
> proteger o pino sem custo, alimentar o HC-SR04 com 3,3 V faz o ECHO cair junto.

---

## 5. Mapa de pinos — CÉREBRO (ESP32-S3 N16R8)

| Componente | Pino do periférico | ESP32-S3 | Observação |
|---|---|---|---|
| UART ← corpo | **RX1 = GPIO18** | | recebe o marcador do WROOM |
| Display SH1106 | CLK (SCK) | **GPIO12** | SPI clock |
| Display SH1106 | MOSI (SDA) | **GPIO11** | SPI dados |
| Display SH1106 | CS | **GPIO8** | chip select |
| Display SH1106 | DC | **GPIO9** | data/command |
| Display SH1106 | RES | **GPIO10** | reset |
| Display SH1106 | VCC | **3,3 V** | |
| Display SH1106 | GND | GND comum | |
| Alimentação | 5V | **5 V do buck (LM2596)** | mesma fonte de lógica do WROOM |
| Alimentação | GND | GND comum | |

> O S3 **não toca nos motores**. Ele só recebe o marcador pela UART, gera a frase e
> a exibe. Toda a parte de potência fica no lado do corpo.

---

## 6. Comunicação entre as placas (UART)

| Corpo (WROOM) | Cérebro (S3) |
|---|---|
| **TX2 = GPIO17** | → | **RX1 = GPIO18** |
| **GND** | ── | **GND** (comum) |

- Velocidade: **9600 baud** nos dois lados.
- É mão única (só o corpo fala, o cérebro escuta).
- ⚠️ **Desconecte o fio TX→RX antes de gravar firmware** em qualquer placa, senão a
  UART ativa atrapalha o upload.

Os 8 marcadores enviados pelo corpo conforme a navegação:
`<start>`, `<explore>`, `<obstacle>`, `<turn_left>`, `<turn_right>`, `<backup>`,
`<stuck>`, `<clear>`.

---

## 7. Ordem de montagem sugerida (regra de ouro: testar peça por peça)

1. **Sem energia**, monte a estrutura: chassi, motores, roda boba, suporte do servo.
2. **Ajuste os conversores ISOLADOS** (só com a bateria, cargas desconectadas):
   buck LM2596 → **5,0 V**; boost XL6009 → **~9 V**. Confirme no multímetro.
3. Monte a eletrônica na protoboard, com **todos os GND unidos**.
4. Teste **cada peça isolada** com um sketch dedicado, com as **rodas no ar**:
   HC-SR04 → servo → motores → display → UART.
5. Só depois integre tudo.
6. Energização por último: confira as tensões dos conversores, então ligue.

---

## 8. Resumo em uma frase

> Robô de dois ESP32 com **uma bateria Li-ion 2S (7,4 V)** e dois conversores: um
> boost XL6009 eleva para ~9 V e move os motores pela ponte H L298N, e um buck LM2596
> abaixa para 5 V e alimenta a lógica, o servo e o sensor; o WROOM navega e envia
> marcadores por UART; o S3 gera falas com o nano-grump num OLED SH1106 — com um
> capacitor de 1000 µF no barramento de 5 V e todos os GND unidos.
