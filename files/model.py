"""
=============================================================
 MINI-GPT  -  o modelo completo do nano-grump
=============================================================

 Junta todas as pecas que construimos nos demos:
   - emb_token   : demo 1 (embedding de caractere)
   - emb_posicao : demo 2 (embedding de posicao)
   - Atencao     : demo 3 (self-attention com mascara causal)
   - FFN         : demo 4 (feed-forward)
   - Bloco       : atencao + FFN, com LayerNorm e residual
   - MiniGPT     : embeddings -> blocos -> saida

=============================================================
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# ------------------------------------------------------------
# HIPERPARAMETROS (as "medidas" do modelo)
# ------------------------------------------------------------

vocab_size = 59     # tamanho do alfabeto (do tokenizer)
n_embd     = 32     # tamanho do vetor de cada token
block_size = 32     # janela de contexto (quantos chars por vez)
n_layer    = 3      # numero de blocos empilhados


# ============================================================
# ATENCAO  (o demo 3 virou uma classe)
# ============================================================

class Atencao(nn.Module):
    def __init__(self):
        super().__init__()
        # As tres "vistas" do token: query, key, value.
        # Cada uma e uma camada linear (tabela de pesos).
        self.query = nn.Linear(n_embd, n_embd, bias=False)
        self.chave = nn.Linear(n_embd, n_embd, bias=False)
        self.value = nn.Linear(n_embd, n_embd, bias=False)
        # Projecao de saida (mistura o resultado antes de devolver).
        self.proj  = nn.Linear(n_embd, n_embd)
        # Mascara causal triangular. register_buffer = guarda junto
        # com o modelo, mas NAO e um peso treinavel.
        self.register_buffer(
            "mascara",
            torch.tril(torch.ones(block_size, block_size))
        )

    def forward(self, x):
        B, T, C = x.shape          # (lote, tokens, tamanho do vetor)

        q = self.query(x)          # (B, T, C)
        k = self.chave(x)          # (B, T, C)
        v = self.value(x)          # (B, T, C)

        # 1. produto escalar + escala  -> notas (B, T, T)
        notas = q @ k.transpose(-2, -1) / (C ** 0.5)

        # 2. mascara causal: futuro vira -inf
        notas = notas.masked_fill(
            self.mascara[:T, :T] == 0,
            float("-inf")
        )

        # 3. softmax -> pesos que somam 1
        pesos = F.softmax(notas, dim=-1)

        # 4. soma ponderada dos values
        saida = pesos @ v          # (B, T, C)

        return self.proj(saida)


# ============================================================
# FFN  (o demo 4 virou uma classe)
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
# BLOCO  (atencao + FFN, com LayerNorm e residual)
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
# MINI-GPT  (o modelo completo)
# ============================================================

class MiniGPT(nn.Module):
    def __init__(self):
        super().__init__()
        # Os dois embeddings.
        self.emb_token   = nn.Embedding(vocab_size, n_embd)
        self.emb_posicao = nn.Embedding(block_size, n_embd)

        # Os 3 blocos empilhados (mesma peca repetida).
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
    print("MINI-GPT montado!")
    print("=" * 55)
    print(f"vocab_size : {vocab_size}")
    print(f"n_embd     : {n_embd}")
    print(f"block_size : {block_size}")
    print(f"n_layer    : {n_layer}")
    print(f"\nParametros treinaveis: {n_params:,}")

    # Passa um lote falso pelo modelo para ver o formato da saida.
    # lote de 2 sequencias, cada uma com 8 tokens.
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

    print("\nModelo pronto para treinar!")
