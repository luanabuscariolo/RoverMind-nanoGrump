"""
=============================================================
 TREINO v2 do nano-grump
=============================================================

 O laco do treino (o coracao continua o mesmo):
   1. pega um lote de exemplos (entrada x, resposta y)
   2. o modelo preve (forward)
   3. mede o erro com cross-entropy (loss)
   4. calcula os gradientes (loss.backward)
   5. ajusta os pesos (optimizer.step)
   6. repete

 MUDANCAS DA v2 (em relacao a v1):
   - le o vocab.json no formato novo (dict com metadados)
   - usa o dataset expandido (robot_voice_final.txt)
   - SPLIT treino/validacao (90/10) para detectar overfitting
   - mede train E val loss (media de varios lotes, nao 1 so)
   - max_iters 3000 -> 8000
   - AdamW com weight_decay (regularizacao)
   - salva o MELHOR modelo (quando a val loss melhora),
     nao apenas o ultimo
   - semente fixa para reprodutibilidade

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

batch_size    = 32       # quantos exemplos por passo
max_iters     = 8000     # [ALTERADO] 3000 -> 8000 (dataset maior)
lr            = 1e-3     # taxa de aprendizado (tamanho do passo)
weight_decay  = 0.01     # [ADICIONADO] regularizacao do AdamW
eval_cada     = 500      # [ALTERADO] 300 -> 500 (medir de 500 em 500)
eval_lotes    = 50       # [ADICIONADO] quantos lotes usar para medir a loss
frac_treino   = 0.9      # [ADICIONADO] 90% treino, 10% validacao

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Treinando em: {device}")

# [ADICIONADO] semente fixa: garante que o treino seja reproduzivel
# (mesma sequencia de sorteios toda vez que rodar).
torch.manual_seed(1337)


# ------------------------------------------------------------
# CARREGAR DADOS E TOKENIZER
# ------------------------------------------------------------

pasta = Path(__file__).parent

# [ALTERADO] vocab.json agora e um dict {"version","type","vocab_size","vocab"}.
# Antes: caracteres = json.loads(...) direto (era uma lista).
# Agora: pegamos o campo "vocab" de dentro do dict.
_vocab_data = json.loads((pasta / "vocab.json").read_text(encoding="utf-8"))
caracteres = _vocab_data["vocab"]
stoi = {c: i for i, c in enumerate(caracteres)}

# [ALTERADO] dataset: robot_voice.txt -> robot_voice_final.txt
texto = (pasta / "data" / "robot_voice_final.txt").read_text(encoding="utf-8")

# Todo o dataset vira uma unica sequencia de numeros.
dados = torch.tensor([stoi[c] for c in texto], dtype=torch.long)
print(f"Dataset: {len(dados)} tokens")


# ------------------------------------------------------------
# SPLIT TREINO / VALIDACAO
# ------------------------------------------------------------
# [ADICIONADO] separamos os dados em duas partes:
#   - treino    : o modelo aprende com ela
#   - validacao : o modelo NUNCA treina nela; usamos so para medir
#                 se ele esta generalizando (e nao apenas decorando).
#
# Como comparar:
#   train loss cai + val loss cai   -> bom, esta aprendendo
#   train loss cai + val loss sobe  -> overfitting (decorando)
#
# OBS: com dataset pequeno, a val loss e um pouco ruidosa. Ela
# ganha poder de diagnostico conforme o dataset cresce - mas ja
# vale como bussola.

n = int(frac_treino * len(dados))
dados_treino = dados[:n]
dados_val    = dados[n:]
print(f"Treino   : {len(dados_treino)} tokens")
print(f"Validacao: {len(dados_val)} tokens")


# ------------------------------------------------------------
# FUNCAO QUE PEGA UM LOTE
# ------------------------------------------------------------
# [ALTERADO] agora recebe qual split usar ("treino" ou "val").
# O resto e igual a v1: sorteia posicoes e monta pares (x, y),
# onde y e o x deslocado 1 caractere para a frente.

def pegar_lote(split):
    fonte = dados_treino if split == "treino" else dados_val
    ini = torch.randint(len(fonte) - block_size, (batch_size,))
    x = torch.stack([fonte[i     : i + block_size]     for i in ini])
    y = torch.stack([fonte[i + 1 : i + block_size + 1] for i in ini])
    return x.to(device), y.to(device)


# ------------------------------------------------------------
# FUNCAO QUE MEDE A LOSS (sem treinar)
# ------------------------------------------------------------
# [ADICIONADO] mede a loss media em varios lotes, para os dois
# splits. Usa media de eval_lotes lotes para reduzir o ruido de
# medir num lote so.
#
# @torch.no_grad(): desliga o calculo de gradientes. Nao vamos
#   treinar aqui, so medir - entao economizamos memoria e tempo.
# modelo.eval() / modelo.train(): alternam o modo do modelo.
#   Alguns componentes (como dropout) se comportam diferente em
#   treino e avaliacao. Nosso modelo ainda nao tem dropout, mas
#   ja deixamos o habito correto.

@torch.no_grad()
def medir_loss():
    resultado = {}
    modelo.eval()                       # modo avaliacao
    for split in ["treino", "val"]:
        perdas = torch.zeros(eval_lotes)
        for k in range(eval_lotes):
            x, y = pegar_lote(split)
            logits = modelo(x)
            B, T, V = logits.shape
            loss = F.cross_entropy(logits.view(B * T, V), y.view(B * T))
            perdas[k] = loss.item()
        resultado[split] = perdas.mean().item()
    modelo.train()                      # volta ao modo treino
    return resultado


# ------------------------------------------------------------
# CRIAR O MODELO E O OTIMIZADOR
# ------------------------------------------------------------

modelo = MiniGPT().to(device)

# [ALTERADO] AdamW agora com weight_decay (regularizacao).
otimizador = torch.optim.AdamW(
    modelo.parameters(), lr=lr, weight_decay=weight_decay
)


# ------------------------------------------------------------
# O LACO DE TREINO
# ------------------------------------------------------------

print("\nIniciando treino...\n")

# [ADICIONADO] guardamos a melhor val loss vista ate agora, para
# salvar o modelo so quando ele melhora de verdade.
melhor_val = float("inf")
caminho_melhor = pasta / "modelo_treinado.pt"

for passo in range(max_iters + 1):
    # Mede e reporta de tempos em tempos.
    if passo % eval_cada == 0:
        losses = medir_loss()
        marca = ""
        # [ADICIONADO] se a val loss melhorou, salva o modelo agora.
        if losses["val"] < melhor_val:
            melhor_val = losses["val"]
            torch.save(modelo.state_dict(), caminho_melhor)
            marca = "  <- melhor ate agora (salvo)"
        print(f"passo {passo:5d}  |  treino: {losses['treino']:.4f}  "
              f"|  val: {losses['val']:.4f}{marca}")

    # 1. pega um lote de TREINO
    x, y = pegar_lote("treino")

    # 2. o modelo preve -> logits (B, T, vocab)
    logits = modelo(x)

    # 3. mede o erro (cross-entropy)
    B, T, V = logits.shape
    loss = F.cross_entropy(logits.view(B * T, V), y.view(B * T))

    # 4. zera gradientes antigos e calcula os novos
    otimizador.zero_grad()
    loss.backward()

    # 5. ajusta os pesos
    otimizador.step()

print("\nTreino terminado!")
print(f"Melhor val loss: {melhor_val:.4f}")
print(f"Melhor modelo salvo em: {caminho_melhor.name}")
