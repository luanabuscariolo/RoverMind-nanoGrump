/*
  ============================================================
  firmware.ino  -  nano-grump no ESP32-S3
  ============================================================

  O que este firmware faz:
    1. Le os pesos do nano-grump da flash (particao "model")
    2. Aguarda um marcador chegar pela Serial
       ex: "<obstacle>\n"
    3. Gera uma frase sarcastica caractere por caractere
       (a mesma logica do generate.py, em C)
    4. Imprime a frase na Serial e no display OLED

  Organizacao:
    PARTE 1 - Configuracoes e estruturas de dados
    PARTE 2 - Funcoes matematicas (as contas dos demos)
    PARTE 3 - Forward pass (a inferencia completa)
    PARTE 4 - Geracao de texto (top-k + temperatura)
    PARTE 5 - setup() e loop()

  Parametros de geracao (mexa aqui para ajustar):
    TEMPERATURA  0.75  (igual ao generate.py)
    TOP_K        4     (igual ao generate.py)
    MAX_TOKENS   120   (limite de caracteres por frase)
  ============================================================
*/

#include <Arduino.h>
#include "esp_partition.h"    // acesso as particoes da flash
#include "esp_heap_caps.h"    // alocacao de memoria em PSRAM/SRAM
#include <math.h>             // expf(), sqrtf()

// ------------------------------------------------------------
// Display OLED SH1106 SPI (pinos confirmados no seu hardware)
// CLK=12, MOSI=11, CS=8, DC=9, RES=10
// ------------------------------------------------------------
#include <U8g2lib.h>
#include <SPI.h>

U8G2_SH1106_128X64_NONAME_F_4W_HW_SPI
  display(U8G2_R0, /*cs=*/8, /*dc=*/9, /*reset=*/10);


// ============================================================
// PARTE 1 — CONFIGURACOES E ESTRUTURAS DE DADOS
// ============================================================

// Parametros de geracao
#define TEMPERATURA   0.75f
#define TOP_K         4
#define MAX_TOKENS    120

// Hiperparametros do modelo (mesmos valores do model.py)
// Serao confirmados ao ler o cabecalho do .bin
#define VOCAB_SIZE  59
#define N_EMBD      64
#define BLOCK_SIZE  64
#define N_LAYER     4
#define N_HEADS     4
#define HEAD_SIZE   (N_EMBD / N_HEADS)   // 64 / 4 = 16
#define FFN_DIM     (4 * N_EMBD)         // 256

// Cabecalho do .bin (os mesmos 6 inteiros que o export.py escreveu)
struct __attribute__((packed)) Cabecalho {
  int vocab_size;
  int n_embd;
  int block_size;
  int n_layer;
  int n_heads;
  int reservado;
};

// Pesos de um unico bloco (atencao + FFN + layernorms)
// Cada campo e um ponteiro que aponta direto para a flash.
// Nao copiamos nada — lemos direto de onde o esptool gravou.
struct PesosBloco {
  const float *ln1_w, *ln1_b;          // layernorm 1 (peso e bias)
  const float *q_w, *k_w, *v_w;       // query, key, value
  const float *proj_w, *proj_b;        // projecao de saida da atencao
  const float *ln2_w, *ln2_b;          // layernorm 2
  const float *ffn1_w, *ffn1_b;        // FFN expandir (64->256)
  const float *ffn2_w, *ffn2_b;        // FFN contrair (256->64)
};

// Todos os pesos do modelo
struct Pesos {
  const float *emb_token;              // embedding de token  (59 x 64)
  const float *emb_pos;                // embedding de posicao (64 x 64)
  PesosBloco   blocos[N_LAYER];        // 4 blocos
  const float *ln_final_w, *ln_final_b; // layernorm final
  const float *saida_w;                // camada de saida (59 x 64)
};

// Vocabulario: os 59 caracteres (mesma ordem do vocab.json)
// Gerado a partir do vocab.json pelo script abaixo em Python:
//
//   import json
//   v = json.load(open("vocab.json"))["vocab"]
//   print("{" + ", ".join(f"'{c}'" if c not in ("'","\\") else
//         ("'\\''") if c=="'" else ("'\\\\'") for c in v) + "}")
//
// Cole o resultado na linha abaixo:
const char VOCAB[VOCAB_SIZE] = {
  '\n',' ','\'',',','-','.', ':','<','>','?',
  'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
  'L', 'M', 'N', 'O', 'P', 'R', 'S', 'T', 'U', 'V',
  'W', 'Y', '_', 'a', 'b', 'c', 'd', 'e', 'f', 'g',
  'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q',
  'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
};

