"""Minimal numpy GPT-2 (124M) forward pass that also returns the attention matrices.

This is the script that produced the REAL data embedded in the Part 1 slide deck.
It needs three files next to it (about 550 MB in total):

  gpt2-10.onnx   GPT-2 small weights, from the ONNX Model Zoo:
                 https://github.com/onnx/models/tree/main/validated/text/machine_comprehension/gpt-2
  encoder.json   the GPT-2 byte-pair vocabulary
  vocab.bpe      the GPT-2 merge rules
                 (both are the original OpenAI tokenizer files; any copy works, e.g.
                 https://huggingface.co/gpt2/tree/main)

    pip install numpy onnx regex
    python gpt2_attention_numpy.py "The cat chased the mouse because it was hungry" --layer 4 --head 3

If you have `transformers` installed, the same numbers come out of
GPT2LMHeadModel(..., attn_implementation="eager")(…, output_attentions=True).
"""
import json, os, sys, argparse, regex as re, numpy as np, onnx
from functools import lru_cache
from onnx import numpy_helper

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------- tokenizer (OpenAI's encoder.py, trimmed) ----------------
@lru_cache()
def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~")+1)) + list(range(ord("¡"), ord("¬")+1)) + list(range(ord("®"), ord("ÿ")+1))
    cs = bs[:]; n = 0
    for b in range(2**8):
        if b not in bs:
            bs.append(b); cs.append(2**8+n); n += 1
    return dict(zip(bs, [chr(c) for c in cs]))

def get_pairs(word):
    pairs = set(); prev = word[0]
    for ch in word[1:]:
        pairs.add((prev, ch)); prev = ch
    return pairs

class Encoder:
    def __init__(self):
        self.encoder = json.load(open(f"{HERE}/encoder.json"))
        self.decoder = {v: k for k, v in self.encoder.items()}
        self.byte_encoder = bytes_to_unicode()
        self.byte_decoder = {v: k for k, v in self.byte_encoder.items()}
        merges = open(f"{HERE}/vocab.bpe", encoding="utf-8").read().split("\n")[1:-1]
        self.bpe_ranks = dict(zip([tuple(m.split()) for m in merges], range(len(merges))))
        self.cache = {}
        self.pat = re.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+""")

    def bpe(self, token):
        if token in self.cache: return self.cache[token]
        word = tuple(token); pairs = get_pairs(word)
        if not pairs: return token
        while True:
            bigram = min(pairs, key=lambda p: self.bpe_ranks.get(p, float("inf")))
            if bigram not in self.bpe_ranks: break
            first, second = bigram; new_word = []; i = 0
            while i < len(word):
                try:
                    j = word.index(first, i); new_word.extend(word[i:j]); i = j
                except ValueError:
                    new_word.extend(word[i:]); break
                if word[i] == first and i < len(word)-1 and word[i+1] == second:
                    new_word.append(first+second); i += 2
                else:
                    new_word.append(word[i]); i += 1
            word = tuple(new_word)
            if len(word) == 1: break
            pairs = get_pairs(word)
        word = " ".join(word); self.cache[token] = word
        return word

    def encode(self, text):
        ids = []
        for tok in re.findall(self.pat, text):
            tok = "".join(self.byte_encoder[b] for b in tok.encode("utf-8"))
            ids.extend(self.encoder[t] for t in self.bpe(tok).split(" "))
        return ids

    def decode(self, ids):
        text = "".join(self.decoder[i] for i in ids)
        return bytearray([self.byte_decoder[c] for c in text]).decode("utf-8", errors="replace")

    def tokens(self, text):
        return [self.decode([i]) for i in self.encode(text)]

# ---------------- model ----------------
class GPT2:
    def __init__(self, path=f"{HERE}/gpt2-10.onnx"):
        m = onnx.load(path)
        self.w = {t.name: numpy_helper.to_array(t) for t in m.graph.initializer if not t.name.isdigit()}
        self.n_layer = 12; self.n_head = 12; self.d = 768

    @staticmethod
    def ln(x, g, b, eps=1e-5):
        mu = x.mean(-1, keepdims=True); var = x.var(-1, keepdims=True)
        return (x - mu) / np.sqrt(var + eps) * g + b

    @staticmethod
    def gelu(x):
        return 0.5 * x * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * x**3)))

    @staticmethod
    def softmax(x):
        x = x - x.max(-1, keepdims=True); e = np.exp(x)
        return e / e.sum(-1, keepdims=True)

    def attn(self, x, i):
        w = self.w; L = x.shape[0]; H = self.n_head; dk = self.d // H
        qkv = x @ w[f"h.{i}.attn.c_attn.weight"] + w[f"h.{i}.attn.c_attn.bias"]   # [L, 3d]
        q, k, v = np.split(qkv, 3, axis=-1)
        q = q.reshape(L, H, dk).transpose(1, 0, 2)     # [H, L, dk]
        k = k.reshape(L, H, dk).transpose(1, 0, 2)
        v = v.reshape(L, H, dk).transpose(1, 0, 2)
        scores = q @ k.transpose(0, 2, 1) / np.sqrt(dk)   # [H, L, L]
        mask = np.triu(np.ones((L, L)), 1) * -1e10
        A = self.softmax(scores + mask)                   # [H, L, L]
        out = (A @ v).transpose(1, 0, 2).reshape(L, self.d)   # concat heads
        out = out @ w[f"h.{i}.attn.c_proj.weight"] + w[f"h.{i}.attn.c_proj.bias"]
        return out, A

    def forward(self, ids):
        w = self.w
        x = w["wte.weight"][ids] + w["wpe.weight"][np.arange(len(ids))]
        attns = []
        for i in range(self.n_layer):
            a, A = self.attn(self.ln(x, w[f"h.{i}.ln_1.weight"], w[f"h.{i}.ln_1.bias"]), i)
            attns.append(A); x = x + a
            h = self.ln(x, w[f"h.{i}.ln_2.weight"], w[f"h.{i}.ln_2.bias"])
            h = self.gelu(h @ w[f"h.{i}.mlp.c_fc.weight"] + w[f"h.{i}.mlp.c_fc.bias"])
            x = x + h @ w[f"h.{i}.mlp.c_proj.weight"] + w[f"h.{i}.mlp.c_proj.bias"]
        x = self.ln(x, w["ln_f.weight"], w["ln_f.bias"])
        logits = x @ w["wte.weight"].T
        return logits, np.stack(attns)   # attns: [layer, head, L, L]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Print one head's attention matrix for a sentence.")
    ap.add_argument("text", nargs="?", default="The cat chased the mouse because it was hungry")
    ap.add_argument("--layer", type=int, default=4); ap.add_argument("--head", type=int, default=3)
    ap.add_argument("--json", help="write all layers/heads to this JSON file")
    a = ap.parse_args()
    enc, model = Encoder(), GPT2()
    ids = enc.encode(a.text); toks = enc.tokens(a.text)
    logits, A = model.forward(ids)
    np.set_printoptions(precision=2, suppress=True, linewidth=200)
    print("tokens:", toks)
    print(f"layer {a.layer}, head {a.head} (rows attend to columns):")
    print(A[a.layer, a.head])
    top = np.argsort(-logits[-1])[:5]
    print("next-token guesses:", [enc.decode([int(i)]) for i in top])
    if a.json:
        json.dump({"tokens": toks, "attention": np.round(A, 4).tolist()}, open(a.json, "w"))
        print("wrote", a.json)
