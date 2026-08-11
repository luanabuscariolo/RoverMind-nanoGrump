"""
=============================================================
 GERACAO de texto do nano-grump
=============================================================

 Carrega o modelo treinado e faz o robo "falar":
 para cada marcador de situacao, gera uma frase sarcastica,
 um caractere de cada vez (autorregressivo).

=============================================================
"""

import json
from pathlib import Path

import torch
import torch.nn.functional as F

from model import MiniGPT, block_size


device = "cuda" if torch.cuda.is_available() else "cpu"


# ------------------------------------------------------------
# TOKENIZER (encode e decode)
# ------------------------------------------------------------

pasta = Path(__file__).parent
caracteres = json.loads((pasta / "vocab.json").read_text(encoding="utf-8"))
stoi = {c: i for i, c in enumerate(caracteres)}
itos = {i: c for i, c in enumerate(caracteres)}

def encode(s): return [stoi[c] for c in s]
def decode(nums): return "".join(itos[n] for n in nums)


# ------------------------------------------------------------
# CARREGAR O MODELO TREINADO
# ------------------------------------------------------------

modelo = MiniGPT().to(device)
modelo.load_state_dict(torch.load(pasta / "modelo_treinado.pt", map_location=device))
modelo.eval()   # modo de avaliacao (desliga coisas de treino)


# ------------------------------------------------------------
# FUNCAO DE GERACAO (o ciclo autorregressivo)
# ------------------------------------------------------------

def gerar(prompt, max_novos=120, temperatura=0.8):
    # prompt vira numeros -> tensor (1, T)
    idx = torch.tensor([encode(prompt)], dtype=torch.long, device=device)

    for _ in range(max_novos):
        # corta o contexto para caber na janela (block_size)
        cond = idx[:, -block_size:]

        # o modelo preve
        with torch.no_grad():
            logits = modelo(cond)

        # pega so a ultima posicao (a previsao do proximo char)
        logits = logits[:, -1, :] / temperatura

        # vira probabilidades e sorteia 1 caractere
        probs = F.softmax(logits, dim=-1)
        prox = torch.multinomial(probs, num_samples=1)

        # anexa ao contexto
        idx = torch.cat([idx, prox], dim=1)

        # para se gerar uma quebra de linha (fim da frase)
        if prox.item() == stoi["\n"]:
            break

    return decode(idx[0].tolist())


# ------------------------------------------------------------
# FAZER O ROBO FALAR EM CADA SITUACAO
# ------------------------------------------------------------

marcadores = [
    "<start>", "<explore>", "<obstacle>", "<turn_left>",
    "<turn_right>", "<backup>", "<stuck>", "<clear>",
]

print("=" * 55)
print("   O NANO-GRUMP FALA")
print("=" * 55)

for m in marcadores:
    frase = gerar(m + " ")
    print(f"\n{frase.strip()}")
