import argparse, json


def load_jsonl(p):
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line:
                try:
                    yield json.loads(line)
                except:
                    pass


def trunc(s, n=80):
    s = s or ""
    return s if len(s)<=n else s[:n]+"…"


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--word", required=True)
    ap.add_argument("--examples", type=int, default=3)
    a=ap.parse_args()
    found=False
    for rec in load_jsonl(a.jsonl):
        if (rec.get("word") or rec.get("title")) != a.word:
            continue
        found=True
        print(f'Word: {a.word}\n  POS: {rec.get("pos")}')
        for i, s in enumerate(rec.get("senses") or []):
            g = s.get("glosses")
            gloss = g[0] if isinstance(g,list) and g else (g if isinstance(g,str) else "")
            print(f'    - Sense[{i}] gloss="{trunc(gloss)}"')
            for j, ex in enumerate((s.get("examples") or [])[:a.examples]):
                txt = ex.get("text") or ex.get("example") or ""
                print(f'        EX[{j}]: "{trunc(txt, 100)}"')
    if not found:
        print("(no record)")


if __name__=="__main__":
    main()
