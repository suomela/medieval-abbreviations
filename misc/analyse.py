#!/usr/bin/env python3

import collections
import itertools
import json
import math

FULL_ONLY = True

class Table:
    def __init__(self, count):
        self.count = count
        self.mutinfo = 0
        for x in [0,1]:
            for y in [0,1]:
                c__ = sum(count[(a,b)] for a in [0,1] for b in [0,1])
                cx_ = sum(count[(x,b)] for b in [0,1])
                c_y = sum(count[(a,y)] for a in [0,1])
                cxy = count[(x,y)]
                px = cx_ / c__
                py = c_y / c__
                pxy = cxy / c__
                self.mutinfo += pxy * math.log2(pxy / px / py)


def get_comp(comps, e):
    for i,c in enumerate(comps):
        if e in c:
            return i,c
    assert False


class Stat:
    def __init__(self, dump):
        self.texts = dump["texts"]
        self.abbr_raw = dump["abbr"]
        self.n = len(self.texts)
        self.abbr = {}
        self.cases = sorted([x for x in itertools.product([0,1], repeat=self.n) if sum(x)])
        for v in self.cases:
            vs = ''.join([str(x) for x in v])
            self.abbr[v] = self.abbr_raw.get(vs, 0)

    def process(self):
        self.count_pairs()
        edges = [(self.pair[(i,j)].mutinfo, i, j) for i,j in self.pair.keys()]
        edges.sort(reverse=True)
        comps = [set([i]) for i in range(self.n)]
        tree = []
        for v,i,j in edges:
            ii, ci = get_comp(comps, i)
            ij, cj = get_comp(comps, j)
            if ii != ij:
                tree.append(tuple(sorted([i,j])))
                comps = [ck for ik, ck in enumerate(comps) if ik not in [ii, ij]]
                comps += [ci | cj]
        assert len(comps) == 1
        assert len(tree) == self.n - 1
        for i,j in tree:
            li = self.texts[i]
            lj = self.texts[j]
            p = self.pair[(i,j)]
            counts = [p.count[x] for x in [(0,0), (1,0), (0,1), (1,1)]]
            print('{:11s} {:11s} {:.3f}   {:3d} {:3d} {:3d} {:3d}'.format(li, lj, p.mutinfo, *counts))

    def count_pairs(self):
        n = self.n
        self.pair = {}
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                count = collections.Counter()
                if FULL_ONLY:
                    for v,c in self.abbr.items():
                        count[(v[i],v[j])] += c
                else:
                    for v,c in self.abbr_raw.items():
                        if v[i] in '01' and v[j] in '01' and '1' in v:
                            count[(int(v[i]),int(v[j]))] += c
                self.pair[(i,j)] = Table(count)


def main():
    with open('output/summary.json') as f:
        stat = Stat(json.load(f))
    stat.process()

main()
