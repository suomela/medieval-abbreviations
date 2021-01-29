#!/usr/bin/env python3

from collections import defaultdict, Counter, OrderedDict
import json
import lxml
from lxml.builder import E

ALL_TEXTS = [
    "Sloane2320",
    "Sloane3566", "Trinity", "Boston",
    "Gonville", "Takamiya",
]

CSS = """
body {
    color: #000;
    background-color: #fff;
    font-family: 'Open Sans', sans-serif;
    font-size: 15px;
    padding: 0px;
    margin: 10px;
    font-weight: 400;
}

#wrap {}

h1 {
    font-size: 30px;
    font-weight: 700;
    padding: 0px;
    margin: 0px;
}

h2 {
    font-size: 15px;
    font-weight: 700;
    padding: 0px;
    margin: 15px 0px;
}

table {
    border-collapse: collapse;
    padding: 0px;
    margin: 0px;
}

td {
    padding: 1px 0px;
    text-align: left;
    vertical-align: top;
}

td.x {
    text-align: right;
    min-width: 30px;
}

td.s {
    text-align: center;
}

td.y {
    text-align: left;
    padding-right: 10px;
    min-width: 30px;
}

td.w {
}
"""

def od(**x):
    return OrderedDict([(("class" if a == "klass" else a), str(b)) for a,b in sorted(x.items())])

def normalize(x):
    return x.lower()

def get_norm_words(d):
    return [ normalize(w) for x,w in d if w is not None ]

def write_html(filename, title, body):
    doc = E.html({"lang": "en"},
        E.head(
            E.title(title),
            E.link(od(rel="stylesheet", href="https://fonts.googleapis.com/css?family=Open+Sans:400,700&subset=latin-ext")),
            E.meta(od(charset="UTF-8")),
            E.meta(od(name="viewport", content="width=device-width, initial-scale=1")),
            E.style(CSS),
        ),
        E.body(
            E.div(od(id="wrap"),
                *body,
            )
        ),
    )
    with open(filename, 'w') as f:
        f.write('<!DOCTYPE html>\n')
        f.write(lxml.etree.tostring(doc, method='html', encoding=str))
        f.write('\n')


class Similarity:
    def __init__(self):
        self.p = {}
        self.raw = []

    def feed_row(self, d):
        self.raw.append(d)
        l = get_norm_words(d)
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

    def form_clusters(self):
        self.comp = defaultdict(list)
        aa = sorted(self.p.keys())
        for a in aa:
            x = self.get(a)
            self.comp[x].append(a)

    def row_to_cluster(self):
        self.rows = []
        for d in self.raw:
            l = get_norm_words(d)
            k = [ self.get(a) for a in l ]
            assert len(set(k)) == 1
            k = k[0]
            self.rows.append((k, d))

    def statistics(self):
        self.typelist = [
            'Everyone',
            'Someone',
            'Nobody',
            'Some but not all',
            'Roughly half',
        ]
        for a in ALL_TEXTS:
            self.typelist += [
                'Only ' + a,
                'All except ' + a,
            ]
        for a in ALL_TEXTS:
            for b in ALL_TEXTS:
                self.typelist += [
                    'Only ' + a + " + " + b,
                    'All except ' + a + " + " + b,
                ]

        self.total = Counter()
        self.classes = defaultdict(Counter)
        for k,d in self.rows:
            abbr = [ x for x,w in d ]
            count = Counter(abbr)
            types = []
            if count[0] == 0:
                types.append('Everyone')
            if count[1] == 0:
                types.append('Nobody')
            else:
                types.append('Someone')
            if count[0] > 0 and count[1] > 0:
                types.append('Some but not all')
            if abs(count[1] - count[0]) <= 1:
                types.append('Roughly half')
            posneg = [[], []]
            for i,text in enumerate(ALL_TEXTS):
                if abbr[i] is not None:
                    posneg[abbr[i]].append(i)
            for v,pn in enumerate(posneg):
                if 1 <= len(pn) <= 2:
                    texts = " + ".join([ALL_TEXTS[i] for i in pn])
                    label = ["All except", "Only"][v] + " " + texts
                    types.append(label)
            self.total[k] += 1
            for t in types:
                assert t in self.typelist, t
                self.classes[k][t] += 1

    def summarize(self, filekey):
        language,funclex = filekey

        doc = []
        doc.append(E.h1(language, ": ", funclex))
        title = language + " " + funclex

        kk = sorted(self.comp.keys())
        for t in self.typelist:
            r = []
            for k in kk:
                x = self.classes[k][t]
                y = self.total[k]
                q = (x+1)/(y+2)
                if x == 0 or y <= 2 or q < 0.5:
                    continue
                r.append((q,x,y,k))
            if len(r) == 0:
                continue
            r.sort(key=lambda z: z[0], reverse=True)
            doc.append(E.h2(t))
            table = []
            for q,x,y,k in r:
                table.append(E.tr(
                    E.td(od(klass="x"), str(x)),
                    E.td(od(klass="s"), "/"),
                    E.td(od(klass="y"), str(y)),
                    E.td(od(klass="w"), " ".join(self.comp[k])),
                ))
            doc.append(E.table(*table))
        filename = "output/examples-{}-{}.html".format(language.lower(), funclex.lower())
        write_html(filename, title, doc)

    def analyze(self, filekey):
        self.form_clusters()
        self.row_to_cluster()
        self.statistics()
        self.summarize(filekey)


def main():
    with open('output/extract.json') as f:
        data = json.load(f)

    sim = defaultdict(Similarity)

    for chunk in data:
        language = chunk['language']
        textmap = { x: i for i,x in enumerate(chunk['texts']) }
        clmap = { x: i for i,x in enumerate(chunk['classes']) }
        for row,cl,words in chunk['rows']:
            funclex = cl[clmap['lex-funct']]
            d = []
            for text in ALL_TEXTS:
                if text in textmap:
                    i = textmap[text]
                    d.append((row[i], words[i]))
                else:
                    d.append((None, None))
            sim[(language,funclex)].feed_row(d)

    for k in sorted(sim.keys()):
        sim[k].analyze(k)

main()
