"""
=============================================================
 DEMO 4 - FFN (feed-forward)  peca isolada do mini-GPT
=============================================================

 Objetivo:
   Ver a FFN processar um token:
     1. expandir  (linear: n_embd -> 4*n_embd)
     2. ReLU      (zera negativos)
     3. contrair  (linear: 4*n_embd -> n_embd)

 nn.Linear(entrada, saida) e a "tabela de pesos" que
 calculamos na mao. O PyTorch cria e gerencia ela sozinho.

=============================================================
"""

import torch
import torch.nn as nn


# ------------------------------------------------------------
# 1. AS DUAS CAMADAS LINEARES
# ------------------------------------------------------------
# n_embd     = tamanho do vetor do token (usamos 32 no projeto)
# n_oculto   = tamanho expandido (o padrao do transformer e 4x)
#
# nn.Linear(entrada, saida) cria a tabela de pesos:
#   - expandir : de n_embd  para n_oculto
#   - contrair : de n_oculto para n_embd

n_embd   = 32
n_oculto = 4 * n_embd   # 128

expandir = nn.Linear(n_embd, n_oculto)
contrair = nn.Linear(n_oculto, n_embd)
ativacao = nn.ReLU()

print("=" * 55)
print("DEMO 4 - FFN")
print("=" * 55)
print(f"n_embd (entrada/saida) : {n_embd}")
print(f"n_oculto (expandido)   : {n_oculto}")
print(f"\nTabela da camada 'expandir': {tuple(expandir.weight.shape)}")
print(f"  (saidas x entradas = {n_oculto} x {n_embd})")
print(f"Tabela da camada 'contrair': {tuple(contrair.weight.shape)}")
print(f"  (saidas x entradas = {n_embd} x {n_oculto})")


# ------------------------------------------------------------
# 2. PASSAR UM TOKEN PELA FFN
# ------------------------------------------------------------
# Criamos um vetor de token aleatorio (tamanho 32), so para
# ver o caminho. No modelo real, ele vem da atencao.

token = torch.randn(n_embd)   # 32 numeros aleatorios

print("\n" + "-" * 55)
print("PASSANDO UM TOKEN PELA FFN")
print("-" * 55)
print(f"Entrada  : vetor de tamanho {tuple(token.shape)}")

# Etapa 1: expandir
passo1 = expandir(token)
print(f"Apos expandir : tamanho {tuple(passo1.shape)}  (virou {n_oculto})")

# Etapa 2: ReLU (conta quantos viraram zero)
passo2 = ativacao(passo1)
zerados = (passo2 == 0).sum().item()
print(f"Apos ReLU     : tamanho {tuple(passo2.shape)}  ({zerados} de {n_oculto} viraram 0)")

# Etapa 3: contrair
saida = contrair(passo2)
print(f"Apos contrair : tamanho {tuple(saida.shape)}  (voltou a {n_embd})")

print("\n  Entrou vetor de 32 -> saiu vetor de 32, mas processado.")


# ------------------------------------------------------------
# 3. A FFN INTEIRA EM UMA LINHA (como fica no modelo)
# ------------------------------------------------------------
# nn.Sequential encadeia as etapas numa unica "peca".
# E assim que a FFN vai aparecer no modelo final.

ffn = nn.Sequential(
    nn.Linear(n_embd, n_oculto),
    nn.ReLU(),
    nn.Linear(n_oculto, n_embd),
)

saida2 = ffn(token)
print("-" * 55)
print("A FFN inteira como uma peca so (nn.Sequential):")
print(f"  entrada {tuple(token.shape)} -> saida {tuple(saida2.shape)}")
print("\nFFN demonstrada!")