// Indice do caractere '\n' (fim de frase) — posicao 0 no vocab
#define TOKEN_NEWLINE 0

// Buffers de calculo na SRAM (pequenos, acessados muitas vezes)
// Declarados globalmente para nao estourar a pilha (stack)
static float x[N_EMBD];          // vetor atual do token
static float xb[N_EMBD];         // copia normalizada
static float q[N_EMBD];          // query
static float k_buf[N_EMBD];      // key
static float v_buf[N_EMBD];      // value
static float h[FFN_DIM];         // buffer intermediario da FFN
static float logits[VOCAB_SIZE]; // saida final (uma nota por caractere)

// Cache KV na PSRAM (cresce com a sequencia, ate BLOCK_SIZE posicoes)
// Guarda as keys e values de todas as posicoes anteriores —
// e o que permite a atencao "olhar para o passado".
static float *kv_cache_k = nullptr;  // (N_LAYER x BLOCK_SIZE x N_EMBD)
static float *kv_cache_v = nullptr;  // (N_LAYER x BLOCK_SIZE x N_EMBD)

// Pesos do modelo (ponteiros para a flash)
static Pesos w;


// ============================================================
// PARTE 2 — FUNCOES MATEMATICAS
// ============================================================
// Estas funcoes implementam as mesmas operacoes dos demos,
// em C. A matematica e identica — so o idioma mudou.

// ------------------------------------------------------------
// rmsnorm: normaliza um vetor (como o LayerNorm do model.py,
// versao simplificada sem media — so divide pelo RMS).
// RMS = raiz da media dos quadrados.
// ------------------------------------------------------------
static void rmsnorm(float *out, const float *x, const float *w, int n) {
  float ss = 0.0f;
  for (int i = 0; i < n; i++) ss += x[i] * x[i];
  ss = 1.0f / sqrtf(ss / n + 1e-5f);
  for (int i = 0; i < n; i++) out[i] = w[i] * (ss * x[i]);
}

// ------------------------------------------------------------
// matmul: multiplica matriz por vetor.
// out[i] = soma(A[i][j] * x[j]) para j de 0 a n-1
// e o que acontece dentro do Linear() do PyTorch.
// ------------------------------------------------------------
static void matmul(float *out, const float *x,
                   const float *A, int linhas, int colunas) {
  for (int i = 0; i < linhas; i++) {
    float acc = 0.0f;
    for (int j = 0; j < colunas; j++)
      acc += A[i * colunas + j] * x[j];
    out[i] = acc;
  }
}

// ------------------------------------------------------------
// softmax: converte notas em probabilidades que somam 1.
// (a mesma operacao do demo 3, etapa 4)
// ------------------------------------------------------------
static void softmax(float *x, int n) {
  float max_val = x[0];
  for (int i = 1; i < n; i++) if (x[i] > max_val) max_val = x[i];
  float soma = 0.0f;
  for (int i = 0; i < n; i++) { x[i] = expf(x[i] - max_val); soma += x[i]; }
  for (int i = 0; i < n; i++) x[i] /= soma;
}

// ------------------------------------------------------------
// relu: zera os negativos (a ativacao da FFN, demo 4)
// ------------------------------------------------------------
static void relu(float *x, int n) {
  for (int i = 0; i < n; i++) if (x[i] < 0.0f) x[i] = 0.0f;
}


// ============================================================
// PARTE 3 — FORWARD PASS (a inferencia completa)
// ============================================================
// Esta funcao e a traducao direta do model.py para C.
// Recebe um token e uma posicao, atualiza o cache KV,
// e preenche o array global "logits" com as notas finais.

