#!/usr/bin/env python3

import collections
import glob
import json
import re
import lxml
from lxml.builder import E
import xlsxwriter

def od(**x):
    return collections.OrderedDict([(("class" if a == "klass" else a), str(b)) for a,b in sorted(x.items())])

def tei(x):
    return '{http://www.tei-c.org/ns/1.0}' + x

def div(e):
    a = e.get('type')
    b = e.get('n')
    if b is not None and b == '':
        b = None
    return a, b

def chunk_div(e):
    a, b = div(e)
    if a == 'running_text':
        assert b is None
        return None
    elif a == 'recipe':
        assert b is not None
        return b
    else:
        assert False, a


class Word:
    def __init__(self):
        self.full = ''
        self.abbr = False

    def feed(self, x):
        if x is not None:
            self.full += x.strip()

    def finish(self):
        assert self.full != ''
        self.full = ' '.join(self.full.split())
        x = self.full.lower()
        x = {
            'ye': 'the',
            'he': 'the',
            'hit': 'it',
            'hyt': 'it',
            'his': 'this',
            'hem': 'them',
            'fro': 'from',
            'froo': 'from',
            'yerof': 'thereof',
        }.get(x, x)
        x = re.sub(r'\s+', '', x)
        x = re.sub(r'[?*/_.]', '', x)
        x = re.sub(r'&', 'et', x)
        x = re.sub(r'\+t', 'þ', x)
        x = re.sub(r'\+3', 'ȝ', x)
        x = re.sub(r'þ', 'th', x)
        x = re.sub(r'^ȝ', 'gh', x)
        x = re.sub(r'(?<=[aiouy])ȝ', 'gh', x)
        x = re.sub(r'ȝ$', 'z', x)
        x = re.sub(r'ȝ', 'y', x)
        x = re.sub(r'ph', 'f', x)
        x = re.sub(r'th|d', 't', x)
        x = re.sub(r'[mn]', 'm', x)
        x = re.sub(r'[zsk]', 'c', x)
        x = re.sub(r'[jyea]', 'i', x)
        x = re.sub(r'[vw]', 'u', x)
        x = re.sub(r'([a-z])(?=\1)', '', x)
        x = re.sub(r'i?ri?', 'r', x)
        x = re.sub(r'cio', 'tio', x)
        x = re.sub(r'^hour', 'our', x)
        x = re.sub(r'(?<=..)i$', '', x)
        x = re.sub(r'(?<=..)is$', 's', x)
        self.norm = x
        x = re.sub(r'[xc]', 't', x)
        x = re.sub(r'[ou]', 'o', x)
        x = re.sub(r'(?<=.)[io]', '', x)
        x = re.sub(r'h', '', x)
        x = re.sub(r'([a-z])(?=\1)', '', x)
        x = {
            'tflt': 'tft',
        }.get(x, x)
        if x == '':
            x = '*'
        self.weak = x


class Chunk:
    def __init__(self, chapter, label):
        self.chapter = chapter
        self.label = label
        self.wc = 0
        self.words = []

