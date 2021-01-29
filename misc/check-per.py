#!/usr/bin/env pypy3

from collections import Counter, defaultdict
import itertools
import json

ALL_TEXTS = [
    "Sloane2320",
    "Sloane3566",
    "Trinity",
    "Boston",
    "Gonville",
    "Takamiya",
]

def main():
    with open("output/extract2.json") as f:
        data = json.load(f)

    texts = ALL_TEXTS[:-1]
    what = ["yes"]
    cases = defaultdict(list)
    print("texts = " + " ".join(texts))
    print("per = {}".format("/".join(what)))
    print()
    for chunk in data:
        textmap = { x: i for i,x in enumerate(chunk["texts"]) }
        clmap = { x: i for i,x in enumerate(chunk["classes"]) }
        for row,cl,words,short in chunk["rows"]:
            if cl[clmap["per"]] not in what:
                continue
            case = " ".join( ({0:"-", 1:"+"}[row[textmap[x]]] if x in textmap else "?") for x in texts )
            cases[case].append(words)
    total = 0
    for case in sorted(cases.keys(), key=lambda x: (-len(cases[x]), x)):
        n = len(cases[case])
        total += n
        examples = Counter()
        for ww in cases[case]:
            for w in ww:
                examples[w] += 1
        examples = sorted(examples.most_common(), key=lambda x: (-x[1], x[0]))
        limited = False
        exlimit = 5
        if len(examples) > exlimit:
            examples = examples[:exlimit]
            limited = True
        examples = ", ".join("{} x {}".format(x[1], x[0]) for x in examples)
        if limited:
            examples += " ..."
        print("{:3d} {}   {}".format(n, case, examples))
    print("{:3d} total".format(total))
    print()

main()
