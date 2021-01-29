#!/usr/bin/env python3

import json
import pandas as pd
import numpy as np
import plotly.offline as py

TEXTS = [
    "Sloane2320",
    "Sloane3566", "Trinity", "Boston",
    "Gonville", "Takamiya",
]

COLOR = {
    ('incipit', 'Latin'): '#000',
    ('explicit', 'Latin'): '#000',
    ('recipe', 'Latin'): '#eee',
    ('text', 'Latin'): '#fff',
    ('text', 'English'): '#fff',
}

MORE = ['lex', 'three syllables']

def smooth(window, x):
    return pd.Series(x).rolling(window, win_type='triang', center=True).mean()

def plot(what, window):
    with open('output/extract.json') as f:
        data = json.load(f)

    keys1 = TEXTS + ['min', 'avg', 'max']
    if what is None:
        keys = keys1 + MORE
    else:
        keys = keys1

    shapes = []
    prevchapter = None
    rows1 = { x: [] for x in keys }
    rows2 = { x: [] for x in keys }
    labels = { x: [] for x in TEXTS }

    def flush():
        for x in keys:
            rows1[x].extend(smooth(window, rows2[x]))
            rows2[x] = []

    start = 0
    for chunk in data:
        if prevchapter != chunk['chapter']:
            if prevchapter is not None:
                flush()
            prevchapter = chunk['chapter']
        textmap = { x: i for i,x in enumerate(chunk['texts']) }
        clmap = { x: i for i,x in enumerate(chunk['classes']) }

        filtered = []
        for row,cl,words in chunk['rows']:
            classes = set()
            y = cl[clmap['lex-funct']]
            assert y in ['func', 'lex']
            classes.add(y)
            for x in ['numeral', 'measurement', 'three syllables']:
                y = cl[clmap[x]]
                assert y in ['yes', 'no', '']
                if y == 'yes':
                    classes.add(x)

            if what is None or what in classes:
                filtered.append([row, words])
            if what is None:
                for x in MORE:
                    rows2[x].append(1 if x in classes else 0)

        end = start + len(filtered)
        shapes.append({
            'type': 'rect',
            'xref': 'x',
            'yref': 'paper',
            'x0': start,
            'x1': end,
            'y0': 0,
            'y1': 1,
            'line': { 'width': 0 },
            'fillcolor': COLOR[(chunk['kind'], chunk['language'])],
            'layer': 'below',
        })
        for row, words in filtered:
            values = []
            for x in TEXTS:
                if x in textmap:
                    v = row[textmap[x]]
                    rows2[x].append(v)
                    w = words[textmap[x]]
                    if v == 1:
                        w += " *"
                    labels[x].append(w)
                    values.append(v)
                else:
                    rows2[x].append(np.nan)
                    labels[x].append(None)
            rows2['min'].append(min(values))
            rows2['max'].append(max(values))
            rows2['avg'].append(sum(values) / len(values))
        start = end
    flush()
    df = pd.DataFrame(rows1)
    curve = []
    # curve += [{
    #     'x': df.index,
    #     'y': df[x],
    #     'name': x,
    #     'line': {'color': '#000', 'width': 1},
    # } for x in ['avg']]
    curve += [{
        'x': df.index,
        'y': df[x],
        'name': x,
        'text': labels[x],
    } for x in TEXTS]
    if what is None:
        curve.append({
            'x': df.index,
            'y': df['lex'],
            'name': 'lex density',
            'line': { 'color': '#000', 'dash': 'dot', 'width': 1 },
        })
        curve.append({
            'x': df.index,
            'y': df['three syllables'],
            'name': 'three syllables',
            'line': { 'color': '#000', 'dash': 'dash', 'width': 1 },
        })
    title = 'abbreviations in {} words — window size {}'.format(
        'all' if what is None else what,
        window
    )
    layout = {
        'title': title,
        'shapes': shapes,
        'yaxis': {
            'range': [0,0.7],
            'hoverformat': '.3f',
        },
        'xaxis': {
            'showgrid': False,
        },
    }
    fig = {'data': curve, 'layout': layout}
    if what is None:
        filename = 'output/plot-{}.html'.format(window)
    else:
        filename = 'output/plot-{}-{}.html'.format(what, window)
    py.plot(fig, filename=filename)

def main():
    for what in [None, 'func', 'lex']:
    # for what in [None]:
        for window in [151, 301]:
            plot(what, window)

main()
