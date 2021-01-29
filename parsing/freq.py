#!/usr/bin/env python3

from collections import defaultdict, Counter, OrderedDict
import json

ALL_TEXTS = [
    "Sloane2320",
    "Sloane3566", "Trinity", "Boston",
    "Gonville", "Takamiya",
]

def normalise(x):
    return x.lower()

class Similarity:
    def __init__(self):
        self.p = {}
        self.raw = []

    def feed_many(self, row, l):
        l = [normalise(a) for a in l]
        self.raw.append((row, l))
        for a in range(len(l)):
            for b in range(a, len(l)):
                self.merge(l[a], l[b])

    def merge(self, a, b):
        self.add(a)
        self.add(b)
        ra = self.get(a)
        rb = self.get(b)
        k = [ra, rb]
        k.sort()
        self.p[k[1]] = k[0]

    def add(self, a):
        if a not in self.p:
            self.p[a] = a

    def get(self, a):
        if self.p[a] == a:
            return a
        else:
            x = self.get(self.p[a])
            self.p[a] = x
            return x

    def cluster(self):
        self.comp = defaultdict(list)
        aa = sorted(self.p.keys())
        for a in aa:
            x = self.get(a)
            self.comp[x].append(a)
        self.count = Counter()
        self.count01 = [Counter(), Counter()]
        for row,l in self.raw:
            x = self.get(l[0])
            self.count[x] += 1
            for v in row:
                self.count01[v][x] += 1

    def dump(self):
        xx = sorted(self.count.most_common(), key=lambda p: (-p[1], p[0]))
        for x,c in xx:
            f0, f1 = [ self.count01[i][x] for i in range(2) ]
            if f1 == 0:
                mark = '-'
            elif f1 >= f0:
                mark = '#'
            else:
                mark = '+'
            print(mark, c, ' '.join(self.comp[x]))

    def get_count(self, l):
        norm = [self.get(normalise(a)) for a in l]
        assert len(set(norm)) == 1
        norm = norm[0]
        return self.count[norm], self.count01[0][norm], self.count01[1][norm]


def main():
    with open('output/extract.json') as f:
        data = json.load(f)

    sim = defaultdict(Similarity)

    for chunk in data:
        language = chunk['language']
        textmap = { x: i for i,x in enumerate(chunk['texts']) }
        clmap = { x: i for i,x in enumerate(chunk['classes']) }
        for row,cl,words,short in chunk['rows']:
            funclex = cl[clmap['lex-funct']]
            sim[(language,funclex)].feed_many(row,words)

    for k in sorted(sim.keys()):
        sim[k].cluster()
        print(' '.join(k))
        print()
        sim[k].dump()
        print()


    for chunk in data:
        language = chunk['language']
        textmap = { x: i for i,x in enumerate(chunk['texts']) }
        clmap = { x: i for i,x in enumerate(chunk['classes']) }
        chunk['classes'].append('freq')
        chunk['classes'].append('sometimes')
        for row,cl,words,short in chunk['rows']:
            funclex = cl[clmap['lex-funct']]
            f, f0, f1 = sim[(language,funclex)].get_count(words)
            cl.append(f)
            cl.append('yes' if f1 > 0 else 'no')

    with open('output/extract2.json', 'w') as f:
        json.dump(data, f, sort_keys=True, indent=1)

main()
