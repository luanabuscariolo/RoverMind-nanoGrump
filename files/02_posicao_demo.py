"""
=============================================================
 DEMO 2 - EMBEDDING DE POSICAO  (peca isolada do mini-GPT)
=============================================================

 Objetivo:
   Ver os DOIS embeddings se somando:
     - embedding de caractere (quem e o token)
     - embedding de posicao   (onde ele esta)

 O que este script faz:
   1. Carrega o vocabulario.
   2. Cria a tabela de caractere  -> (vocab, n_embd)
   3. Cria a tabela de posicao    -> (block_size, n_embd)
   4. Pega um texto, soma os dois, e mostra o resultado.
   5. Prova que a MESMA letra em posicoes diferentes
      gera vetores finais diferentes.

=============================================================
"""

import json
from pathlib import Path

import torch
import torch.nn as nn


# ------------------------------------------------------------
# 1. CARREGAR O VOCABULARIO
# ------------------------------------------------------------

CAMINHO_VOCAB = Path(__file__).parent / "vocab.json"
caracteres = json.loads(CAMINHO_VOCAB.read_text(encoding="utf-8"))

stoi = {c: i for i, c in enumerate(caracteres)}

def encode(s: str) -> list[int]:
    return [stoi[c] for c in s]

tamanho_vocab = len(caracteres)


# ------------------------------------------------------------
# 2. ESCOLHAS DO MODELO
# ------------------------------------------------------------
# n_embd     = tamanho de cada vetor (ja usamos 32)
# block_size = quantas posicoes a tabela de posicao cobre.
#              E o tamanho maximo de sequencia (janela de contexto).

n_embd = 32
block_size = 32

print("=" * 55)
print("DEMO 2 - EMBEDDING DE POSICAO")
print("=" * 55)
print(f"Vocabulario : {tamanho_vocab}")
print(f"n_embd      : {n_embd}")
print(f"block_size  : {block_size}")


# ------------------------------------------------------------
# 3. AS DUAS TABELAS
# ------------------------------------------------------------
# Tabela de caractere: uma linha por token do vocabulario.
# Tabela de posicao  : uma linha por posicao (0 ate block_size-1).

emb_caractere = nn.Embedding(tamanho_vocab, n_embd)
emb_posicao   = nn.Embedding(block_size, n_embd)

print(f"\nTabela de caractere: {tuple(emb_caractere.weight.shape)}")
print(f"Tabela de posicao  : {tuple(emb_posicao.weight.shape)}")


# ------------------------------------------------------------
# 4. SOMAR OS DOIS PARA UM TEXTO
# ------------------------------------------------------------

texto = "cab"
numeros = encode(texto)                     # ex: [36, 34, 35]
entrada = torch.tensor(numeros)             # formato (3,)

# Vetores de caractere: um por token -> formato (3, n_embd)
vetores_caractere = emb_caractere(entrada)

# Vetores de posicao: precisamos das posicoes 0, 1, 2...
# torch.arange(len) cria [0, 1, 2, ...] automaticamente.
posicoes = torch.arange(len(numeros))       # tensor([0, 1, 2])
vetores_posicao = emb_posicao(posicoes)     # formato (3, n_embd)

# A SOMA (elemento a elemento). O PyTorch soma os vetores
# alinhados por posicao automaticamente.
entrada_do_modelo = vetores_caractere + vetores_posicao

print("\n" + "-" * 55)
print(f"Texto: {texto!r}  ->  numeros: {numeros}")
print("-" * 55)
print(f"Formato caractere : {tuple(vetores_caractere.shape)}")
print(f"Formato posicao   : {tuple(vetores_posicao.shape)}")
print(f"Formato da soma   : {tuple(entrada_do_modelo.shape)}")
print("  (mesmo formato: entra (3,32) + (3,32), sai (3,32))")


# ------------------------------------------------------------
# 5. PROVA: MESMA LETRA, POSICOES DIFERENTES
# ------------------------------------------------------------
# Vamos olhar a letra 'a'. No texto "cab", o 'a' esta na
# posicao 1. Vamos comparar o vetor final dele na posicao 1
# com o que seria na posicao 0.
# Mostramos so os 4 primeiros numeros para facilitar a leitura.

idx_a = stoi["a"]
vetor_a = emb_caractere(torch.tensor(idx_a))   # so o caractere 'a'

a_na_pos0 = vetor_a + emb_posicao(torch.tensor(0))
a_na_pos1 = vetor_a + emb_posicao(torch.tensor(1))

print("\n" + "-" * 55)
print("MESMA LETRA 'a', POSICOES DIFERENTES (4 primeiros numeros)")
print("-" * 55)
print(f"'a' na posicao 0 : {a_na_pos0[:4].tolist()}")
print(f"'a' na posicao 1 : {a_na_pos1[:4].tolist()}")
print("  -> vetores diferentes! O modelo agora enxerga a ordem.")

print("\nEmbedding de posicao demonstrado!")
