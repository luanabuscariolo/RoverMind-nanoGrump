"""
=============================================================
 TOKENIZER DE CARACTERES  -  Cerebro do Robo
=============================================================

 O que este arquivo faz:

   1. Le o dataset (as frases do robo).
   2. Descobre o "alfabeto" (todos os caracteres unicos).
   3. Cria dois dicionarios:
        - stoi : caractere  -> numero  (string to int)
        - itos : numero      -> caractere (int to string)
   4. Oferece duas funcoes:
        - encode(texto)  : texto  -> lista de numeros
        - decode(numeros): numeros -> texto
   5. Salva o vocabulario em um arquivo, para as proximas
      etapas usarem exatamente o mesmo mapeamento.

 Por que caracteres (e nao palavras)?
   Porque o vocabulario fica minusculo (~40 simbolos) e
   voce entende cada linha. Perfeito para aprender e para
   caber num modelo pequeno.

=============================================================
"""

import json
from pathlib import Path


# ------------------------------------------------------------
# 1. LER O DATASET
# ------------------------------------------------------------
# Path(__file__).parent = a pasta onde este script esta.
# Assim o caminho funciona nao importa de onde voce rode.

# [ALTERADO] robot_voice.txt -> robot_voice_final.txt (dataset expandido v2)
CAMINHO_DATASET = Path(__file__).parent / "data" / "robot_voice_final.txt"

texto = CAMINHO_DATASET.read_text(encoding="utf-8")

print("=" * 55)
print("TOKENIZER DE CARACTERES")
print("=" * 55)
print(f"Total de caracteres no dataset: {len(texto)}")

# [ADICIONADO] resumo de frases e marcadores para diagnostico rapido
linhas = [l for l in texto.splitlines() if l.strip()]
marcadores_conhecidos = [
    "<start>", "<explore>", "<obstacle>", "<turn_left>",
    "<turn_right>", "<backup>", "<stuck>", "<clear>",
]
print(f"Total de frases          : {len(linhas)}")
for m in marcadores_conhecidos:
    n = sum(1 for l in linhas if l.startswith(m))
    print(f"  {m:15s} {n:4d} frases")


# ------------------------------------------------------------
# 2. DESCOBRIR O ALFABETO (VOCABULARIO)
# ------------------------------------------------------------
# set(texto) pega cada caractere unico (sem repetir).
# sorted(...) coloca em ordem, para o resultado ser sempre
# o mesmo toda vez que rodarmos (importante!).

caracteres = sorted(set(texto))
tamanho_vocab = len(caracteres)

print(f"Tamanho do vocabulario: {tamanho_vocab} caracteres unicos")
print("Vocabulario (entre aspas para ver espacos):")
print("  " + "  ".join(repr(c) for c in caracteres))

# [ADICIONADO] validacao: garante que nenhum caractere do dataset
# ficou de fora do vocabulario. Com dataset gerado por script isso
# nao deve ocorrer, mas e um seguro barato para quando o dataset
# crescer manualmente no futuro.
chars_no_dataset = set(texto)
chars_fora_do_vocab = chars_no_dataset - set(caracteres)
if chars_fora_do_vocab:
    raise ValueError(
        f"ERRO: {len(chars_fora_do_vocab)} caracteres no dataset "
        f"nao estao no vocabulario: {sorted(chars_fora_do_vocab)}"
    )
print("Validacao: todos os caracteres do dataset estao no vocabulario. OK.")


# ------------------------------------------------------------
# 3. CRIAR OS DOIS DICIONARIOS
# ------------------------------------------------------------
# stoi: de cada caractere para um numero.
#   enumerate da o indice (0, 1, 2, ...) e o caractere.
# itos: o caminho inverso (numero -> caractere).

stoi = {c: i for i, c in enumerate(caracteres)}
itos = {i: c for i, c in enumerate(caracteres)}


# ------------------------------------------------------------
# 4. FUNCOES DE ENCODE E DECODE
# ------------------------------------------------------------

def encode(s: str) -> list[int]:
    """Recebe um texto e devolve a lista de numeros."""
    return [stoi[c] for c in s]


def decode(numeros: list[int]) -> str:
    """Recebe uma lista de numeros e devolve o texto."""
    return "".join(itos[n] for n in numeros)


# ------------------------------------------------------------
# 5. TESTE DE IDA E VOLTA (round-trip)
# ------------------------------------------------------------
# Se encode e decode estao certos, decode(encode(x)) == x.
# Esse e o teste que prova que o tokenizer funciona.

frase_teste = "<obstacle> Oh look, a wall."

numeros = encode(frase_teste)
de_volta = decode(numeros)

print()
print("-" * 55)
print("TESTE DE IDA E VOLTA")
print("-" * 55)
print(f"Frase original : {frase_teste}")
print(f"Virou numeros  : {numeros}")
print(f"Voltou a texto : {de_volta}")
print(f"Bateu igual?   : {frase_teste == de_volta}")


# ------------------------------------------------------------
# 6. SALVAR O VOCABULARIO
# ------------------------------------------------------------
# Guardamos o alfabeto em um arquivo. As proximas etapas
# (modelo, treino, exportacao) precisam usar EXATAMENTE
# este mesmo mapeamento, senao os numeros nao batem.

CAMINHO_VOCAB = Path(__file__).parent / "vocab.json"

# [ALTERADO] formato do vocab.json: era lista simples [...],
# agora e dict com metadados {"version", "type", "vocab_size", "vocab"}.
# Motivo: o model.py vai ler vocab_size daqui (nao mais fixo em 59),
# e os metadados ajudam na exportacao para o ESP32-S3 depois.
#
# COMPATIBILIDADE: o model.py, train.py e generate.py precisam ser
# atualizados para ler vocab["vocab"] em vez de acessar a lista direto.
# Isso sera feito na Fase 3 (atualizacao do model.py).
payload = {
    "version"   : 2,
    "type"      : "character",
    "vocab_size" : tamanho_vocab,
    "vocab"     : caracteres,
}

with open(CAMINHO_VOCAB, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print()
print(f"Vocabulario salvo em: {CAMINHO_VOCAB.name}")
print(f"  vocab_size : {tamanho_vocab}")
print(f"  version    : {payload['version']}")
print(f"  type       : {payload['type']}")
print("Tokenizer pronto!")
