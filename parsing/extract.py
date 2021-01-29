#!/usr/bin/env python3

import collections
import glob
import json
import re
import lxml
from lxml.builder import E
import xlrd

CLLABELS  = ['A lex-funct', 'B numeral?', 'C measurement?', 'D Three syllables?', 'E Per']
CLLABELS2 = [  'lex-funct',   'numeral',    'measurement',    'three syllables',  'per'  ]

AM_MAP = {
    "sup-2": "^\uA75B",
    "sup-4": "^\uA75D",
    "sup-hook": "^\uA770",
    "sup- a": "^a",
    "sup-a":  "^a",
    "sup-c":  "^c",
    "sup-d":  "^d",
    "sup-e":  "^e",
    "sup-i":  "^i",
    "sup-m":  "^m",
    "sup-o":  "^o",
    "sup-r":  "^r",
    "sup-s":  "^s",
    "sup-t":  "^t",
    "sup-u":  "^u",
    "sup-x":  "^x",
    "sup-z":  "^z",
    "sup-do": "^d^o",
    "sup-li": "^l^i",
    "sup-us": "^u^s",

    "&": "&",
    "POUND": "£",
    "+R": "\u211E",
    "2": "\uA75B",
    "4": "\uA75D",
    "9": "\uF1A6",
    "DRACHM": "\uF2E6",
    "hook": "^\uA770",
    "loop": "\uA76D",
    "loopedq": "\uA759",
    "mac": "\uF00D",
    "OUNCE": "\u2125",
    "per": "\uA751",
    "pro": "\uA753",
    "SEMIS": "\uE8B7",
    "ss": "\uE8B7",
    "strikeh": "\u0127",
    "strikel": "\u0142",
    "strikeq": "\uA757",
    "strikev": "\uE8BB",
    "z": "\uA76B",

    ".": ".",
    ".i.": ".i.",
    ".p.": ".p.",
    ".s.": ".s.",
    "a": "^a",
    "c": "^c",
    "crossedq": "\uA757",
    "m": "^m",
    "p.": "p.",
    "pre": "p^\uA770",
    "quam": "\uA759",
    "r": "^r",
    "RECIPE": "\u211E",
    "Recipe": "\u211E",
    "RECIPE.": "\u211E",
    "strike": "\u0142",
    "strikeb": "\u0243",
    "t": "^t",
}

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


def fix_word(x):
    return ' '.join(x.split()).replace("+t", "þ")

class Word:
    def __init__(self):
        self.full = ''
        self.short = ''
        self.abbr = False

    def feed(self, x):
        if x is not None:
            self.full += x.strip()

    def feed_short(self, x):
        if x is not None:
            self.short += x.strip()

    def finish(self):
        assert self.full != ''
        self.full = fix_word(self.full)
        if self.abbr:
            assert self.short != ''
            self.short = fix_word(self.short)
        else:
            assert self.short == ''


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
                c.kind = 'text'
                c0, c1 = self.chunks[i-1], self.chunks[i+1]
                assert c0.chapter == c.chapter == c1.chapter
                c.label = '({}-{})'.format(c0.label, c1.label)
                c.key2, c.key3 = c0.key2, c1.key3
            elif c.label in ('incipit', 'explicit'):
                c.kind = c.label
            else:
                assert 1 <= int(c.label) <= 5
                c.kind = 'recipe'
            if c.kind == 'text' and c.chapter == 'English':
                c.language = 'English'
            else:
                c.language = 'Latin'
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
        recurse = {tei(x) for x in ['choice', 'ex', 'expan', 'gb', 'hi', 'lb', 'pc']}
        for child in elem:
            if child.tag in recurse:
                self.parse_word_more(child, word)
            elif child.tag == tei('abbr'):
                assert not word.abbr
                word.abbr = True
                self.parse_word_abbr(child, word)
            else:
                assert False, child.tag
            word.feed(child.tail)

    def parse_word_abbr(self, elem, word):
        word.feed_short(elem.text)
        recurse = {tei(x) for x in ['gb', 'hi', 'lb', 'pc']}
        for child in elem:
            if child.tag in recurse:
                self.parse_word_abbr(child, word)
            elif child.tag == tei('am'):
                self.parse_word_am(child, word)
            else:
                assert False, child.tag
            word.feed_short(child.tail)

    def parse_word_am(self, elem, word):
        x = elem.text
        x = x.strip(" ")
        x = x.rstrip("?")
        x = re.sub(r"\(sic\)$", "", x)
        word.feed_short(AM_MAP[x])
        for child in elem:
            assert False, child.tag


