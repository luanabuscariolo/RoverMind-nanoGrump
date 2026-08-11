"""
=============================================================
 MINI-GPT v2  -  o modelo completo do nano-grump
=============================================================

 Junta todas as pecas que construimos nos demos:
   - emb_token   : demo 1 (embedding de caractere)
   - emb_posicao : demo 2 (embedding de posicao)
   - Atencao     : demo 3 + demo 5 (self-attention MULTI-CABECA)
   - FFN         : demo 4 (feed-forward)
   - Bloco       : atencao + FFN, com LayerNorm e residual
   - MiniGPT     : embeddings -> blocos -> saida

 MUDANCAS DA v2 (em relacao a v1):
   - vocab_size agora e LIDO do vocab.json (nao mais fixo em 59)
   - n_embd     : 32 -> 64
   - block_size : 32 -> 64
   - n_layer    : 3  -> 4
   - n_heads    : NOVO (4 cabecas de atencao)
   - Atencao    : reescrita de single-head para MULTI-CABECA

=============================================================
"""

import json                          # [ADICIONADO] para ler o vocab.json
from pathlib import Path             # [ADICIONADO] para achar o vocab.json

import torch
import torch.nn as nn
import torch.nn.functional as F


# ------------------------------------------------------------
# HIPERPARAMETROS (as "medidas" do modelo)
# ------------------------------------------------------------

# [ALTERADO] vocab_size era fixo em 59. Agora e lido do vocab.json
# gerado pelo tokenizer. Assim, se o dataset mudar e o vocabulario
# crescer, o modelo se ajusta sozinho (sem quebrar silenciosamente).
#
# O vocab.json v2 e um dict: {"version", "type", "vocab_size", "vocab"}.
# Lemos o campo "vocab_size" diretamente.
_caminho_vocab = Path(__file__).parent / "vocab.json"
_vocab_data = json.loads(_caminho_vocab.read_text(encoding="utf-8"))
vocab_size = _vocab_data["vocab_size"]     # [ALTERADO] antes: vocab_size = 59

n_embd     = 64     # [ALTERADO] 32 -> 64  (tamanho do vetor de cada token)
block_size = 64     # [ALTERADO] 32 -> 64  (janela de contexto)
n_layer    = 4      # [ALTERADO] 3  -> 4   (numero de blocos empilhados)
n_heads    = 4      # [ADICIONADO] numero de cabecas de atencao

# Seguranca: n_embd precisa ser divisivel por n_heads, senao as
# fatias das cabecas nao ficam do mesmo tamanho.
assert n_embd % n_heads == 0, "n_embd precisa ser divisivel por n_heads"


# ============================================================
# ATENCAO MULTI-CABECA  (demo 3 + demo 5 viraram esta classe)
# ============================================================
# Diferenca para a v1 (single-head):
#   v1: uma atencao usando o vetor inteiro (64 numeros).
#   v2: 4 cabecas, cada uma cuidando de 64/4 = 16 numeros,
#       rodando atencao em paralelo, e depois concatenando.
#
# Truque de eficiencia: em vez de fatiar "na mao" (como no demo 5),
# usamos .view() + .transpose() para criar uma dimensao de cabecas
# e deixar o PyTorch rodar as 4 atencoes de uma vez so.

class Atencao(nn.Module):
    def __init__(self):
        super().__init__()
        # As tres "vistas" do token: query, key, value.
        # Note que continuam do tamanho n_embd INTEIRO (64).
        # O fatiamento em cabecas acontece DEPOIS, no forward.
        self.query = nn.Linear(n_embd, n_embd, bias=False)
        self.chave = nn.Linear(n_embd, n_embd, bias=False)
        self.value = nn.Linear(n_embd, n_embd, bias=False)

        # Projecao de saida (mistura o resultado das cabecas).
        self.proj  = nn.Linear(n_embd, n_embd)

        # [ADICIONADO] guardamos o tamanho de cada cabeca.
        self.head_size = n_embd // n_heads   # 64 / 4 = 16

        # Mascara causal triangular (igual a v1).
        self.register_buffer(
            "mascara",
            torch.tril(torch.ones(block_size, block_size))
        )

    def forward(self, x):
        B, T, C = x.shape          # (lote, tokens, n_embd=64)

        # 1. Q, K, V para o vetor inteiro (B, T, C).
        q = self.query(x)
        k = self.chave(x)
        v = self.value(x)

        # 2. [MULTI-CABECA] fatiar C em (n_heads, head_size) e mover
        #    a dimensao das cabecas para a frente. Isso transforma:
        #       (B, T, C)  ->  (B, n_heads, T, head_size)
        #
        #    view(...)     : quebra a ultima dimensao 64 em (4, 16)
        #    transpose(1,2): troca a posicao dos tokens e das cabecas,
        #                    para cada cabeca virar um "lote" proprio.
        #
        #    Resultado: o PyTorch roda as 4 atencoes em paralelo,
        #    cada uma trabalhando so na sua fatia de 16 numeros.
        q = q.view(B, T, n_heads, self.head_size).transpose(1, 2)
        k = k.view(B, T, n_heads, self.head_size).transpose(1, 2)
        v = v.view(B, T, n_heads, self.head_size).transpose(1, 2)
        # agora q, k, v tem formato (B, n_heads, T, head_size)

        # 3. produto escalar + escala -> notas (B, n_heads, T, T)
        #    A conta e a MESMA do demo 3, mas agora com a dimensao
        #    extra das cabecas. Escalamos por raiz de head_size
        #    (16), nao mais por C inteiro.
        notas = q @ k.transpose(-2, -1) / (self.head_size ** 0.5)

        # 4. mascara causal: futuro vira -inf (igual a v1).
        notas = notas.masked_fill(
            self.mascara[:T, :T] == 0,
            float("-inf")
        )

        # 5. softmax -> pesos que somam 1 (por linha, em cada cabeca)
        pesos = F.softmax(notas, dim=-1)

        # 6. soma ponderada dos values (B, n_heads, T, head_size)
        saida = pesos @ v

        # 7. [MULTI-CABECA] CONCATENAR as cabecas de volta:
        #    desfaz o transpose e "cola" as fatias, voltando a (B, T, C).
        #    contiguous() reorganiza a memoria para o view funcionar.
        saida = saida.transpose(1, 2).contiguous().view(B, T, C)

        # 8. projecao final (mistura o que as cabecas produziram)
        return self.proj(saida)


