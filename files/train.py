"""
=============================================================
 TREINO do nano-grump
=============================================================

 O laco do treino:
   1. pega um lote de exemplos (entrada x, resposta y)
   2. o modelo preve (forward)
   3. mede o erro com cross-entropy (loss)
   4. calcula os gradientes (loss.backward)
   5. ajusta os pesos (optimizer.step)
   6. repete

 No fim, salva os pesos treinados em modelo_treinado.pt

=============================================================
"""

import json
from pathlib import Path

import torch
import torch.nn.functional as F

from model import MiniGPT, block_size


# ------------------------------------------------------------
# CONFIGURACOES DO TREINO
# ------------------------------------------------------------

batch_size = 32       # quantos exemplos por passo
max_iters  = 3000     # quantos passos de treino
lr         = 1e-3     # taxa de aprendizado (tamanho do passo)
eval_cada  = 300      # de quantos em quantos passos mostrar o erro

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Treinando em: {device}")


# ------------------------------------------------------------
# CARREGAR DADOS E TOKENIZER
# ------------------------------------------------------------

pasta = Path(__file__).parent
caracteres = json.loads((pasta / "vocab.json").read_text(encoding="utf-8"))
stoi = {c: i for i, c in enumerate(caracteres)}

texto = (pasta / "data" / "robot_voice.txt").read_text(encoding="utf-8")

# Todo o dataset vira uma unica sequencia de numeros.
dados = torch.tensor([stoi[c] for c in texto], dtype=torch.long)
print(f"Dataset: {len(dados)} tokens")


# ------------------------------------------------------------
# FUNCAO QUE PEGA UM LOTE
# ------------------------------------------------------------
# Sorteia posicoes aleatorias e monta os pares (x, y),
# onde y e o x deslocado 1 caractere para a frente.

def pegar_lote():
    # posicoes iniciais aleatorias
    ini = torch.randint(len(dados) - block_size, (batch_size,))
    x = torch.stack([dados[i     : i + block_size]     for i in ini])
    y = torch.stack([dados[i + 1 : i + block_size + 1] for i in ini])
    return x.to(device), y.to(device)


# ------------------------------------------------------------
# CRIAR O MODELO E O OTIMIZADOR
# ------------------------------------------------------------

modelo = MiniGPT().to(device)

# AdamW = o "otimizador", quem da o passo de descida do gradiente.
otimizador = torch.optim.AdamW(modelo.parameters(), lr=lr)


# ------------------------------------------------------------
# O LACO DE TREINO
# ------------------------------------------------------------

print("\nIniciando treino...\n")

for passo in range(max_iters + 1):
    # 1. pega um lote
    x, y = pegar_lote()

    # 2. o modelo preve -> logits (B, T, vocab)
    logits = modelo(x)

    # 3. mede o erro (cross-entropy)
    #    reorganizamos para (B*T, vocab) e (B*T,) que e o formato
    #    que a cross_entropy espera.
    B, T, V = logits.shape
    loss = F.cross_entropy(logits.view(B * T, V), y.view(B * T))

    # 4. zera gradientes antigos e calcula os novos
    otimizador.zero_grad()
    loss.backward()

    # 5. ajusta os pesos
    otimizador.step()

    # mostra o erro de tempos em tempos
    if passo % eval_cada == 0:
        print(f"passo {passo:5d}  |  erro (loss): {loss.item():.4f}")

print("\nTreino terminado!")


# ------------------------------------------------------------
# SALVAR OS PESOS TREINADOS
# ------------------------------------------------------------

caminho_modelo = pasta / "modelo_treinado.pt"
torch.save(modelo.state_dict(), caminho_modelo)
print(f"Pesos salvos em: {caminho_modelo.name}")
