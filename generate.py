"""
=============================================================
 GERACAO v2 do nano-grump
=============================================================

 Carrega o modelo treinado e faz o robo "falar":
 para cada marcador de situacao, gera frases sarcasticas,
 um caractere de cada vez (autorregressivo).

 MUDANCAS DA v2 (em relacao a v1):
   - le o vocab.json no formato novo (dict com metadados)
   - amostragem com TOP-K (corta caracteres improvaveis)
   - parametros configuraveis (temperatura, top_k, n por marcador)
   - gera VARIAS frases por marcador (para avaliar variedade)

 TOP-K em uma frase:
   em vez de sortear entre os 59 caracteres (incluindo os
   improvaveis que geram lixo), mantem so os k mais provaveis
   e zera o resto antes de sortear.

=============================================================
"""

import json
from pathlib import Path

import torch
import torch.nn.functional as F

from model import MiniGPT, block_size


device = "cuda" if torch.cuda.is_available() else "cpu"


# ------------------------------------------------------------
# PARAMETROS DE GERACAO (mexa aqui para comparar)
# ------------------------------------------------------------
# [ADICIONADO] tudo configuravel num lugar so.
#   temperatura : < 1 deixa mais "certinho"; > 1 mais "criativo"
#   top_k       : quantos caracteres mais provaveis manter
#   n_por_marcador : quantas frases gerar por marcador

TEMPERATURA    = 0.75    # [ALTERADO v2-final] 0.8 -> 0.75
TOP_K          = 4       # [ALTERADO v2-final] 5 -> 4 (config escolhida apos comparacao)
N_POR_MARCADOR = 3       # [ADICIONADO] 3 frases por marcador
MAX_NOVOS      = 120     # limite de caracteres por frase


# ------------------------------------------------------------
# TOKENIZER (encode e decode)
# ------------------------------------------------------------

pasta = Path(__file__).parent

# [ALTERADO] vocab.json agora e um dict; pegamos o campo "vocab".
_vocab_data = json.loads((pasta / "vocab.json").read_text(encoding="utf-8"))
caracteres = _vocab_data["vocab"]

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

def gerar(prompt, max_novos=MAX_NOVOS, temperatura=TEMPERATURA, top_k=TOP_K):
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

        # [ADICIONADO] TOP-K: mantem so os k maiores logits, e coloca
        # -inf no resto. Assim, os caracteres improvaveis nem entram
        # no sorteio (viram probabilidade zero apos o softmax).
        if top_k is not None:
            # topk devolve os k maiores valores; v[:, [-1]] e o menor
            # deles (o "corte"). Tudo abaixo do corte vira -inf.
            v, _ = torch.topk(logits, top_k)
            corte = v[:, [-1]]
            logits[logits < corte] = float("-inf")

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
print("   O NANO-GRUMP v2 FALA")
print("=" * 55)
print(f"   temperatura={TEMPERATURA}  top_k={TOP_K}  "
      f"({N_POR_MARCADOR} frases por marcador)")
print("=" * 55)

for m in marcadores:
    print(f"\n--- {m} ---")
    for _ in range(N_POR_MARCADOR):
        frase = gerar(m + " ")
        print(f"  {frase.strip()}")