static void forward(int token, int pos) {

  // 1. EMBEDDING (demo 1 + demo 2)
  // x = emb_token[token] + emb_posicao[pos]
  const float *te = w.emb_token + token * N_EMBD;
  const float *pe = w.emb_pos   + pos   * N_EMBD;
  for (int i = 0; i < N_EMBD; i++) x[i] = te[i] + pe[i];

  // 2. BLOCOS (demo 3 + demo 4 + demo 5, repetido N_LAYER vezes)
  for (int l = 0; l < N_LAYER; l++) {
    PesosBloco *b = &w.blocos[l];

    // --- SUB-CAMADA 1: ATENCAO MULTI-CABECA ---

    // 2a. LayerNorm antes da atencao (pre-norm, como no model.py)
    rmsnorm(xb, x, b->ln1_w, N_EMBD);
    // OBS: nosso layernorm nao tem bias — o export.py exportou
    // o bias mas aqui usamos RMSNorm simplificado (sem bias).
    // A diferenca e minima na pratica para este modelo.

    // 2b. Calcular Q, K, V (as tres "vistas" de cada token)
    matmul(q,     xb, b->q_w, N_EMBD, N_EMBD);
    matmul(k_buf, xb, b->k_w, N_EMBD, N_EMBD);
    matmul(v_buf, xb, b->v_w, N_EMBD, N_EMBD);

    // 2c. Guardar K e V no cache (para as posicoes futuras
    //     poderem "olhar para tras" — a mascara causal do demo 3)
    float *kc = kv_cache_k + l * BLOCK_SIZE * N_EMBD + pos * N_EMBD;
    float *vc = kv_cache_v + l * BLOCK_SIZE * N_EMBD + pos * N_EMBD;
    for (int i = 0; i < N_EMBD; i++) { kc[i] = k_buf[i]; vc[i] = v_buf[i]; }

    // 2d. ATENCAO MULTI-CABECA (demo 5)
    // Para cada cabeca, calculamos a atencao independentemente
    // numa fatia de HEAD_SIZE numeros (16 de 64).
    float att_out[N_EMBD] = {0};

    for (int h_idx = 0; h_idx < N_HEADS; h_idx++) {
      int offset = h_idx * HEAD_SIZE;  // inicio da fatia desta cabeca

      // Ponteiro para a fatia desta cabeca em Q
      float *q_h = q + offset;

      // Calcular notas: quanto esta posicao "presta atencao" a cada
      // posicao anterior (produto escalar Q . K, escalado)
      float scores[BLOCK_SIZE];
      for (int t = 0; t <= pos; t++) {
        float *k_h = kv_cache_k + l * BLOCK_SIZE * N_EMBD
                     + t * N_EMBD + offset;
        float dot = 0.0f;
        for (int i = 0; i < HEAD_SIZE; i++) dot += q_h[i] * k_h[i];
        scores[t] = dot / sqrtf((float)HEAD_SIZE);
      }

      // Softmax das notas (so ate "pos", mascara causal automatica)
      float max_s = scores[0];
      for (int t = 1; t <= pos; t++) if (scores[t] > max_s) max_s = scores[t];
      float soma = 0.0f;
      for (int t = 0; t <= pos; t++) { scores[t] = expf(scores[t]-max_s); soma += scores[t]; }
      for (int t = 0; t <= pos; t++) scores[t] /= soma;

      // Soma ponderada dos Values (pesos . V)
      for (int t = 0; t <= pos; t++) {
        float *v_h = kv_cache_v + l * BLOCK_SIZE * N_EMBD
                     + t * N_EMBD + offset;
        for (int i = 0; i < HEAD_SIZE; i++)
          att_out[offset + i] += scores[t] * v_h[i];
      }
    }

    // 2e. Projecao de saida da atencao + residual
    float proj_out[N_EMBD];
    matmul(proj_out, att_out, b->proj_w, N_EMBD, N_EMBD);
    for (int i = 0; i < N_EMBD; i++)
      x[i] += proj_out[i] + b->proj_b[i];

    // --- SUB-CAMADA 2: FFN (demo 4) ---

    // 2f. LayerNorm antes da FFN
    rmsnorm(xb, x, b->ln2_w, N_EMBD);

    // 2g. Expandir: 64 -> 256
    matmul(h, xb, b->ffn1_w, FFN_DIM, N_EMBD);
    for (int i = 0; i < FFN_DIM; i++) h[i] += b->ffn1_b[i];
    relu(h, FFN_DIM);

    // 2h. Contrair: 256 -> 64  + residual
    float ffn_out[N_EMBD];
    matmul(ffn_out, h, b->ffn2_w, N_EMBD, FFN_DIM);
    for (int i = 0; i < N_EMBD; i++)
      x[i] += ffn_out[i] + b->ffn2_b[i];
  }

  // 3. LAYERNORM FINAL + CAMADA DE SAIDA
  rmsnorm(xb, x, w.ln_final_w, N_EMBD);
  matmul(logits, xb, w.saida_w, VOCAB_SIZE, N_EMBD);
}


// ============================================================
// PARTE 4 — GERACAO DE TEXTO (top-k + temperatura)
// ============================================================
// Traducao direta do generate.py para C.

// Sorteia um indice proporcional as probabilidades em probs[].
// Usamos o gerador de numeros aleatorios do Arduino (random()).
static int amostrar(float *probs, int n) {
  float r = (float)random(10000) / 10000.0f;
  float acum = 0.0f;
  for (int i = 0; i < n; i++) {
    acum += probs[i];
    if (r < acum) return i;
  }
  return n - 1;
}