class Num:
    def __init__(self, v=0):
        self.v = v


def common(chunks, what):
    s = set()
    for c in chunks:
        s.add(getattr(c, what))
    assert len(s) == 1
    return list(s)[0]

def fix_class(s):
    s = s.lower().strip()
    if s in ['ye', 'yes¨']:
        s = 'yes'
    return s

class Align:
    def __init__(self):
        self.text_map = {}
        self.texts = []
        self.fixes0 = 0
        self.fixes1 = 0
        self.rows = 0

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
        self.book = xlrd.open_workbook('data/jburgundy.xlsx')
        result = []
        for key in sorted(self.names.keys()):
            record = self.extract_one(key)
            if record is not None:
                result.append(record)
        with open('output/extract.json', 'w') as f:
            json.dump(result, f, sort_keys=True, indent=1)
        print("rows: {}".format(self.rows))
        print("fix 0: {}".format(self.fixes0))
        print("fix 1: {}".format(self.fixes1))

    def extract_one(self, key):
        sheet = self.book.sheet_by_name(self.names[key])
        labels = []
        chunks = []
        for text in self.texts:
            if key in text.chunk_map:
                labels.append(text.label)
                chunks.append(text.chunk_map[key])
        n = len(chunks)
        if n == 1:
            return None
        # print(key, self.names[key], labels)
        for j,label in enumerate(labels):
            assert sheet.cell(0, 2*j).value == '#'
            assert sheet.cell(0, 2*j+1).value == label
        cscore = 2*n
        cfix = cscore + 1
        ccl = cfix + 1
        ncl = len(CLLABELS)
        got_head = [ sheet.cell(0, i).value for i in range(ccl, ccl+ncl) ]
        assert got_head == CLLABELS, got_head

        rows = []
        count_good = 0
        count_bad = [0 for i in range(n)]
        current = [0 for i in range(n)]
        for r in range(1, sheet.nrows):
            score = sheet.cell(r, cscore).value
            fix = sheet.cell(r, cfix).value
            self.rows += 1
            if fix == 1:
                self.fixes1 += 1
                assert score == ''
                good = True
            elif fix == 0:
                self.fixes0 += 1
                assert score != ''
                good = False
            elif score != '':
                good = True
                assert good >= 1
                assert fix == ''
            else:
                good = False
                assert fix == ''
            row = []
            words = []
            short = []
            for j in range(n):
                v = sheet.cell(r, 2*j).value
                if v == '':
                    row.append(None)
                else:
                    v = int(v)
                    assert current[j] == v
                    current[j] += 1
                    if not good:
                        count_bad[j] += 1
                    word = chunks[j].words[v]
                    row.append(1 if word.abbr else 0)
                    words.append(word.full)
                    short.append(word.short)
            cl = [ fix_class(sheet.cell(r, i).value) for i in range(ccl, ccl+ncl) ]
            assert cl[0] in ['func', 'lex', 'lex???', 'yes', 'no', '']
            for i in range(1,4):
                assert cl[i] in ['yes', 'no', '']
            if good:
                count_good += 1
                if cl[0] not in ['func', 'lex']:
                    print('{}: row {}, {} = "{}"'.format(self.names[key], r+1, CLLABELS[0], cl[0]))
                # for i in range(1,4):
                #     if cl[i] not in ['yes', 'no']:
                #         print('{}: row {}, {} = "{}"'.format(self.names[key], r+1, CLLABELS[i], cl[i]))
                for j in range(n):
                    assert row[j] is not None
                rows.append([row, cl, words, short])
                # print(row, cl)

        assert count_good == len(rows)
        for j in range(n):
            assert current[j] == len(chunks[j].words)
            assert current[j] == count_good + count_bad[j]

        return {
            'key': key,
            'name': self.names[key],
            'texts': labels,
            'rows': rows,
            'chapter': common(chunks, 'chapter'),
            'kind': common(chunks, 'kind'),
            'language': common(chunks, 'language'),
            'classes': CLLABELS2,
            'aligned': count_good,
            'unaligned': count_bad,
            'total': current,
        }

fixes = collections.Counter()

def main():
    align = Align()
    for filename in sorted(glob.glob('data/*.xml')):
        m = re.fullmatch(r'data/(.*)_DSH_final\.xml', filename)
        assert m
        label = m.group(1)
        align.feed(label, filename)
    align.process()

main()
