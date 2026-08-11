"""
=============================================================
 DEMO 5 - ATENCAO MULTI-CABECA  peca isolada do mini-GPT v2
=============================================================

 Objetivo:
   Ver, com numeros reais, como a atencao multi-cabeca:
     1. FATIA o vetor de cada token em pedacos (um por cabeca)
     2. roda a atencao COMPLETA e INDEPENDENTE em cada fatia
     3. CONCATENA os resultados de volta num vetor so
     4. passa por uma projecao final que mistura as cabecas

 Comparacao com o demo 3 (atencao single-head):
   - demo 3: UMA atencao usando o vetor inteiro
   - demo 5: VARIAS atencoes, cada uma numa fatia do vetor

 Usamos numeros pequenos (n_embd=8, n_heads=2) para conseguir
 acompanhar as contas a olho nu.

=============================================================
"""

import torch
import torch.nn.functional as F


# ------------------------------------------------------------
# 0. AS MEDIDAS DO DEMO
# ------------------------------------------------------------
# n_embd  = tamanho do vetor de cada token
# n_heads = quantas cabecas
# head_size = tamanho da fatia de cada cabeca (n_embd / n_heads)
#
# Regra importante: n_embd PRECISA ser divisivel por n_heads,
# senao as fatias nao ficam do mesmo tamanho.

n_embd  = 8
n_heads = 2
head_size = n_embd // n_heads   # 8 / 2 = 4

print("=" * 55)
print("DEMO 5 - ATENCAO MULTI-CABECA")
print("=" * 55)
print(f"n_embd    : {n_embd}   (tamanho do vetor de cada token)")
print(f"n_heads   : {n_heads}   (numero de cabecas)")
print(f"head_size : {head_size}   (fatia de cada cabeca = n_embd / n_heads)")


# ------------------------------------------------------------
# 1. O PONTO DE PARTIDA: 3 TOKENS
# ------------------------------------------------------------
# 3 tokens, cada um com um vetor de tamanho 8.
# Escolhidos a mao para os numeros serem faceis de seguir.

x = torch.tensor([
    [1.0, 0.5, -0.3, 0.8,   0.2, -0.1, 0.9, 0.4],   # token 0
    [0.0, 1.0,  0.2, 0.1,   0.7,  0.3, 0.1, 0.5],   # token 1
    [0.4, 0.4,  0.4, 0.4,   0.6,  0.6, 0.6, 0.6],   # token 2
])

n_tokens = x.shape[0]

print("\n" + "-" * 55)
print("1. OS 3 TOKENS (vetores de tamanho 8)")
print("-" * 55)
print(x)
print("  cada linha e um token; cada token tem 8 numeros")


# ------------------------------------------------------------
# 2. O FATIAMENTO: dividir os 8 numeros em 2 cabecas de 4
# ------------------------------------------------------------
# A cabeca 1 pega as colunas 0..3 de todos os tokens.
# A cabeca 2 pega as colunas 4..7 de todos os tokens.
#
# No modelo real, antes de fatiar, o vetor passa por camadas
# Linear (Q, K, V). Aqui, para focar no CONCEITO de fatiar,
# vamos usar o proprio x como se ja fosse Q=K=V. Simplificacao
# didatica: o que importa e ver a fatia virar uma atencao.

fatia_c1 = x[:, 0:4]    # cabeca 1: colunas 0,1,2,3
fatia_c2 = x[:, 4:8]    # cabeca 2: colunas 4,5,6,7

print("\n" + "-" * 55)
print("2. FATIAMENTO (cada cabeca pega 4 das 8 colunas)")
print("-" * 55)
print("Cabeca 1 (colunas 0-3):")
print(fatia_c1)
print("\nCabeca 2 (colunas 4-7):")
print(fatia_c2)


# ------------------------------------------------------------
# 3. A ATENCAO DE UMA CABECA (a mesma conta do demo 3)
# ------------------------------------------------------------
# Recebe uma fatia (n_tokens, head_size) e roda:
#   Q.K^T -> escala -> mascara causal -> softmax -> .V
# Aqui, como simplificacao, usamos Q = K = V = fatia.

def atencao_de_uma_cabeca(fatia):
    dk = fatia.shape[1]   # head_size = 4

    # 1. produto escalar Q.K^T -> notas (n_tokens, n_tokens)
    notas = fatia @ fatia.transpose(-2, -1) / (dk ** 0.5)

    # 2. mascara causal: cada token so ve a si mesmo e os anteriores
    triangulo = torch.tril(torch.ones(n_tokens, n_tokens))
    notas = notas.masked_fill(triangulo == 0, float("-inf"))

    # 3. softmax -> pesos que somam 1 por linha
    pesos = F.softmax(notas, dim=-1)

    # 4. soma ponderada dos values
    saida = pesos @ fatia

    return saida, pesos


# ------------------------------------------------------------
# 4. RODAR A ATENCAO EM CADA CABECA (independente!)
# ------------------------------------------------------------

saida_c1, pesos_c1 = atencao_de_uma_cabeca(fatia_c1)
saida_c2, pesos_c2 = atencao_de_uma_cabeca(fatia_c2)

print("\n" + "-" * 55)
print("3. ATENCAO RODANDO EM CADA CABECA (independentemente)")
print("-" * 55)

print("\nCABECA 1 - pesos de atencao (quem olha para quem):")
print(pesos_c1.round(decimals=3))
print("CABECA 1 - saida (fatia processada):")
print(saida_c1.round(decimals=3))

print("\nCABECA 2 - pesos de atencao (quem olha para quem):")
print(pesos_c2.round(decimals=3))
print("CABECA 2 - saida (fatia processada):")
print(saida_c2.round(decimals=3))

print("\n  Repare: as duas cabecas produziram pesos DIFERENTES.")
print("  Cada uma 'enxergou' as relacoes entre tokens a seu modo.")


# ------------------------------------------------------------
# 5. CONCATENAR: colar as fatias de volta num vetor de 8
# ------------------------------------------------------------
# torch.cat junta as saidas lado a lado (dim=-1 = colunas).
# Cabeca 1 (4 numeros) + cabeca 2 (4 numeros) = 8 numeros.

resultado = torch.cat([saida_c1, saida_c2], dim=-1)

print("\n" + "-" * 55)
print("4. CONCATENACAO (colar as cabecas de volta)")
print("-" * 55)
print(resultado.round(decimals=3))
print(f"  formato: {tuple(resultado.shape)}  (voltou a ter 8 colunas)")
print("  as primeiras 4 colunas vieram da cabeca 1,")
print("  as ultimas 4 colunas vieram da cabeca 2.")


# ------------------------------------------------------------
# 6. RESUMO DO FLUXO
# ------------------------------------------------------------

print("\n" + "=" * 55)
print("RESUMO DO FLUXO")
print("=" * 55)
print("  vetor de 8")
print("     -> fatia em 2 pedacos de 4")
print("     -> atencao independente em cada pedaco")
print("     -> concatena de volta em 8")
print("     -> (no modelo real) uma projecao final mistura tudo")
print()
print("  Custo parecido com 1 atencao, mas com 2 perspectivas.")
print("=" * 55)
