#!/usr/bin/env python3

import math
from collections import Counter, defaultdict
import colorsys
import json
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot

matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = "Junicode"
matplotlib.rcParams["font.weight"] = "regular"
matplotlib.rcParams["mathtext.default"] = "regular"

def myhsv(h,s,v):
    rgb = colorsys.hsv_to_rgb(h/360.0, s/100.0, v/100.0)
    return "#%02x%02x%02x" % tuple(round(x * 255) for x in rgb)

dorange = myhsv(20, 100, 80)
orange = myhsv(20, 65, 95)
lorange = myhsv(20, 15, 100)
llorange = myhsv(20, 8, 100)
dblue = myhsv(200, 95, 70)
blue = myhsv(200, 85, 80)
lblue = myhsv(200, 15, 90)
llblue = myhsv(200, 8, 99)
dpurp = myhsv(260, 100, 95)
purp = myhsv(260, 30, 95)
llpurp = myhsv(260, 5, 99)
dgreen = myhsv(100, 100, 50)
green = myhsv(100, 40, 90)
llgreen = myhsv(100, 8, 99)
black = myhsv(0, 0, 0)
llblack = myhsv(0, 0, 90)
lllblack = myhsv(0, 0, 95)
dred = myhsv(0, 90, 80)
red = myhsv(0, 70, 90)
llred = myhsv(0, 5, 99)
gray = myhsv(0, 0, 30)
lgray = myhsv(0, 0, 80)

def darker(rgb, amount):
    rgb = rgb.lstrip("#")
    r,g,b = [int(rgb[2*x:2*x+2], 16)/255.0 for x in range(3)]
    h,l,s = colorsys.rgb_to_hls(r,g,b)
    l = amount
    r,g,b = colorsys.hls_to_rgb(h,l,s)
    return "#%02x%02x%02x" % tuple(round(x * 255) for x in [r,g,b])

color_range = ['#ffffcc','#a1dab4','#41b6c4','#2c7fb8','#253494']
bcolor_range = [myhsv(0,0,i) for i in [99,95,90,85,80]]
tcolor_range = [None] + [ darker(x, 0.4) for x in color_range[1:] ]


ALL_TEXTS = [
    "Sloane2320",
    "Sloane3566", "Trinity", "Boston",
    "Gonville", "Takamiya",
]


def textnamemap(text):
    assert text in ALL_TEXTS
    return re.sub(r"(\d+)", r" \1", text)

def gen_fig_ax(texts, xtot, ytot, figsize):
    fig = matplotlib.pyplot.figure(figsize=figsize)
    ax = fig.add_axes([0.0, 0.1, 1.0, 0.9])
    ax.set_axis_off()
    ax.set_xlim((0, xtot))
    ax.set_ylim((0, ytot))

    for j, text in enumerate(texts):
        ax.text(
            0.5 + j, -0.01 * ytot, textnamemap(text),
            horizontalalignment="center", verticalalignment="top",
            color="#000000",
        )

    return fig, ax


def figsave(fig, basename):
    print(basename)
    fig.savefig("output/{}.png".format(basename), dpi=300)
    fig.savefig("output/{}.pdf".format(basename))
    matplotlib.pyplot.close(fig)


def legend(fig, textcols):
    width, height = fig.get_size_inches()
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_axis_off()

    font_width_factor = 0.065
    scale = 5
    margin = 0.5
    ax.set_xlim((0, scale * width))
    ax.set_ylim((0, scale * height))

    pos = margin
    for i,tc in enumerate(textcols):
        text, cols, tcol = tc
        for col in cols:
            ax.add_patch(matplotlib.patches.Rectangle(
                (pos, margin),
                1/len(cols), 1,
                facecolor=col,
            ))
            pos += 1/len(cols)
        t = ax.text(
            0.2 + pos, margin + 0.45, text,
            horizontalalignment="left", verticalalignment="center",
            color="#000000",
        )
        pos += 1.0 + font_width_factor * scale * len(text)


def normalize(x):
    return x.lower().rstrip("?")

def representative(row):
    counter = Counter()
    for x in row:
        x = normalize(x)
        counter[x] += 1
    counts = counter.most_common()
    counts.sort(key=lambda x: (-x[1], x[0]))
    return counts[0][0]

def example_counts(ex):
    counter = Counter()
    orig = defaultdict(set)
    orig_short = defaultdict(Counter)
    for r,short in ex:
        rep = representative(r)
        counter[rep] += 1
        for x in r:
            orig[rep].add(x)
        for x in short:
            if x != "":
                orig_short[rep][x] += 1
    counts = counter.most_common()
    counts.sort(key=lambda x: (-x[1], x[0]))
    return counts, orig, orig_short

