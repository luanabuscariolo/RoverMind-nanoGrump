"""
=============================================================
 DEMO 3 - ATENCAO (self-attention)  peca isolada do mini-GPT
=============================================================

 Objetivo:
   Ver, com numeros reais, as etapas da atencao:
     1. produto escalar (Q . K)  -> notas
     2. escala (dividir por raiz de dk)
     3. mascara causal (futuro vira -infinito)
     4. softmax                   -> pesos (somam 1)
     5. soma ponderada dos Values -> saida

 Usamos numeros pequenos e escolhidos a mao, para os
 valores serem faceis de acompanhar.

=============================================================
"""

import torch
import torch.nn.functional as F


# ------------------------------------------------------------
# 0. O PONTO DE PARTIDA
# ------------------------------------------------------------
# 3 tokens, e vetores Q/K/V de tamanho 2 (dk = 2).
# No modelo real, Q/K/V saem de camadas Linear aplicadas ao
# vetor do token. Aqui colocamos a mao para enxergar as contas.

Q = torch.tensor([[2., 0.],
                  [0., 2.],
                  [1., 1.]])

K = torch.tensor([[1., 0.],
                  [0., 1.],
                  [1., 1.]])

V = torch.tensor([[10.,  0.],
                  [ 0., 10.],
                  [ 5.,  5.]])

dk = Q.shape[1]   # tamanho do vetor = 2

print("=" * 55)
print("DEMO 3 - ATENCAO")
print("=" * 55)
print("Q (queries):\n", Q)
print("K (keys):\n", K)
print("V (values):\n", V)


# ------------------------------------------------------------
# 1. PRODUTO ESCALAR:  notas = Q . K^T
# ------------------------------------------------------------
# Cada linha i, coluna j = quanto o token i "casa" com o j.
# K.T (transposta) alinha as dimensoes para a multiplicacao.

notas = Q @ K.T

print("\n" + "-" * 55)
print("1. NOTAS (produto escalar Q . K^T)")
print("-" * 55)
print(notas)
print("  linha i, coluna j = quanto o token i casa com o token j")


# ------------------------------------------------------------
# 2. ESCALA:  dividir por raiz de dk
# ------------------------------------------------------------
# Estabiliza os numeros antes do softmax.

notas_escaladas = notas / (dk ** 0.5)

print("\n" + "-" * 55)
print(f"2. NOTAS ESCALADAS (dividido por raiz de {dk} = {dk**0.5:.3f})")
print("-" * 55)
print(notas_escaladas)


# ------------------------------------------------------------
# 3. MASCARA CAUSAL:  futuro vira -infinito
# ------------------------------------------------------------
# torch.tril = pega o triangulo inferior (a diagonal e abaixo).
# Onde NAO e permitido (futuro), colocamos -infinito.

n_tokens = Q.shape[0]
triangulo = torch.tril(torch.ones(n_tokens, n_tokens))  # 1 = permitido

notas_mascaradas = notas_escaladas.masked_fill(
    triangulo == 0,          # onde o triangulo e 0 (futuro)
    float("-inf")            # coloca -infinito
)

print("\n" + "-" * 55)
print("3. COM MASCARA CAUSAL (futuro = -inf)")
print("-" * 55)
print(notas_mascaradas)
print("  repare no triangulo de cima preenchido com -inf")


# ------------------------------------------------------------
# 4. SOFTMAX:  vira pesos que somam 1 (por linha)
# ------------------------------------------------------------
# dim=-1 aplica o softmax em cada linha separadamente.
# -inf vira 0 automaticamente (e^-inf = 0).

pesos = F.softmax(notas_mascaradas, dim=-1)

print("\n" + "-" * 55)
print("4. PESOS (softmax por linha)")
print("-" * 55)
print(pesos.round(decimals=3))
print("  triangular! cada linha soma 1:", pesos.sum(dim=-1).tolist())


# ------------------------------------------------------------
# 5. SOMA PONDERADA DOS VALUES:  saida = pesos . V
# ------------------------------------------------------------
# Cada token vira uma mistura dos Values, conforme seus pesos.

saida = pesos @ V

print("\n" + "-" * 55)
print("5. SAIDA (pesos . V) - o novo vetor de cada token")
print("-" * 55)
print(saida.round(decimals=3))

print("\n" + "=" * 55)
print("Leitura do resultado:")
print("  token 1 so viu a si mesmo  -> saida = V do token 1 = [10, 0]")
print("  token 2 misturou 1 e 2")
print("  token 3 misturou 1, 2 e 3")
print("=" * 55)
