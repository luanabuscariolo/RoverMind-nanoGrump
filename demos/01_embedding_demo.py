"""
=============================================================
 DEMO 1 - EMBEDDING  (peca isolada do mini-GPT)
=============================================================

 Objetivo:
   Ver, na pratica, um caractere virar um vetor.

 O que este script faz:
   1. Carrega o vocabulario (vocab.json) do tokenizer.
   2. Cria a TABELA DE EMBEDDINGS com o PyTorch.
   3. Pega um texto, vira numeros, e passa pela tabela.
   4. Mostra os vetores que sairam.

 Esta e uma peca de diagnostico: nao e o modelo final,
 e so o primeiro tijolo, testado sozinho.

=============================================================
"""

import json
from pathlib import Path

import torch
import torch.nn as nn


# ------------------------------------------------------------
# 1. CARREGAR O VOCABULARIO
# ------------------------------------------------------------
# Reaproveitamos o vocab.json que o tokenizer.py salvou.
# Assim usamos EXATAMENTE o mesmo mapeamento de antes.

CAMINHO_VOCAB = Path(__file__).parent / "vocab.json"
caracteres = json.loads(CAMINHO_VOCAB.read_text(encoding="utf-8"))

stoi = {c: i for i, c in enumerate(caracteres)}
itos = {i: c for i, c in enumerate(caracteres)}

def encode(s: str) -> list[int]:
    return [stoi[c] for c in s]

tamanho_vocab = len(caracteres)
print("=" * 55)
print("DEMO 1 - EMBEDDING")
print("=" * 55)
print(f"Tamanho do vocabulario: {tamanho_vocab}")


# ------------------------------------------------------------
# 2. ESCOLHER O TAMANHO DO VETOR (n_embd)
# ------------------------------------------------------------
# Cada caractere vira um vetor com este tanto de numeros.
# E uma ESCOLHA nossa:
#   - pequeno  -> modelo leve, cabe facil no ESP32, menos expressivo
#   - grande   -> mais expressivo, porem mais pesado
# Comecamos pequeno, condizente com um robo de vocabulario minusculo.

n_embd = 32
print(f"Tamanho de cada vetor (n_embd): {n_embd}")


# ------------------------------------------------------------
# 3. CRIAR A TABELA DE EMBEDDINGS
# ------------------------------------------------------------
# nn.Embedding(linhas, colunas):
#   linhas  = tamanho_vocab (uma linha por caractere)
#   colunas = n_embd        (o tamanho de cada vetor)
#
# Ela nasce preenchida com numeros ALEATORIOS.
# O treino vai ajusta-los depois.

tabela_embedding = nn.Embedding(tamanho_vocab, n_embd)

print(f"\nFormato da tabela: {tuple(tabela_embedding.weight.shape)}")
print("  (linhas = caracteres, colunas = tamanho do vetor)")
print(f"Os numeros sao aprendiveis? {tabela_embedding.weight.requires_grad}")


# ------------------------------------------------------------
# 4. PASSAR UM TEXTO PELA TABELA
# ------------------------------------------------------------
# Pegamos um texto, viramos numeros (encode), e transformamos
# numa "torch.tensor" (o tipo de dado que o PyTorch entende).

texto = "hi"
numeros = encode(texto)
entrada = torch.tensor(numeros)   # ex: tensor([41, 42])

print("\n" + "-" * 55)
print("PASSANDO UM TEXTO PELA TABELA")
print("-" * 55)
print(f"Texto            : {texto!r}")
print(f"Numeros (encode) : {numeros}")

# Aqui acontece a magica: cada numero busca sua linha na tabela.
vetores = tabela_embedding(entrada)

print(f"Formato da saida : {tuple(vetores.shape)}")
print(f"  -> {len(numeros)} caracteres, cada um virou um vetor de {n_embd} numeros")

# Mostra o vetor do primeiro caractere (so os 8 primeiros numeros,
# para nao poluir a tela).
print(f"\nVetor do caractere {texto[0]!r} (8 primeiros de {n_embd} numeros):")
print(f"  {vetores[0][:8].tolist()}")


# ------------------------------------------------------------
# 5. CONFIRMAR QUE RODA NA GPU
# ------------------------------------------------------------
# Movemos a tabela e a entrada para a GPU e refazemos a busca.
# E o mesmo processo, so que na placa.

if torch.cuda.is_available():
    tabela_gpu = tabela_embedding.to("cuda")
    entrada_gpu = entrada.to("cuda")
    vetores_gpu = tabela_gpu(entrada_gpu)
    print("\n" + "-" * 55)
    print(f"Rodou na GPU? Sim -> saida esta em: {vetores_gpu.device}")
else:
    print("\nGPU nao disponivel - rodou na CPU.")

print("\nEmbedding demonstrado!")
