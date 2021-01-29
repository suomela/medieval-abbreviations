#!/usr/bin/env python3

import collections
import glob
import json
import re
import lxml
from lxml.builder import E

def od(**x):
    return collections.OrderedDict([(("class" if a == "klass" else a), str(b)) for a,b in sorted(x.items())])

def tei(x):
    return '{http://www.tei-c.org/ns/1.0}' + x

class Text:
    def __init__(self, label, filename):
        tree = lxml.etree.parse(filename)
        root = tree.getroot()
        body = root.find(tei('text')).find(tei('body'))
        print('{}:'.format(label))
        print()
        self.parse(body, 1)
        print()

    def parse(self, elem, depth):
        for child in elem:
            if child.tag == tei('div'):
                a = child.get('type')
                b = child.get('n')
                if b is not None and b != '':
                    t = '{} {}'.format(a, b)
                else:
                    t = a
                print('{}{}'.format('    ' * depth, t))
                self.parse(child, depth + 1)

def main():
    for filename in sorted(glob.glob('data/*.xml')):
        m = re.fullmatch(r'data/(.*)_DSH_final\.xml', filename)
        assert m
        label = m.group(1)
        Text(label, filename)

main()
