import argparse, json, sys


def load_jsonl(p):
    items=[]
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: 
                continue
            try:
                items.append(json.loads(line))
            except Exception as e:
                print(f"[WARN] {e}", file=sys.stderr)
    return items


def iter_examples(rec):
    word = rec.get("word") or rec.get("title")
    pos = rec.get("pos")
    senses = rec.get("senses") or []
    for i, s in enumerate(senses):
        gloss = ""
        g = s.get("glosses")
        if isinstance(g, list) and g:
            gloss = g[0]
        elif isinstance(g, str):
            gloss = g
        for ex in (s.get("examples") or []):
            txt = ex.get("text") or ex.get("example") or ""
            yield word, pos, i, gloss, txt


def pick(items, needle):
    out=[]
    for r in items:
        for w,p,i,g,t in iter_examples(r):
            if needle in t:
                out.append({"word":w,"pos":p,"sense_index":i,"gloss":g})
    return out


def trunc(s, n=90):
    s = s or ""
    return s if len(s)<=n else s[:n]+"…"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--contains", required=True)
    args=ap.parse_args()
    A=load_jsonl(args.a); B=load_jsonl(args.b)
    ah=pick(A, args.contains); bh=pick(B, args.contains)
    print("=== A ===")
    for h in ah:
        print(f'[A] word={h["word"]} pos={h["pos"]} sense={h["sense_index"]} gloss="{trunc(h["gloss"])}"')
    print("=== B ===")
    for h in bh:
        print(f'[B] word={h["word"]} pos={h["pos"]} sense={h["sense_index"]} gloss="{trunc(h["gloss"])}"')


if __name__=="__main__":
    main()