# ============================================================
# FFN  (o demo 4 virou uma classe)  -  INALTERADA na v2
# ============================================================

class FFN(nn.Module):
    def __init__(self):
        super().__init__()
        self.rede = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd),   # expandir
            nn.ReLU(),                        # cortar negativos
            nn.Linear(4 * n_embd, n_embd),   # contrair
        )

    def forward(self, x):
        return self.rede(x)


# ============================================================
# BLOCO  (atencao + FFN, com LayerNorm e residual)  -  INALTERADO
# ============================================================

class Bloco(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1     = nn.LayerNorm(n_embd)   # antes da atencao
        self.atencao = Atencao()
        self.ln2     = nn.LayerNorm(n_embd)   # antes da FFN
        self.ffn     = FFN()

    def forward(self, x):
        # Padrao pre-norm com residual (o "atalho" e o x + ...):
        x = x + self.atencao(self.ln1(x))   # sub-camada 1
        x = x + self.ffn(self.ln2(x))       # sub-camada 2
        return x


# ============================================================
# MINI-GPT  (o modelo completo)  -  quase inalterado
# ============================================================

class MiniGPT(nn.Module):
    def __init__(self):
        super().__init__()
        # Os dois embeddings.
        self.emb_token   = nn.Embedding(vocab_size, n_embd)
        self.emb_posicao = nn.Embedding(block_size, n_embd)

        # Os blocos empilhados (agora n_layer=4).
        self.blocos = nn.Sequential(*[Bloco() for _ in range(n_layer)])

        # LayerNorm final + camada de saida.
        self.ln_final = nn.LayerNorm(n_embd)
        self.saida    = nn.Linear(n_embd, vocab_size)

    def forward(self, idx):
        B, T = idx.shape

        # Embeddings: quem e cada token + onde ele esta.
        tok = self.emb_token(idx)                                   # (B, T, C)
        pos = self.emb_posicao(torch.arange(T, device=idx.device)) # (T, C)
        x = tok + pos                                               # soma (broadcast)

        # Passa pelos blocos, depois norma final.
        x = self.blocos(x)
        x = self.ln_final(x)

        # Camada de saida: uma nota (logit) para cada caractere.
        logits = self.saida(x)                                     # (B, T, vocab)
        return logits


# ============================================================
# TESTE RAPIDO (roda so se executar este arquivo direto)
# ============================================================

if __name__ == "__main__":
    modelo = MiniGPT()

    # Conta os parametros (numeros aprendiveis do modelo).
    n_params = sum(p.numel() for p in modelo.parameters())

    print("=" * 55)
    print("MINI-GPT v2 montado!")
    print("=" * 55)
    print(f"vocab_size : {vocab_size}   (lido do vocab.json)")
    print(f"n_embd     : {n_embd}")
    print(f"block_size : {block_size}")
    print(f"n_layer    : {n_layer}")
    print(f"n_heads    : {n_heads}   (cada cabeca cuida de {n_embd // n_heads} numeros)")
    print(f"\nParametros treinaveis: {n_params:,}")

    # Passa um lote falso pelo modelo para ver o formato da saida.
    idx_falso = torch.randint(0, vocab_size, (2, 8))
    logits = modelo(idx_falso)

    print(f"\nEntrada  : {tuple(idx_falso.shape)}  (2 sequencias de 8 tokens)")
    print(f"Saida    : {tuple(logits.shape)}  (2 x 8 x {vocab_size})")
    print(f"  -> para cada token, {vocab_size} notas (uma por caractere possivel)")

    if torch.cuda.is_available():
        modelo = modelo.to("cuda")
        idx_gpu = idx_falso.to("cuda")
        logits_gpu = modelo(idx_gpu)
        print(f"\nRodou na GPU? Sim -> {logits_gpu.device}")
    else:
        print("\nGPU nao disponivel - rodou na CPU.")

    print("\nModelo v2 pronto para treinar!")
