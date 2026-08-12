"""
=============================================================
 EXPORTADOR DE PESOS  -  nano-grump
=============================================================

 Traduz o modelo_treinado.pt (formato PyTorch, so o Python
 entende) para um arquivo nano-grump.bin (bytes puros, que
 o firmware C do ESP32-S3 consegue ler).

 O arquivo .bin tem dois blocos, nesta ordem:

   [CABECALHO]  informacoes do modelo (tamanhos, dimensoes)
   [PESOS]      os 211.003 numeros, em ordem fixa

 O firmware C do ESP32-S3 le nessa mesma ordem.
 A ordem tem que ser identica nos dois lados.

 Como usar:
   uv run export.py

 Saida:
   nano-grump.bin  (~844 KB, pronto para gravar no ESP32-S3)

=============================================================
"""

import json
import struct
from pathlib import Path

import torch

from model import MiniGPT, vocab_size, n_embd, block_size, n_layer, n_heads


# ------------------------------------------------------------
# CAMINHOS
# ------------------------------------------------------------

pasta          = Path(__file__).parent
caminho_modelo = pasta / "modelo_treinado.pt"
caminho_saida  = pasta / "nano-grump.bin"


# ------------------------------------------------------------
# 1. CARREGAR O MODELO TREINADO
# ------------------------------------------------------------

print("=" * 55)
print("EXPORTADOR DE PESOS  -  nano-grump")
print("=" * 55)

modelo = MiniGPT()
modelo.load_state_dict(
    torch.load(caminho_modelo, map_location="cpu")
)
modelo.eval()
print(f"Modelo carregado: {caminho_modelo.name}")


# ------------------------------------------------------------
# FUNCAO AUXILIAR: tensor -> bytes float32
# ------------------------------------------------------------
# Converte um tensor PyTorch para uma sequencia de bytes no
# formato float32 (4 bytes por numero).
#
# .detach()        : desliga o calculo de gradiente (nao precisamos)
# .cpu()           : garante que esta na RAM, nao na GPU
# .numpy()         : converte para array NumPy
# .astype("f")     : converte cada numero para float32 (4 bytes)
# .tobytes()       : vira bytes puros, prontos para gravar no arquivo

def para_bytes(tensor):
    return tensor.detach().cpu().numpy().astype("f").tobytes()


# ------------------------------------------------------------
# 2. ESCREVER O ARQUIVO .bin
# ------------------------------------------------------------

with open(caminho_saida, "wb") as f:   # "wb" = write binary (escrita de bytes)

    # --------------------------------------------------------
    # BLOCO 1: CABECALHO
    # --------------------------------------------------------
    # Escrevemos 6 numeros inteiros (4 bytes cada = 24 bytes no total).
    # O firmware C le esses 6 inteiros primeiro para saber as
    # dimensoes do modelo antes de ler os pesos.
    #
    # struct.pack("6i", ...) = empacota 6 inteiros em bytes.
    # "i" = inteiro de 32 bits com sinal (int no C).

    cabecalho = struct.pack(
        "6i",
        vocab_size,   # quantos caracteres no vocabulario (59)
        n_embd,       # tamanho do vetor de cada token (64)
        block_size,   # janela de contexto (64)
        n_layer,      # numero de blocos (4)
        n_heads,      # numero de cabecas de atencao (4)
        0,            # reservado para uso futuro (ex: versao)
    )
    f.write(cabecalho)
    print(f"\nCabecalho escrito ({len(cabecalho)} bytes):")
    print(f"  vocab_size = {vocab_size}")
    print(f"  n_embd     = {n_embd}")
    print(f"  block_size = {block_size}")
    print(f"  n_layer    = {n_layer}")
    print(f"  n_heads    = {n_heads}")

    # --------------------------------------------------------
    # BLOCO 2: PESOS
    # --------------------------------------------------------
    # Escrevemos os 211.003 numeros em ordem fixa.
    # O firmware C vai ler nessa mesma ordem para reconstruir
    # cada camada do modelo.
    #
    # A ordem e:
    #   1. embedding de token
    #   2. embedding de posicao
    #   3. para cada bloco (0 a n_layer-1):
    #        layernorm 1 (peso + bias)
    #        atencao: query, chave, value, proj
    #        layernorm 2 (peso + bias)
    #        ffn: expandir (peso + bias), contrair (peso + bias)
    #   4. layernorm final (peso + bias)
    #   5. camada de saida (peso)

    total_bytes = 0

    # 1. embeddings
    f.write(para_bytes(modelo.emb_token.weight))
    f.write(para_bytes(modelo.emb_posicao.weight))
    total_bytes += modelo.emb_token.weight.numel()
    total_bytes += modelo.emb_posicao.weight.numel()

    # 2. blocos (0 a n_layer-1)
    for i, bloco in enumerate(modelo.blocos):
        # layernorm 1
        f.write(para_bytes(bloco.ln1.weight))
        f.write(para_bytes(bloco.ln1.bias))
        # atencao: query, chave, value, projecao
        f.write(para_bytes(bloco.atencao.query.weight))
        f.write(para_bytes(bloco.atencao.chave.weight))
        f.write(para_bytes(bloco.atencao.value.weight))
        f.write(para_bytes(bloco.atencao.proj.weight))
        f.write(para_bytes(bloco.atencao.proj.bias))
        # layernorm 2
        f.write(para_bytes(bloco.ln2.weight))
        f.write(para_bytes(bloco.ln2.bias))
        # ffn: expandir e contrair (pesos e bias)
        f.write(para_bytes(bloco.ffn.rede[0].weight))
        f.write(para_bytes(bloco.ffn.rede[0].bias))
        f.write(para_bytes(bloco.ffn.rede[2].weight))
        f.write(para_bytes(bloco.ffn.rede[2].bias))

        params_bloco = (
            bloco.ln1.weight.numel() + bloco.ln1.bias.numel() +
            bloco.atencao.query.weight.numel() +
            bloco.atencao.chave.weight.numel() +
            bloco.atencao.value.weight.numel() +
            bloco.atencao.proj.weight.numel() +
            bloco.atencao.proj.bias.numel() +
            bloco.ln2.weight.numel() + bloco.ln2.bias.numel() +
            bloco.ffn.rede[0].weight.numel() +
            bloco.ffn.rede[0].bias.numel() +
            bloco.ffn.rede[2].weight.numel() +
            bloco.ffn.rede[2].bias.numel()
        )
        total_bytes += params_bloco
        print(f"  bloco {i} exportado  ({params_bloco:,} params)")

    # 3. layernorm final
    f.write(para_bytes(modelo.ln_final.weight))
    f.write(para_bytes(modelo.ln_final.bias))
    total_bytes += modelo.ln_final.weight.numel()
    total_bytes += modelo.ln_final.bias.numel()

    # 4. camada de saida (sem bias, por padrao do PyTorch)
    f.write(para_bytes(modelo.saida.weight))
    total_bytes += modelo.saida.weight.numel()


# ------------------------------------------------------------
# RELATORIO FINAL
# ------------------------------------------------------------

tamanho_arquivo = caminho_saida.stat().st_size
print(f"\nPesos exportados : {total_bytes:,} numeros")
print(f"Tamanho do .bin  : {tamanho_arquivo:,} bytes "
      f"({tamanho_arquivo / 1024:.1f} KB)")
print(f"Arquivo salvo em : {caminho_saida.name}")
print("\nPronto para gravar no ESP32-S3.")