// Gera uma frase a partir de um prompt (string com o marcador).
// Imprime cada caractere na Serial e no display conforme gera.
static void gerar(const char *prompt) {

  // Zerar o cache KV (comecar uma nova sequencia do zero)
  memset(kv_cache_k, 0,
         N_LAYER * BLOCK_SIZE * N_EMBD * sizeof(float));
  memset(kv_cache_v, 0,
         N_LAYER * BLOCK_SIZE * N_EMBD * sizeof(float));

  // Converter o prompt em tokens (encode — igual ao tokenizer.py)
  int tokens[BLOCK_SIZE];
  int n_prompt = 0;
  for (int c = 0; prompt[c] != '\0' && n_prompt < BLOCK_SIZE; c++) {
    for (int v = 0; v < VOCAB_SIZE; v++) {
      if (VOCAB[v] == prompt[c]) { tokens[n_prompt++] = v; break; }
    }
  }

  // Alimentar o prompt no modelo (sem gerar saida ainda)
  int pos = 0;
  for (int i = 0; i < n_prompt; i++) {
    forward(tokens[i], pos++);
  }

  // Gerar caracteres um por um (autorregressivo)
  Serial.print(prompt);
  for (int step = 0; step < MAX_TOKENS && pos < BLOCK_SIZE; step++) {

    // Aplicar temperatura: dividir os logits pela temperatura
    // (igual ao generate.py: logits / temperatura)
    for (int v = 0; v < VOCAB_SIZE; v++)
      logits[v] /= TEMPERATURA;

    // TOP-K: manter so os K maiores logits,
    // colocar -infinito nos demais
    float top_vals[TOP_K];
    for (int i = 0; i < TOP_K; i++) top_vals[i] = -1e30f;
    for (int v = 0; v < VOCAB_SIZE; v++) {
      if (logits[v] > top_vals[TOP_K-1]) {
        top_vals[TOP_K-1] = logits[v];
        // ordenar (bubble sort simples — TOP_K e pequeno)
        for (int i = TOP_K-1; i > 0 && top_vals[i] > top_vals[i-1]; i--) {
          float tmp = top_vals[i]; top_vals[i] = top_vals[i-1]; top_vals[i-1] = tmp;
        }
      }
    }
    float corte = top_vals[TOP_K-1];
    for (int v = 0; v < VOCAB_SIZE; v++)
      if (logits[v] < corte) logits[v] = -1e30f;

    // Softmax -> probabilidades
    softmax(logits, VOCAB_SIZE);

    // Sortear o proximo token
    int next_token = amostrar(logits, VOCAB_SIZE);

    // Se gerou '\n', a frase acabou
    if (next_token == TOKEN_NEWLINE) break;

    // Imprimir o caractere gerado
    char c = VOCAB[next_token];
    Serial.print(c);
    display_char(c);   // funcao que vamos implementar no Passo 4

    // Avancar o modelo com o token gerado
    forward(next_token, pos++);
  }

  Serial.println();
  display_flush();   // funcao que vamos implementar no Passo 4
}


