#!/usr/bin/env pypy3

from collections import defaultdict, Counter, OrderedDict
import json
import random
import lxml
from lxml.builder import E

ALL_TEXTS = [
    "Sloane2320",
    "Sloane3566", "Trinity", "Boston",
    "Gonville", "Takamiya",
]

ABBR = {
    'incipit-explicit': 'inc/expl',
    'measurement': 'measur.',
    'three syllables': '3-syll.',
    'not three syllables': 'short',
}

WHAT = [
    ( ('Latin',), () ),
    ( ('Latin', 'func',), ('func',) ),
    ( ('Latin', 'lex',), ('lex',) ),
    ( ('English',), () ),
    ( ('English', 'func',), ('func',) ),
    ( ('English', 'lex',), ('lex',) ),
    ( ('Latin', 'recipe',), ('Latin',) ),
    ( ('Latin', 'func',), ('Latin',) ),
    ( ('Latin', 'lex',), ('Latin',) ),
    ( ('English', 'func',), ('English',) ),
    ( ('English', 'lex',), ('English',) ),
    ( ('Latin', 'recipe', 'func',), ('Latin','func',) ),
    ( ('Latin', 'recipe', 'func',), ('Latin','recipe',) ),
    ( ('Latin', 'recipe', 'lex',), ('Latin','lex',) ),
    ( ('Latin', 'recipe', 'lex',), ('Latin','recipe',) ),
]

N = 10000


CSS = """
BODY {
    color: #000;
    background-color: #fff;
    font-family: 'Open Sans', sans-serif;
    font-size: 15px;
    padding: 0px;
    margin: 10px;
}

#wrap {}

table {
    border-collapse: collapse;
    padding: 0px;
    margin: 0px;
    margin-left: auto;
    margin-right: auto;
}

td {
    padding: 0px 8px;
    text-align: left;
    vertical-align: top;
    white-space: nowrap;
}

td.pad {
    width: 12px;
    min-width: 12px;
    padding: 0px;
}

tr.pad {
    height: 15px;
}

tr.header td {
    padding: 1px;
    text-align: center;
}

tr.lineunder td {
    border-bottom: 1px solid #000;
}

td.t1, td.t2, td.count {
    padding: 0px 5px;
    text-align: center;
}

td.h5 { background-color: #2166ac; color: #fff; }
td.h4 { background-color: #4393c3; color: #fff; }
td.h3 { background-color: #92c5de; color: #000; }
td.h2 { background-color: #d1e5f0; color: #000; }
td.h1 { background-color: #ffffff; color: #000; }
td.nn { background-color: #ffffff; color: #ddd; }
td.l1 { background-color: #ffffff; color: #000; }
td.l2 { background-color: #fddbc7; color: #000; }
td.l3 { background-color: #f4a582; color: #000; }
td.l4 { background-color: #d6604d; color: #fff; }
td.l5 { background-color: #b2182b; color: #fff; }

.other { font-size: 10px; }

.bar {
    display: block;
    min-height: 5px;
    width: 0px;
    background-color: #ccc;
    margin-top: 2px;
}
"""

def od(**x):
    return OrderedDict([(("class" if a == "klass" else a), str(b)) for a,b in sorted(x.items())])

def write_html(filename, body):
    doc = E.html({"lang": "en"},
        E.head(
            E.title("John of Burgundy"),
            E.link(od(rel="stylesheet", href="https://fonts.googleapis.com/css?family=Open+Sans")),
            E.meta(od(charset="UTF-8")),
            E.meta(od(name="viewport", content="width=device-width, initial-scale=1")),
            E.style(CSS),
        ),
        E.body(
            E.div(od(id="wrap"),
                body,
            )
        ),
    )
    with open(filename, 'w') as f:
        f.write('<!DOCTYPE html>\n')
        f.write(lxml.etree.tostring(doc, method='html', encoding=str))
        f.write('\n')


def get_level(v, l, low):
    if v <= l[0]:
        i = 0
        while i + 1 < len(l) and v <= l[i+1]:
            i += 1
        return '{}{}'.format("l" if low else "h", i+1)
    else:
        return 'nn'

class Table0:
    def __init__(self):
        self.n0 = 0
        self.n = 0

    def add(self, hit):
        self.n0 += 1
        if hit:
            self.n += 1

    def html(self):
        kl = "count"
        return [
            E.td(od(colspan="2", klass=kl), str(self.n))
        ]

class Table1:
    def __init__(self):
        self.c0 = [0,0]
        self.n0 = 0
        self.c = [0,0]
        self.n = 0

    def add(self, hit, v1):
        self.c0[v1] += 1
        self.n0 += 1
        if hit:
            self.c[v1] += 1
            self.n += 1

    def html(self):
        c = self.c[1]
        n = self.n
        title = '{}/{}'.format(c, n)
        kl = "t1"
        if n == 0:
            return [
                E.td(od(colspan="2", klass=kl, title=title), '')
            ]
        f = c / n
        return [
            E.td(od(colspan="2", klass=kl, title=title),
                '{:.1f}%'.format(100.0 * f),
                E.span(od(klass="bar", style="min-width: {:.0f}px".format(50*f)))
            )
        ]