class Text:
    def __init__(self, label, filename):
        self.label = label
        self.filename = filename
        tree = lxml.etree.parse(filename)
        root = tree.getroot()
        body = root.find(tei('text')).find(tei('body'))
        self.chunk = None
        self.chunks = []
        self.chunk_map = {}
        self.parse_top(body)
        assert self.chunk is None
        self.cleanup()

    def cleanup(self):
        for c in self.chunks:
            c.key2 = None
        for c in self.chunks:
            if c.label is None:
                c.orig = 'text'
            else:
                c.orig = c.label
        for i,c in enumerate(self.chunks):
            if c.chapter is None:
                if c.label == 'incipit':
                    c.chapter = self.chunks[i+1].chapter
                    c.key2 = c.key3 = 0
                elif c.label == 'explicit':
                    c.chapter = self.chunks[i-1].chapter
                    c.key2 = c.key3 = 9
                else:
                    assert False
        for c in self.chunks:
            c.chapter, c.key1 = {
                'JB_Latin_long': ('Latin', 1),
                'JB_English': ('English', 2),
                'JB_Epistolary': ('Epistolary', 3),
            }[c.chapter]

            c.chapter = re.sub(r'^JB_', '', c.chapter)
            c.chapter = re.sub(r'_long$', '', c.chapter)
            if c.label is not None:
                if c.chapter == 'Epistolary':
                    c.label = re.sub(r'^epistolary', '', c.label)
                elif c.chapter == 'Latin':
                    c.label = re.sub(r'^(JBlong|Burgundy)', '', c.label)
                if c.key2 is None:
                    c.key2 = c.key3 = int(c.label)
        for i,c in enumerate(self.chunks):
            if c.label is None:
                c0, c1 = self.chunks[i-1], self.chunks[i+1]
                assert c0.chapter == c.chapter == c1.chapter
                c.label = '({}-{})'.format(c0.label, c1.label)
                c.key2, c.key3 = c0.key2, c1.key3
        for c in self.chunks:
            c.key = '{}{}{}'.format(c.key1, c.key2, c.key3)
            c.name = '{} {}'.format(c.chapter, c.label)
            self.chunk_map[c.key] = c

    def last_same(self, chapter, label):
        if not len(self.chunks):
            return
        p = self.chunks[-1]
        return (p.chapter, p.label) == (chapter, label)

    def start_chunk(self, chapter, label):
        assert self.chunk is None
        if self.last_same(chapter, label):
            self.chunk = self.chunks.pop()
        else:
            self.chunk = Chunk(chapter, label)

    def finish_chunk(self):
        if self.chunk is not None:
            if self.chunk.wc:
                self.chunks.append(self.chunk)
            self.chunk = None

    def parse_top(self, elem):
        skip = {tei(x) for x in ['lb', 'gb']}
        for child in elem:
            if child.tag == tei('div'):
                a, b = div(child)
                if a in ['incipit', 'explicit']:
                    assert b is None
                    self.parse_chunk(child, None, a)
                elif a in ['chapter']:
                    assert b is not None
                    self.parse_chapter(child, b)
                else:
                    assert False, a
            elif child.tag in skip:
                pass
            else:
                assert False, child.tag

    def parse_chapter(self, elem, chapter):
        skip = {tei(x) for x in ['lb', 'gb']}
        for child in elem:
            if child.tag == tei('div'):
                self.parse_chunk(child, chapter, chunk_div(child))
            elif child.tag in skip:
                pass
            else:
                assert False, child.tag

    def parse_chunk(self, elem, chapter, label):
        self.start_chunk(chapter, label)
        self.parse_more(elem)
        self.finish_chunk()

    def parse_other_chunk(self, elem, label):
        old = self.chunk
        if old.label == label:
            self.parse_more(elem)
        else:
            self.finish_chunk()
            self.parse_chunk(elem, old.chapter, label)
            self.start_chunk(old.chapter, old.label)

    def parse_more(self, elem):
        recurse = {tei(x) for x in ['abbr', 'am', 'choice', 'ex', 'expan', 'gb', 'hi', 'lb', 'p', 'pb', 'pc']}
        for child in elem:
            if child.tag in recurse:
                self.parse_more(child)
            elif child.tag == tei('div'):
                self.parse_other_chunk(child, chunk_div(child))
            elif child.tag == tei('w'):
                self.chunk.wc += 1
                self.parse_word(child)
            else:
                assert False, child.tag

    def parse_word(self, elem):
        word = Word()
        self.parse_word_more(elem, word)
        word.finish()
        self.chunk.words.append(word)

    def parse_word_more(self, elem, word):
        word.feed(elem.text)
        recurse = {tei(x) for x in ['am', 'choice', 'ex', 'expan', 'gb', 'hi', 'lb', 'pc']}
        for child in elem:
            if child.tag in recurse:
                self.parse_word_more(child, word)
            elif child.tag == tei('abbr'):
                word.abbr = True
            else:
                assert False, child.tag
            word.feed(child.tail)


Match = collections.namedtuple('Match', 'ii limit weak')

class Num:
    def __init__(self, v=0):
        self.v = v