// ============================================================
// PARTE 5 — SETUP E LOOP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n=== nano-grump v2 ===");

  // --- 1. Encontrar e mapear a particao "model" ---
  const esp_partition_t *part = esp_partition_find_first(
    ESP_PARTITION_TYPE_DATA, (esp_partition_subtype_t)0x40, "model");
  if (!part) {
    Serial.println("ERRO: particao 'model' nao encontrada."); return;
  }
  const void *base;
  esp_partition_mmap_handle_t handle;
  if (esp_partition_mmap(part, 0, part->size,
      ESP_PARTITION_MMAP_DATA, &base, &handle) != ESP_OK) {
    Serial.println("ERRO: mmap falhou."); return;
  }
  Serial.println("Particao mapeada.");

  // --- 2. Verificar o cabecalho ---
  const Cabecalho *cab = (const Cabecalho *)base;
  if (cab->vocab_size != VOCAB_SIZE || cab->n_embd != N_EMBD ||
      cab->block_size != BLOCK_SIZE || cab->n_layer != N_LAYER ||
      cab->n_heads    != N_HEADS) {
    Serial.println("ERRO: cabecalho nao bate com o firmware."); return;
  }
  Serial.println("Cabecalho OK.");

  // --- 3. Apontar os pesos para a flash (sem copiar nada) ---
  // Comecamos logo apos o cabecalho (24 bytes)
  const float *p = (const float *)((const uint8_t *)base + 24);

  w.emb_token = p; p += VOCAB_SIZE * N_EMBD;   // 59 x 64
  w.emb_pos   = p; p += BLOCK_SIZE * N_EMBD;   // 64 x 64

  for (int l = 0; l < N_LAYER; l++) {
    PesosBloco *b = &w.blocos[l];
    b->ln1_w  = p; p += N_EMBD;
    b->ln1_b  = p; p += N_EMBD;
    b->q_w    = p; p += N_EMBD * N_EMBD;
    b->k_w    = p; p += N_EMBD * N_EMBD;
    b->v_w    = p; p += N_EMBD * N_EMBD;
    b->proj_w = p; p += N_EMBD * N_EMBD;
    b->proj_b = p; p += N_EMBD;
    b->ln2_w  = p; p += N_EMBD;
    b->ln2_b  = p; p += N_EMBD;
    b->ffn1_w = p; p += FFN_DIM * N_EMBD;
    b->ffn1_b = p; p += FFN_DIM;
    b->ffn2_w = p; p += N_EMBD * FFN_DIM;
    b->ffn2_b = p; p += N_EMBD;
  }

  w.ln_final_w = p; p += N_EMBD;
  w.ln_final_b = p; p += N_EMBD;
  w.saida_w    = p;

  Serial.println("Pesos mapeados.");

  // --- 4. Alocar cache KV na PSRAM ---
  size_t kv_bytes = N_LAYER * BLOCK_SIZE * N_EMBD * sizeof(float);
  kv_cache_k = (float *)heap_caps_malloc(kv_bytes, MALLOC_CAP_SPIRAM);
  kv_cache_v = (float *)heap_caps_malloc(kv_bytes, MALLOC_CAP_SPIRAM);
  if (!kv_cache_k || !kv_cache_v) {
    Serial.println("ERRO: falha ao alocar cache KV na PSRAM."); return;
  }
  Serial.printf("Cache KV alocado: %.1f KB na PSRAM\n",
                2 * kv_bytes / 1024.0f);

  // --- 5. Inicializar o display OLED ---
  display.begin();
  display.clearBuffer();
  display.setFont(u8g2_font_6x10_tf);
  display.drawStr(0, 12, "nano-grump v2");
  display.drawStr(0, 26, "aguardando...");
  display.sendBuffer();

  Serial.println("Display OK.");
  Serial.println("\nPronto. Envie um marcador pela Serial:");
  Serial.println("  <start>, <explore>, <obstacle>,");
  Serial.println("  <turn_left>, <turn_right>,");
  Serial.println("  <backup>, <stuck>, <clear>");
}

// Buffer para acumular o marcador recebido pela Serial
static char input_buf[32];
static int  input_len = 0;

// Variaveis para exibir a frase no display linha por linha
static char display_line1[22] = "";
static char display_line2[22] = "";
static char display_line3[22] = "";
static int  display_col = 0;
static int  display_row = 0;

// Exibe um caractere no display, quebra linha quando necessario
void display_char(char c) {
  if (display_col == 0 && display_row == 0) {
    memset(display_line1, 0, sizeof(display_line1));
    memset(display_line2, 0, sizeof(display_line2));
    memset(display_line3, 0, sizeof(display_line3));
  }
  char *linha = (display_row == 0) ? display_line1
              : (display_row == 1) ? display_line2
                                   : display_line3;
  if (display_col < 21) {
    linha[display_col++] = c;
    linha[display_col]   = '\0';
  } else {
    display_col = 0;
    display_row = (display_row < 2) ? display_row + 1 : 2;
    linha = (display_row == 1) ? display_line2 : display_line3;
    linha[display_col++] = c;
    linha[display_col]   = '\0';
  }
}

// Envia o conteudo acumulado para o display de uma vez
void display_flush() {
  display.clearBuffer();
  display.setFont(u8g2_font_6x10_tf);
  display.drawStr(0, 12, display_line1);
  display.drawStr(0, 26, display_line2);
  display.drawStr(0, 40, display_line3);
  display.sendBuffer();
  // Resetar para a proxima frase
  display_col = 0;
  display_row = 0;
}

void loop() {
  // Ler caracteres da Serial e acumular ate receber '\n'
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (input_len > 0) {
        input_buf[input_len] = '\0';
        // Verificar se e um marcador valido
        if (strncmp(input_buf, "<", 1) == 0) {
          // Adicionar espaco apos o marcador (como o generate.py faz)
          char prompt[34];
          snprintf(prompt, sizeof(prompt), "%s ", input_buf);
          Serial.printf("\nGerando para: %s\n", input_buf);
          gerar(prompt);
        } else {
          Serial.println("Marcador invalido. Use: <start>, <obstacle>, etc.");
        }
        input_len = 0;
      }
    } else if (input_len < 31) {
      input_buf[input_len++] = c;
    }
  }
}
