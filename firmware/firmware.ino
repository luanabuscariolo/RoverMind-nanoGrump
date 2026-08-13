/*
  firmware.ino — nano-grump, Passo 2
  Abre a particao "model", le o cabecalho e imprime os
  6 valores na Serial. So isso — sem inferencia ainda.
  Se os numeros baterem com o export.py, a base esta certa.
*/

#include "esp_partition.h"   // funcoes para acessar particoes da flash

// Estrutura do cabecalho — os mesmos 6 inteiros que o export.py escreveu.
// "packed" garante que o C nao adiciona espacos entre os campos.
struct __attribute__((packed)) Cabecalho {
  int vocab_size;   // 59
  int n_embd;       // 64
  int block_size;   // 64
  int n_layer;      // 4
  int n_heads;      // 4
  int reservado;    // 0
};

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n=== nano-grump: lendo cabecalho ===");

  // 1. Encontrar a particao "model" na flash
  const esp_partition_t *part = esp_partition_find_first(
    ESP_PARTITION_TYPE_DATA,          // tipo: dados (nao firmware)
    (esp_partition_subtype_t) 0x40,   // subtipo customizado (igual ao partitions.csv)
    "model"                           // nome da particao
  );

  if (!part) {
    Serial.println("ERRO: particao 'model' nao encontrada.");
    Serial.println("Verifique se o partitions.csv esta correto e");
    Serial.println("se o Partition Scheme esta em Custom.");
    return;
  }
  Serial.printf("Particao encontrada: tamanho=%.1f MB  offset=0x%x\n",
                part->size / 1048576.0, part->address);

  // 2. Mapear a particao na memoria
  // Depois do mmap, "base" e um ponteiro para o inicio dos dados —
  // como se fosse um array gigante que aponta direto para a flash.
  const void *base;
  esp_partition_mmap_handle_t handle;
  esp_err_t err = esp_partition_mmap(
    part, 0, part->size,
    ESP_PARTITION_MMAP_DATA,
    &base, &handle
  );
  if (err != ESP_OK) {
    Serial.printf("ERRO: mmap falhou (codigo %d)\n", err);
    return;
  }
  Serial.println("Particao mapeada na memoria.");

  // 3. Ler o cabecalho
  // Interpretamos os primeiros bytes da particao como um Cabecalho.
  // E como pegar os primeiros 24 bytes e dizer: "isso e um Cabecalho".
  const Cabecalho *cab = (const Cabecalho *) base;

  // 4. Imprimir os valores — devem bater com o export.py
  Serial.println("\n--- Cabecalho ---");
  Serial.printf("vocab_size : %d  (esperado: 59)\n",  cab->vocab_size);
  Serial.printf("n_embd     : %d  (esperado: 64)\n",  cab->n_embd);
  Serial.printf("block_size : %d  (esperado: 64)\n",  cab->block_size);
  Serial.printf("n_layer    : %d  (esperado: 4)\n",   cab->n_layer);
  Serial.printf("n_heads    : %d  (esperado: 4)\n",   cab->n_heads);
  Serial.printf("reservado  : %d  (esperado: 0)\n",   cab->reservado);

  // 5. Verificacao automatica
  bool ok = (cab->vocab_size == 59 &&
             cab->n_embd     == 64 &&
             cab->block_size == 64 &&
             cab->n_layer    == 4  &&
             cab->n_heads    == 4  &&
             cab->reservado  == 0);

  Serial.println(ok ? "\nCABECALHO OK — base esta certa."
                    : "\nERRO — algum valor nao bate. Verifique o export.py.");
}

void loop() {}