def pick_repr(counts):
    counts = counts.most_common()
    counts.sort(key=lambda x: (-x[1], x[0]))
    return counts[0][0]

def latexify(x):
    return re.sub(r"\^(.)", r"$^{\1}$", x)

def draw_overview():
    texts = ALL_TEXTS
    with open("output/extract.json") as f:
        data = json.load(f)

    chapterskip = 200
    chapterplace = 0.75 * chapterskip
    pad = 80
    total = pad / 2
    blocks = []
    chapters = []
    labels = []
    curchapt = None
    for chunk in data:
        textmap = { x: i for i,x in enumerate(chunk['texts']) }
        clmap = { x: i for i,x in enumerate(chunk['classes']) }
        lang = chunk["language"]
        good = chunk["aligned"]

        if chunk['chapter'] != curchapt:
            bottom = total
            curchapt = chunk['chapter']
            bottom += chapterskip
            mid = total + chapterplace
            chaptname = {
                "Latin": "Latin: long version",
                "English": "English version",
                "Epistolary": "Latin: epistolary version",
            }[curchapt]
            chapters.append((mid, chaptname))
            total = bottom + pad

        bottom = total
        for j, text in enumerate(texts):
            if text not in textmap:
                continue
            jj = textmap[text]

            abbrcount = 0
            for row, cl, words, short in chunk["rows"]:
                abbrcount += row[jj]
            assert abbrcount <= good

            bad = chunk['unaligned'][jj]
            blocks.append(("aligned", lang, j, total, total + good, abbrcount/good))
            blocks.append(("unaligned", lang, j, total + good, total + good + bad, 1.0))
            bottom = max(bottom, total + good + bad)
        mid = (total + bottom) / 2

        label = chunk["kind"]

        if chunk["chapter"] == "Epistolary" and chunk["kind"] == "explicit":
            mid += 20  # manual tweaking for the last row label

        labels.append((mid, label))
        total = bottom + pad

    fig, ax = gen_fig_ax(texts, len(texts) + 0.6, total, (6, 9))

    casecols = [("Latin", [lblue, blue], dblue), ("English", [lorange, orange], dorange)]
    legend(fig, casecols + [
        ("abbreviated", [cols[1] for case, cols, tcol in casecols], None),
        ("spelled out", [cols[0] for case, cols, tcol in casecols], None),
        ("unaligned", [lgray], None),
    ])

    width = 0.8
    margin = (1 - width) / 2
    for b in blocks:
        kind, lang, j, y0, y1, part = b
        if kind == "aligned":
            cols = { case: cols for case, cols, tcol in casecols }[lang]
        elif kind == "unaligned":
            cols = (lgray, lgray)
        else:
            assert False, kind

        for col, part0, part1 in [
            (cols[1], 0.0, part),
            (cols[0], part, 1.0),
        ]:
            if part0 == part1:
                continue
            ax.add_patch(matplotlib.patches.Rectangle(
                (margin + j + width * part0, total - y1),
                width * (part1 - part0), y1 - y0,
                facecolor=col,
            ))

    for y, label in chapters:
        ax.text(
            margin, total - y, label,
            horizontalalignment="left", verticalalignment="center",
            color="#000000",
            style="italic",
            fontsize=12,
        )

    for y, label in labels:
        ax.text(
            len(texts), total - y, label,
            horizontalalignment="left", verticalalignment="center",
            color="#000000",
            style="italic",
            fontsize=9,
        )

    figsave(fig, "overview")