class Align:
    def __init__(self):
        self.text_map = {}
        self.texts = []

    def feed(self, label, filename):
        assert label not in self.texts
        text = Text(label, filename)
        self.text_map[label] = text
        self.texts.append(text)

    def process(self):
        self.names = {}
        for text in self.texts:
            for chunk in text.chunks:
                if chunk.key in self.names:
                    assert self.names[chunk.key] == chunk.name
                else:
                    self.names[chunk.key] = chunk.name
        self.index()
        self.summary = collections.Counter()
        self.wb = xlsxwriter.Workbook('output/jburgundy.xlsx')
        self.formats = {}
        for key in sorted(self.names.keys()):
            self.align(key)
        self.write_summary()
        self.wb.close()

    def fmt(self, ff):
        if len(ff) == 0:
            return None
        z = {}
        for f in ff:
            z.update(f)
        t = tuple(sorted(z.items()))
        if t not in self.formats:
            format = self.wb.add_format(z)
            self.formats[t] = format
        return self.formats[t]

    def index(self):
        tablerows = []

        def add_row(r, kl=None, link=None):
            r2 = []
            for j,x in enumerate(r):
                if j:
                    r2.append(E.td(od(klass="pad"), ""))
                r2.append(x)
            attr = collections.OrderedDict()
            if kl is not None:
                attr["class"] = kl
            if link is not None:
                attr["onclick"] = "window.open('{}');".format(link)
            tablerows.append(E.tr(attr, *r2))

        add_row([E.td(text.label) for text in self.texts], "head")

        prev = '1'
        for key in sorted(self.names.keys()):
            r = []
            link = "{}.html".format(key)
            for text in self.texts:
                if key in text.chunk_map:
                    r.append(E.td(text.chunk_map[key].orig))
                else:
                    r.append(E.td(""))
            if prev != key[0]:
                prev = key[0]
                add_row(r, "sep hover", link=link)
            else:
                add_row(r, "hover", link=link)

        doc = E.html({"lang": "en"},
            E.head(
                E.title("John of Burgundy"),
                E.link(od(rel="stylesheet", href="style.css", type="text/css")),
                E.meta(od(charset="UTF-8")),
                E.meta(od(name="viewport", content="width=device-width, initial-scale=1")),
            ),
            E.body(
                E.div(od(id="wrap"),
                    E.table(*tablerows),
                )
            ),
        )

        filename = 'output/index.html'
        with open(filename, 'w') as f:
            f.write('<!DOCTYPE html>\n')
            f.write(lxml.etree.tostring(doc, method='html', encoding=str))
            f.write('\n')

    def write_summary(self):
        dump = {
            'texts': [ text.label for text in self.texts ],
            'abbr': dict(self.summary),
        }
        with open('output/summary.json', 'w') as f:
            json.dump(dump, f, sort_keys=True, indent=1)
 
    def align(self, key):
        print(key, self.names[key])
        labels = []
        chunks = []
        for text in self.texts:
            if key in text.chunk_map:
                labels.append(text.label)
                chunks.append(text.chunk_map[key])
        n = len(chunks)

        def peek(j, i, limit, weak):
            w = ''
            while True:
                if i >= len(chunks[j].words):
                    return None
                word = chunks[j].words[i]
                w += word.weak if weak else word.norm
                if len(w) >= limit:
                    return w
                i += 1

        def find_between(aa, bb, limit, weak):
            o = 1
            seen = collections.defaultdict(dict)
            while True:
                progress = False
                for j in range(n):
                    if aa[j] + o >= bb[j]:
                        continue
                    w = peek(j, aa[j] + o, limit, weak)
                    if w is None:
                        continue
                    progress = True
                    if j not in seen[w]:
                        seen[w][j] = o
                        if len(seen[w]) == n:
                            return seen[w]
                if not progress:
                    return None
                o += 1

        def refine(aa, bb, limit, weak):
            new_matches = []
            ii = aa
            while True:
                vv = find_between(ii, bb, limit, weak)
                if vv is None:
                    break
                ii = [ii[j] + vv[j] for j in range(n)]
                new_matches.append(Match(ii, limit, weak))
            return new_matches

        ff = [ -1 for j in range(n) ]
        nn = [ len(chunks[j].words) for j in range(n) ]

        matches = [Match(ff, None, None), Match(nn, None, None)]

        for weak in [False, True]:
            rg = range(2,40) if weak else range(1,40)
            for limit in reversed(rg):
                new_matches = [matches[0]]
                for mi in range(1, len(matches)):
                    aa = matches[mi-1]
                    bb = matches[mi]
                    new_matches.extend(refine(aa.ii, bb.ii, limit, weak))
                    new_matches.append(bb)
                matches = new_matches
                print(limit, len(matches))

        matches.pop(0)
        matches.pop()

        for mm in matches:
            ma = ''
            j = 0
            for text in self.texts:
                if key in text.chunk_map:
                    w = text.chunk_map[key].words[mm.ii[j]]
                    ma += '1' if w.abbr else '0'
                    j += 1
                else:
                    ma += 'N'
            self.summary[ma] += 1

        tablerows = []
        ws = self.wb.add_worksheet(self.names[key])
        wsr = Num(0)

        def add_row(r, kl=None):
            r2 = []
            for j,x in enumerate(r):
                if j:
                    r2.append(E.td(od(klass="pad"), ""))
                r2.append(x)
            if kl is None:
                tablerows.append(E.tr(*r2))
            else:
                tablerows.append(E.tr(od(klass=kl), *r2))

        add_row([E.td(l) for l in labels], "head")
        for j,x in enumerate(labels):
            ws.set_column(2*j, 2*j, 5)
            ws.set_column(2*j+1, 2*j+1, 16)
            ws.write_string(wsr.v, 2*j, '#', self.fmt([{'bold':True}, {'align': 'right'}]))
            ws.write_string(wsr.v, 2*j + 1, x, self.fmt([{'bold':True}]))
        ws.set_column(2*n, 2*n+1, 8)
        ws.write_string(wsr.v, 2*n, 'score', self.fmt([{'bold':True}, {'align': 'right'}]))
        ws.write_string(wsr.v, 2*n+1, 'fix', self.fmt([{'bold':True}, {'align': 'right'}]))
        wsr.v += 1

        ii = [ 0 for j in range(n) ]

        def word_cell(w):
            kl = "abbr" if w.abbr else "normal"
            return(E.td(od(klass=kl, title="{} {}".format(w.norm, w.weak)), w.full))

        def add_gap(mm):
            while True:
                r = []
                seen = False
                for j,c in enumerate(chunks):
                    if ii[j] < mm.ii[j]:
                        w = c.words[ii[j]]
                        r.append(word_cell(w))
                        col = {'color': '#ff0000'}
                        ws.write_number(wsr.v, 2*j, ii[j])
                        ws.write_string(wsr.v, 2*j + 1, w.full, self.fmt([col, {'bold': w.abbr}]))
                        ii[j] += 1
                        seen = True
                    else:
                        r.append(E.td(od(klass="empty"), ''))
                if not seen:
                    return
                add_row(r, "gap")
                wsr.v += 1

        def add_match(mm):
            r = []
            for j,c in enumerate(chunks):
                assert ii[j] == mm.ii[j]
                w = c.words[ii[j]]
                r.append(word_cell(w))
                col = {'color': '#0000ff' if w.abbr else '#000000'}
                ws.write_number(wsr.v, 2*j, ii[j])
                ws.write_string(wsr.v, 2*j + 1, w.full, self.fmt([col, {'bold': w.abbr}]))
                ii[j] += 1
            add_row(r, "match")
            col = {'color': '#ff0000' if mm.weak or mm.limit < 10 else '#000000'}
            ws.write_number(wsr.v, 2*n, mm.limit + (0 if mm.weak else 50), self.fmt([col]))
            wsr.v += 1

        for mm in matches:
            add_gap(mm)
            add_match(mm)
        add_gap(Match(nn, None, None))

        doc = E.html({"lang": "en"},
            E.head(
                E.title(self.names[key]),
                E.link(od(rel="stylesheet", href="style.css", type="text/css")),
                E.meta(od(charset="UTF-8")),
                E.meta(od(name="viewport", content="width=device-width, initial-scale=1")),
            ),
            E.body(
                E.div(od(id="wrap"),
                    E.table(*tablerows),
                )
            ),
        )

        filename = 'output/{}.html'.format(key)
        with open(filename, 'w') as f:
            f.write('<!DOCTYPE html>\n')
            f.write(lxml.etree.tostring(doc, method='html', encoding=str))
            f.write('\n')
        print()


def main():
    align = Align()
    for filename in sorted(glob.glob('data/*.xml')):
        m = re.fullmatch(r'data/(.*)_DSH_final\.xml', filename)
        assert m
        label = m.group(1)
        align.feed(label, filename)
    align.process()

main()