def calc(c):
    c00 = c[0][0]
    c01 = c[0][1]
    c10 = c[1][0]
    c11 = c[1][1]
    c0_ = c00 + c01
    c1_ = c10 + c11
    c_0 = c00 + c10
    c_1 = c01 + c11
    c__ = c0_ + c1_
    if c0_ == 0 or c1_ == 0 or c_0 == 0 or c_1 == 0:
        return 1
    if c01 > c10:
        return 1 - (c__ * c10) / (c1_ * c_0)
    else:
        return 1 - (c__ * c01) / (c0_ * c_1)


def calc_sign(a, c):
    k = 0
    pop = []
    for x,y in [ (0,0), (0,1), (1,0), (1,1) ]:
        pop += [ (x,y) ] * a[x][y]
        k += c[x][y]

    f0 = calc(a)
    f1 = calc(c)
    n0 = 0
    n1 = 0
    for i in range(N):
        d = [[0,0],[0,0]]
        for x,y in random.sample(pop, k):
            d[x][y] += 1
        f = calc(d)
        if f <= f1:
            n0 += 1
        if f >= f1:
            n1 += 1

    p = (1 + min(n0, n1)) / N
    return (f0, f1, p, n0 < n1)


class Table2:
    def __init__(self):
        self.c0 = [[0,0],[0,0]]
        self.c = [[0,0],[0,0]]

    def add(self, hit, v1, v2):
        self.c0[v1][v2] += 1
        if hit:
            self.c[v1][v2] += 1

    def html(self):
        f0, f, p, low = calc_sign(self.c0, self.c)
        level = get_level(p, [0.1, 0.05, 0.01, 0.005, 0.001], low)
        return [
            E.td(od(klass="t2 " + level), '{:.0f}'.format(100 * f)),
            E.td(od(klass="t2 other " + level), '{:.0f}'.format(100 * f0)),
        ]

def add_header(tablerows):
    for i in range(2):
        if i == 0:
            row = [E.td('Text 1'), E.td('Text 2')]
        else:
            row = [E.td(), E.td()]
        for ww in WHAT:
            what = ww[i]
            if len(what) == 0:
                label = ['all']
            else:
                label = []
                for w in what:
                    if len(label) > 0:
                        label.append(E.br())
                    label.append(ABBR.get(w, w))
            row.append(E.td(od(klass='pad')))
            row.append(E.td(od(colspan="2"), *label))
        tablerows.append(E.tr(od(klass="header"), *row))
        klass = ["pad", "pad lineunder"][i]
        tablerows.append(E.tr(od(klass=klass), E.td(od(colspan=str(2 + 3*len(WHAT))))))


def process(texts, data, limiter, tablerows):
    print(' '.join(texts))

    ll = len(texts)
    counters = defaultdict([Table0, Table1, Table2][ll])

    for chunk in data:

        textmap = { x: i for i,x in enumerate(chunk['texts']) }
        clmap = { x: i for i,x in enumerate(chunk['classes']) }

        assert textmap.keys() <= set(ALL_TEXTS)
        if not (set(texts) <= textmap.keys()):
            continue

        for row,cl,words in chunk['rows']:
            vv = [ row[textmap[x]] for x in texts ]

            if not limiter(cl[clmap['freq']], cl[clmap['sometimes']] == 'yes'):
                continue

            classes = set()
            y = cl[clmap['lex-funct']]
            assert y in ['func', 'lex']
            classes.add(y)

            for x in ['numeral', 'measurement', 'three syllables']:
                y = cl[clmap[x]]
                assert y in ['yes', 'no', '']
                if y == 'yes':
                    classes.add(x)
                elif y == 'no':
                    classes.add('not ' + x)

            y = chunk['kind']
            if y in ['incipit', 'explicit']:
                y = 'incipit-explicit'
            classes.add(y)

            classes.add(chunk['language'])

            for w1, w2 in WHAT:
                if set(w2) <= classes:
                    counters[(w1,w2)].add(set(w1) <= classes, *vv)


    row = [E.td(x) for x in texts]
    if ll == 0:
        row.append(E.td(od(colspan="2"), 'words'))

    if ll == 1:
        row.append(E.td())

    for w1, w2 in WHAT:
        row.append(E.td(od(klass='pad')))
        row.extend(counters[(w1,w2)].html())

    tablerows.append(E.tr(*row))


def limit(data, filekey, limiter):
    n = len(ALL_TEXTS)
    tablerows = []
    add_header(tablerows)
    tablerows.append(E.tr(od(klass="pad")))
    process([], data, limiter, tablerows)
    for i in range(n):
        tablerows.append(E.tr(od(klass="pad")))
        process([ALL_TEXTS[i]], data, limiter, tablerows)
        tablerows.append(E.tr(od(klass="pad")))
        for j in range(n):
            if j != i:
                process([ALL_TEXTS[i], ALL_TEXTS[j]], data, limiter, tablerows)
    write_html('output/comparison{}.html'.format(filekey), E.table(*tablerows))


def main():
    random.seed(0)
    with open('output/extract2.json') as f:
        data = json.load(f)
    limit(data, '', lambda f,s: True)
    limit(data, '-abbr', lambda f,s: s)

main()