def draw_blocks_base(key, casecols, flags, restrict=None, words_only=None):
    if words_only is None:
        words_only = [ i for i,cc in enumerate(casecols) ]

    filename = "" if restrict is None else "-" + restrict
    with open("output/optimized{}.json".format(filename)) as f:
        opt = json.load(f)
        texts = opt["texts"]
        rows = opt["rows"]

    sort = ("sort" in flags)
    words = ("words" in flags)

    pad = 20
    total = sum(c + pad for r,c,counts in rows)

    def rowkey(row):
        r, c, examples = row
        s = 0
        for i, cc in enumerate(casecols):
            case, cols, tcol = cc
            ex = examples.get(key + " " + case, [])
            f = len(ex)/c
            s += i * f
        return (-s, c)

    if sort:
        rows.sort(key=rowkey)

    if len(words_only) == 1:
        ncols = 4
        colspace = 3.0
    elif len(words_only) == 2:
        ncols = 3
        colspace = 2.5
    else:
        ncols = 1
        colspace = 0.9
    extra_space = colspace * len(words_only) if words else 0
    fig, ax = gen_fig_ax(texts, len(texts) + extra_space, total, (8 if words else 6, 9))

    legend(fig, casecols + [
        ("abbreviated", [cols[1] for case, cols, tcol in casecols], None),
        ("spelled out", [cols[0] for case, cols, tcol in casecols], None),
    ])

    width = 0.9
    margin = (1 - width) / 2

    textfile = []

    y = 0
    for r,c,examples in rows:
        textfile.append(" + ".join(text.upper() for i, text in enumerate(texts) if r[i] == 1))
        textfile.append("")

        f0 = 0
        jj = 0
        for j, casecol in enumerate(casecols):
            case, cols, tcol = casecol
            ex = examples.get(key + " " + case, [])
            f = len(ex)/c
            textfile.append("  {}: {}/{}".format(case, len(ex), c))
            textfile.append("")
            for i, text in enumerate(texts):
                v = r[i]
                assert v in [0,1]
                ax.add_patch(matplotlib.patches.Rectangle(
                    (margin + i + f0 * width, y),
                    f * width, c,
                    facecolor=cols[v],
                ))
            f0 += f
            if words and j in words_only:
                counts, orig, orig_short = example_counts(ex)
                for i, wordcount in enumerate(counts):
                    word, count = wordcount
                    textfile.append("    {:3}: {:20}  {}".format(
                        count, word, 
                        # " ".join(sorted(orig_short[word].keys(), key=lambda x: (x.lower(), x))),
                        " ".join(sorted(orig[word], key=lambda x: (x.lower(), x))),
                    ))
                textfile.append("")

                place = 0
                col = 0
                for i, wordcount in enumerate(counts):
                    word, count = wordcount
                    abbr = pick_repr(orig_short[word])

                    scale = (2 + math.sqrt(min(count, 15))) * 2.8
                    space = scale * 5.0

                    if space > c:
                        break

                    if place + space > c:
                        place = 0
                        col += 1

                    if col >= ncols:
                        break

                    bboxes = [ None ]

                    if tcol is None:
                        bboxes.append(dict(facecolor=cols[1], linewidth=0, boxstyle="round,pad=0.3"))
                        color = "#000000"
                    else:
                        color = tcol

                    for zorder,bbox in enumerate(bboxes):
                        ax.text(
                            len(texts) + (jj * ncols + col + 0.5) * colspace/ncols, y + c - place, latexify(abbr),
                            horizontalalignment="center", verticalalignment="top",
                            color=color, bbox=bbox, zorder=-zorder,
                            fontsize=scale,
                        )
                    place += space
                jj += 1

        y += c + pad

    basename = "blocks-" + key
    for flag in flags:
        basename += "-" + flag
    basename += filename
    figsave(fig, basename)

    if words:
        with open("output/{}.txt".format(basename), "w") as f:
            for l in textfile:
                f.write(l + "\n")

def draw_blocks():
    for flags in [
        ["sort"],
        ["sort", "words"]
    ]:
        draw_blocks_base(
            "per",
            [("other", [lllblack, lgray], gray), ("per", [llred, red], dred)],
            flags,
            words_only=[1],
        )
        draw_blocks_base(
            "language",
            [("Latin", [llblue, blue], dblue), ("English", [llorange, orange], dorange)],
            flags,
        )
        draw_blocks_base(
            "lex",
            [("lex", [llpurp, purp], dpurp), ("func", [llblack, gray], black)],
            flags,
        )
        draw_blocks_base(
            "recipe",
            [("other", [llgreen, green], dgreen), ("recipe", [llblack, gray], black)],
            flags,
        )
        lengths = ["-4", "5-6", "7-8", "9-10", "11-"]
        cases = [ [x, [bcolor_range[i], color_range[i]], tcolor_range[i] ] for i,x in enumerate(lengths) ]
        draw_blocks_base("characters", cases, flags)

        # draw_blocks_base(
        #     "lex",
        #     [("lex", [llblue, blue]), ("func", [llblack, black])],
        #     flags,
        #     "text",
        # )
        # draw_blocks_base(
        #     "length",
        #     [("short", [llblue, blue]), ("long", [llblack, black])],
        #     flags,
        # )

def main():
    draw_overview()
    draw_blocks()

main()
