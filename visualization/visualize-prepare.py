#!/usr/bin/env pypy3

from collections import Counter, defaultdict
import itertools
import json
import random
import statistics

ALL_TEXTS = [
    "Sloane2320",
    "Sloane3566",
    "Trinity",
    "Boston",
    "Gonville",
    # "Takamiya",
]

THRESHOLD = 10

def normalize(x):
    return x.lower().rstrip("?").replace("+t", "þ")

def calc_length(x):
    return len(normalize(x))

infty = float("inf")


class Data:
    def __init__(self, restrict):
        self.texts = ALL_TEXTS
        self.restrict = restrict
        self.filename = "" if restrict is None else "-" + restrict

    def load(self):
        with open("output/extract2.json".format(self.filename)) as f:
            self.data = json.load(f)
        counter = Counter()
        self.examples = defaultdict(lambda: defaultdict(list))
        for chunk in self.data:
            textmap = { x: i for i,x in enumerate(chunk["texts"]) }
            clmap = { x: i for i,x in enumerate(chunk["classes"]) }
            recipe = "recipe" if chunk["kind"] == "recipe" else "other"
            if self.restrict is not None and chunk["kind"] != self.restrict:
                continue
            for row,cl,words,short in chunk["rows"]:
                vv = tuple([ row[textmap[x]] if x in textmap else 0.5 for x in self.texts ])
                if max(vv) < 1:
                    continue
                examples = tuple([ words[textmap[x]] for x in self.texts ])
                examples_short = tuple([ short[textmap[x]] for x in self.texts ])
                counter[vv] += 1
                chars = round(statistics.mean(calc_length(w) for w in examples))
                if chars <= 4:
                    char_label = "-4"
                elif 5 <= chars <= 6:
                    char_label = "5-6"
                elif 7 <= chars <= 8:
                    char_label = "7-8"
                elif 9 <= chars <= 10:
                    char_label = "9-10"
                elif 11 <= chars:
                    char_label = "11-"
                else:
                    assert False, chars
                LMAP = { "yes": "long", "": "short", "no": "short" }
                PERMAP = { "yes": "per", "": "other", "other": "other", "no": "other" }
                cases = [
                    "language " + chunk["language"],
                    "lex " + cl[clmap["lex-funct"]],
                    "length " + LMAP[cl[clmap["three syllables"]]],
                    "per " + PERMAP[cl[clmap["per"]]],
                    "recipe " + recipe,
                    "characters " + char_label,
                ]
                for case in cases:
                    self.examples[vv][case].append([examples, examples_short])
        self.rows = sorted(counter.items(), key=lambda x: (sum(x[0]), x[0]))
        self.rows = [ (vv,c) for vv,c in self.rows if c >= THRESHOLD ]

    def eval_col_perm(self, perm):
        tt = 0
        for vv, c in self.rows:
            t = 0
            p = 0
            for i in perm:
                x = vv[i]
                t += abs(p - x)
                p = x
            t += abs(p)
            tt += c * t
        return tt

    def eval_row_perm(self, perm):
        p = None
        m = len(self.texts)
        tt = [ 0 for i in range(m) ]
        for j in perm:
            vv, c = self.rows[j]
            if p is not None:
                for i in range(m):
                    tt[i] += abs(p[i] - vv[i])
            p = vv
        return sum(x ** 2 for x in tt)

    def opt_col_perm(self):
        perm = None
        value = None
        for p in itertools.permutations(range(len(self.texts))):
            v = self.eval_col_perm(p)
            if value is None or v < value:
                perm, value = p, v
        self.colp = perm
        for x in self.colp:
            print(self.texts[x])

    def improve_row_perm(self, perm, pairs):
        random.shuffle(pairs)
        value = self.eval_row_perm(perm)
        for a,b in pairs:
            p = perm[:a] + perm[a:b][::-1] + perm[b:]
            v = self.eval_row_perm(p)
            if v < value:
                return p, v
        return None, None

    def find_good_row_perm(self):
        n = len(self.rows)

        pairs = []
        for a in range(n):
            for b in range(a+2,n+1):
                pairs.append((a,b))

        perm = list(range(n))
        # random.shuffle(perm)

        value = self.eval_row_perm(perm)
        while True:
            p, v = self.improve_row_perm(perm, pairs)
            if p is None:
                return perm, value
            perm, value = p, v

    def opt_row_perm(self):
        perm, value = self.find_good_row_perm()
        for i in range(500):
            p, v = self.find_good_row_perm()
            if v < value:
                perm, value = p, v
            print(value, v)
        self.rowp = perm

    def write(self):
        texts = [ self.texts[i] for i in self.colp ]
        rows = []
        for j in self.rowp:
            vv, c = self.rows[j]
            ss = ""
            r = [ vv[i] for i in self.colp ]
            examples = self.examples[vv]
            rows.append((r, c, examples))

        result = {
            "texts": texts,
            "rows": rows,
        }

        with open("output/optimized{}.json".format(self.filename), "w") as f:
            json.dump(result, f, sort_keys=True)


def main():
    random.seed(0)
    for restrict in [ None, "text" ]:
        data = Data(restrict)
        data.load()
        data.opt_col_perm()
        data.opt_row_perm()
        data.write()

main()
