#!/usr/bin/env pypy3

from collections import defaultdict, Counter, OrderedDict
import json
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

WHAT = [tuple(x) for x in [
    [],
    ['Latin'], ['English'],
    ['recipe'], ['text'], ['incipit-explicit'],
    ['func'], ['lex'],
    ['Latin', 'func'], ['Latin', 'lex'],
    ['English', 'func'], ['English', 'lex'],
    ['recipe', 'func'], ['recipe', 'lex'],
    ['numeral'], ['measurement'],
    ['three syllables'], ['recipe', 'three syllables'], ['English', 'three syllables'], ['Latin', 'three syllables'],
    ['not three syllables'], ['recipe', 'not three syllables'], ['English', 'not three syllables'], ['Latin', 'not three syllables'],
]]

THRESHOLD1 = 20
THRESHOLD2 = 20
THRESHOLDF = 1.02

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

td.h5 { background-color: #053061; color: #fff; }
td.h4 { background-color: #2166ac; color: #fff; }
td.h3 { background-color: #4393c3; color: #fff; }
td.h2 { background-color: #92c5de; color: #000; }
td.h1 { background-color: #d1e5f0; color: #000; }
td.nn { background-color: #ffffff; color: #000; }
td.l1 { background-color: #fddbc7; color: #000; }
td.l2 { background-color: #f4a582; color: #000; }
td.l3 { background-color: #d6604d; color: #fff; }
td.l4 { background-color: #b2182b; color: #fff; }
td.l5 { background-color: #67001f; color: #fff; }

td.small { background-color: #fff; color: #ddd; }
td.verysmall { background-color: #fff; color: #fff; }

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


def get_level(v, l1, l2):
    if v <= l1[0]:
        i = 0
        while i + 1 < len(l1) and v <= l1[i+1]:
            i += 1
        return 'l{}'.format(i+1)
    elif v >= l2[0]:
        i = 0
        while i + 1 < len(l2) and v >= l2[i+1]:
            i += 1
        return 'h{}'.format(i+1)
    else:
        return 'nn'

class Table0:
    def __init__(self):
        self.n = 0

    def add(self):
        self.n += 1

    def html(self):
        kl = "count"
        return [
            E.td(od(colspan="2", klass=kl), str(self.n))
        ]

class Table1:
    def __init__(self):
        self.c = [0,0]
        self.n = 0

    def add(self, v1):
        self.c[v1] += 1
        self.n += 1

    def html(self):
        c = self.c[1]
        n = self.n
        title = '{}/{}'.format(c, n)
        kl = "t1"
        if n < THRESHOLD1:
            kl += " small"
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

class Table2:
    def __init__(self):
        self.c = [[0,0],[0,0]]
        self.c1 = [0,0]
        self.c2 = [0,0]
        self.n = 0

    def add(self, v1, v2):
        self.c[v1][v2] += 1
        self.c1[v1] += 1
        self.c2[v2] += 1
        self.n += 1

    def html(self):
        if self.n == 0:
            return [
                E.td(od(klass='t2'), ''),
                E.td(od(klass='t2 dir'), ''),
            ]
        fv1 = self.c1[0] / self.n
        fv2 = self.c2[1] / self.n
        expected_random = fv1 * fv2 * self.n
        if self.c2[1] > self.c1[1]:
            expected_system = self.c2[1] - self.c1[1]
        else:
            expected_system = 0
        if self.c2[1] >= THRESHOLDF * self.c1[1]:
            dd = "+"
        elif self.c1[1] >= THRESHOLDF * self.c2[1]:
            dd = "−"
        else:
            dd = "±"
        got = self.c[0][1]
        if got == expected_random == expected_system:
            f = 1
        else:
            f = 1 - (got - expected_system) / (expected_random - expected_system)
        level = get_level(100*f, [25,20,15,10,5], [75,80,85,90,95])
        kl = "t2 " + level
        if abs(expected_random - expected_system) < THRESHOLD2:
            kl += " small"
        if abs(expected_random - expected_system) == 0:
            kl += " verysmall"
        title = "{} vs. {}, common {}, expected {:.0f}".format(self.c1[1], self.c2[1], self.c[1][1], self.c1[1] * self.c2[1] / self.n)
        return [
            E.td(od(klass=kl, title=title), '{:.0f}'.format(100 * f)),
            E.td(od(klass=kl + " dir", title=title), dd),
        ]

def add_header(tablerows):
    row = [E.td('Text 1'), E.td('Text 2')]
    for what in WHAT:
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

            for what in WHAT:
                if set(what) <= classes:
                    counters[what].add(*vv)


    row = [E.td(x) for x in texts]
    if ll == 0:
        row.append(E.td(od(colspan="2"), 'words'))

    if ll == 1:
        row.append(E.td())

    for what in WHAT:
        row.append(E.td(od(klass='pad')))
        row.extend(counters[what].html())

    tablerows.append(E.tr(*row))


def limit(data, filekey, limiter):
    n = len(ALL_TEXTS)
    tablerows = []
    add_header(tablerows)
    tablerows.append(E.tr(od(klass="pad lineunder"), E.td(od(colspan=str(2 + 3*len(WHAT))))))
    tablerows.append(E.tr(od(klass="pad")))
    process([], data, limiter, tablerows)
    for i in range(n):
        tablerows.append(E.tr(od(klass="pad")))
        process([ALL_TEXTS[i]], data, limiter, tablerows)
        tablerows.append(E.tr(od(klass="pad")))
        for j in range(n):
            if j != i:
                process([ALL_TEXTS[i], ALL_TEXTS[j]], data, limiter, tablerows)
    write_html('output/pairs{}.html'.format(filekey), E.table(*tablerows))


def main():
    with open('output/extract2.json') as f:
        data = json.load(f)
    limit(data, '', lambda f,s: True)
    limit(data, '-abbr', lambda f,s: s)
    limit(data, '-1', lambda f,s: f == 1)
    limit(data, '-1-abbr', lambda f,s: s and f == 1)
    limit(data, '-rare', lambda f,s: f <= 5)
    limit(data, '-rare-abbr', lambda f,s: s and f <= 5)
    limit(data, '-common', lambda f,s: f > 5)
    limit(data, '-common-abbr', lambda f,s: s and f > 5)
    limit(data, '-verycommon', lambda f,s: f > 10)
    limit(data, '-verycommon-abbr', lambda f,s: s and f > 10)

main()
