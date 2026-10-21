"""Render real DEF/LEF geometry, without pretending to be an Innovus GUI.

Python 3.8+ and Pillow are sufficient; no EDA process is launched. Example:
  python render_layout.py --def design.def --lef std.lef --lef io.lef \
      --lef bond.lef --lef memory.lef --stage postroute --out overview.png

All placed component outlines use their actual oriented LEF SIZE and DEF
location. A magnified placement panel shows real cells, not location markers.
Signal/special route centre-lines are deterministic reservoir samples of
actual DEF paths; vias, patch rectangles and pin metal are not drawn. This is
an overview, not a DRC/connectivity/LVS check or a transistor/GDS rendering.
Licensed LEFs should remain outside Git or in the ignored eda/work directory.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sys


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
ORIENT = {"R0": "N", "R180": "S", "R90": "W", "R270": "E",
          "MX": "FS", "MY": "FN", "MXR90": "FW", "MYR90": "FE"}
COLORS = {"logic": "#567b99", "physical": "#afc0cb", "macro": "#285f89",
          "signal_pad": "#e89d45", "power_pad": "#63a38c", "bond": "#f0d26e",
          "io_filler": "#a9cbb9", "corner": "#455667", "other": "#a586b3"}
LABELS = {"logic": "Standard logic cells", "physical": "Core fillers / taps",
          "macro": "SRAM / block macros", "signal_pad": "Signal IO pads",
          "power_pad": "Supply IO pads", "bond": "Bond-pad cells",
          "io_filler": "IO fillers", "corner": "IO corners / endcaps",
          "other": "Other placed cells"}
METAL_COLORS = ["#c96b48", "#4a8fc4", "#a368b3", "#55a984", "#c6a440", "#bb6689"]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def open_text(path):
    if str(path).lower().endswith(".gz"):
        return gzip.open(str(path), "rt", encoding="utf-8", errors="replace")
    return Path(path).open("r", encoding="utf-8", errors="replace")


def read_lefs(paths):
    macros, sites, layers, vias = {}, {}, {}, {}
    for path in paths:
        with open_text(path) as stream:
            text = re.sub(r"(?m)^\s*#.*$", "", stream.read())
        for kind, output in (("SITE", sites), ("MACRO", macros)):
            pattern = r"(?m)^\s*" + kind + r"\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$"
            for m in re.finditer(pattern, text, re.S):
                size = re.search(r"\bSIZE\s+(" + NUMBER + r")\s+BY\s+(" + NUMBER + r")\s*;", m[2])
                if not size:
                    continue
                item = {"size": tuple(map(float, size.groups()))}
                if min(item["size"]) <= 0:
                    raise ValueError("Nonpositive LEF size: " + m[1])
                clas = re.search(r"\bCLASS\s+([^;]+);", m[2])
                item["class"] = clas[1].strip() if clas else ""
                if m[1] in output and output[m[1]] != item:
                    raise ValueError("Conflicting LEF SIZE/CLASS: " + m[1])
                output[m[1]] = item
        for m in re.finditer(r"(?m)^LAYER\s+(\S+)\s*\n(.*?)^END\s+\1\s*$", text, re.S):
            if re.search(r"\bTYPE\s+ROUTING\s*;", m[2]):
                width = re.search(r"\bWIDTH\s+(" + NUMBER + r")\s*;", m[2])
                layers[m[1]] = float(width[1]) if width else None
        for m in re.finditer(r"(?m)^VIA\s+(\S+)[^\n]*\n(.*?)^END\s+\1\s*$", text, re.S):
            names = re.findall(r"\bLAYER\s+(\S+)\s*;", m[2])
            if len(names) >= 2:
                vias[m[1]] = (names[0], names[-1])
    if not macros:
        raise ValueError("No sized LEF MACRO definitions supplied")
    return macros, sites, layers, vias


class Sample:
    """Bounded, reproducible sampling of actual segments without decimation bias."""
    def __init__(self, capacity, seed):
        self.capacity, self.random = capacity, random.Random(seed)
        self.total, self.items, self.layers = 0, [], Counter()

    def add(self, item):
        self.total += 1
        self.layers[item[0]] += 1
        if len(self.items) < self.capacity:
            self.items.append(item)
        elif self.capacity:
            i = self.random.randrange(self.total)
            if i < self.capacity:
                self.items[i] = item


def route_paths(body, units, sample, widths, vias, stats):
    # A path starts with ROUTED/FIXED/COVER or NEW. Connectivity tuples before
    # that point are deliberately excluded. A + starts the next DEF property.
    starts = list(re.finditer(r"(?:\+\s*(?:ROUTED|FIXED|COVER)|\bNEW)\s+(\S+)\s*", body))
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        tail = body[start.end():end]
        # Special-net SHAPE/STYLE properties are part of the wire, so remove
        # those prefixes; other properties terminate routing data.
        tail = re.sub(r"\+\s*(?:SHAPE|STYLE)\s+\S+", "", tail)
        tail = tail.split("+", 1)[0]
        tokens = re.findall(r"\([^)]*\)|[^\s()]+", tail)
        layer = start[1]
        width = widths.get(layer)
        if tokens and re.fullmatch(NUMBER, tokens[0]):
            width = float(tokens.pop(0)) / units
        previous, skip_rect = None, False
        for token in tokens:
            if token == "RECT":
                skip_rect = True
                stats["patch_rectangles_omitted"] += 1
                continue
            if token.startswith("("):
                if skip_rect:
                    skip_rect = False
                    continue
                values = token[1:-1].split()
                if len(values) not in (2, 3):
                    raise ValueError("Unsupported DEF route coordinate: " + token)
                if any(v == "*" for v in values[:2]) and previous is None:
                    raise ValueError("DEF route starts with unresolved * coordinate")
                xy = tuple(previous[k] if value == "*" else float(value) / units
                           for k, value in enumerate(values[:2]))
                if previous is not None and previous != xy:
                    sample.add((layer, previous[0], previous[1], xy[0], xy[1], width))
                previous = xy
            elif token in vias:
                stats["via_occurrences_omitted"] += 1
                a, b = vias[token]
                if layer == a:
                    layer = b
                elif layer == b:
                    layer = a
                else:
                    raise ValueError("DEF via does not touch active route layer: " + token)


def parse_def(path, sites, widths, lef_vias, route_limit, special_limit):
    data = {"components": [], "rows": [], "core_properties": {}, "declared_counts": {},
            "route_details": Counter(), "net_counts": Counter(), "embedded_stage": None}
    samples = {"NETS": Sample(route_limit, 20261021), "SPECIALNETS": Sample(special_limit, 20261022)}
    vias = dict(lef_vias)
    section, record, outside = None, [], []

    def consume(kind, body):
        fields = body.split(None, 2)
        if kind == "COMPONENTS":
            if len(fields) < 3:
                raise ValueError("Malformed DEF COMPONENT record")
            name, master = fields[0], fields[1]
            pos = re.search(r"\+\s+(FIXED|PLACED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", fields[2])
            item = {"name": name, "master": master, "status": "UNPLACED"}
            if pos:
                orient = ORIENT.get(pos[4], pos[4])
                if orient not in {"N", "S", "E", "W", "FN", "FS", "FE", "FW"}:
                    raise ValueError("Unknown DEF orientation: " + orient)
                item.update(status=pos[1], x=int(pos[2])/data["units"],
                            y=int(pos[3])/data["units"], orient=orient)
            data["components"].append(item)
        elif kind == "VIAS":
            names = re.search(r"\+\s+LAYERS\s+(\S+)\s+\S+\s+(\S+)", body)
            if names:
                vias[fields[0]] = names.groups()
            else:
                names = re.findall(r"\+\s+RECT\s+(\S+)", body)
                if len(names) >= 2:
                    vias[fields[0]] = (names[0], names[-1])
        elif kind in samples:
            data["net_counts"][kind] += 1
            route_paths(body, data["units"], samples[kind], widths, vias, data["route_details"])

    with open_text(path) as stream:
        for line in stream:
            line = re.sub(r"#.*$", "", line).strip()
            if not line:
                continue
            header = re.match(r"(COMPONENTS|NETS|SPECIALNETS|VIAS|PINS|BLOCKAGES|REGIONS|GROUPS|FILLS)\s+(\d+)\s*;", line)
            if header:
                section = header[1]
                data["declared_counts"][section] = int(header[2])
                outside = []
                continue
            if section:
                if re.match(r"END\s+" + section + r"\b", line):
                    if record:
                        raise ValueError("Unterminated DEF record in " + section)
                    section = None
                    continue
                if section not in {"COMPONENTS", "VIAS", "NETS", "SPECIALNETS"}:
                    continue
                if line.startswith("-") and not record:
                    line = line[1:].lstrip()
                record.append(line)
                if ";" in line:
                    consume(section, " ".join(record).rsplit(";", 1)[0])
                    record = []
                continue
            m = re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", line)
            if m:
                data["units"] = int(m[1])
            m = re.match(r"DESIGN\s+(\S+)\s*;", line)
            if m:
                data["design"] = m[1]
            m = re.search(r"(?:DESIGN\s+|\+\s*PROPERTY\s+)(FE_CORE_BOX_\w+)\s+(?:REAL\s+)?(" + NUMBER + r")", line)
            if m:
                data["core_properties"][m[1]] = float(m[2])
            m = re.search(r"flow_implementation_stage\s+STRING\s+\"([^\"]+)\"", line)
            if m:
                data["embedded_stage"] = m[1]
            if not outside and not re.match(r"(?:DIEAREA|ROW)\b", line):
                continue
            outside.append(line)
            if ";" not in line:
                continue
            statement, outside = " ".join(outside), []
            if statement.startswith("DIEAREA"):
                points = re.findall(r"\(\s*(-?\d+)\s+(-?\d+)\s*\)", statement)
                data["die_points_um"] = [(int(x)/data["units"], int(y)/data["units"]) for x, y in points]
            elif statement.startswith("ROW "):
                m = re.search(r"ROW\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\S+)\s+DO\s+(\d+)\s+BY\s+(\d+)\s+STEP\s+(-?\d+)\s+(-?\d+)", statement)
                if not m:
                    raise ValueError("Unsupported DEF ROW: " + statement[:160])
                name, site, x, y, orient, nx, ny, dx, dy = m.groups()
                if site not in sites:
                    raise ValueError("Missing placement SITE LEF: " + site)
                w, h = sites[site]["size"]
                if ORIENT.get(orient, orient) in {"E", "W", "FE", "FW"}:
                    w, h = h, w
                x, y, dx, dy = (int(v)/data["units"] for v in (x, y, dx, dy))
                end_x, end_y = x+(int(nx)-1)*dx, y+(int(ny)-1)*dy
                data["rows"].append((min(x, end_x), min(y, end_y), max(x, end_x)+w, max(y, end_y)+h))
    if section or record:
        raise ValueError("Truncated DEF section")
    if not data.get("units") or not data.get("die_points_um"):
        raise ValueError("DEF must declare UNITS and DIEAREA")
    points = data["die_points_um"]
    if len(points) == 2:
        (x0, y0), (x1, y1) = points
        data["die_points_um"] = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    elif len(points) < 4:
        raise ValueError("Unsupported DIEAREA polygon")
    if len(data["components"]) != data["declared_counts"].get("COMPONENTS"):
        raise ValueError("DEF COMPONENTS count mismatch")
    for kind in samples:
        if data["net_counts"][kind] != data["declared_counts"].get(kind, 0):
            raise ValueError("DEF " + kind + " count mismatch")
    props = data["core_properties"]
    if all("FE_CORE_BOX_"+key in props for key in ("LL_X", "LL_Y", "UR_X", "UR_Y")):
        data["core_um"] = tuple(props["FE_CORE_BOX_"+key] for key in ("LL_X", "LL_Y", "UR_X", "UR_Y"))
        data["core_source"] = "DEF FE_CORE_BOX properties"
    elif data["rows"]:
        rows = data["rows"]
        data["core_um"] = (min(r[0] for r in rows), min(r[1] for r in rows), max(r[2] for r in rows), max(r[3] for r in rows))
        data["core_source"] = "Actual ROW envelope (core boundary not exported)"
    else:
        data["core_um"], data["core_source"] = None, "Not exported; no invented core boundary"
    return data, samples


def category(component, macro):
    name, master, clas = component["name"].lower(), component["master"].upper(), macro["class"].upper()
    if "bond" in name or re.match(r"PAD\d", master):
        return "bond"
    if clas.startswith("PAD"):
        if re.match(r"PV(?:DD|SS)", master) or " POWER" in clas:
            return "power_pad"
        if "SPACER" in clas or master.startswith("PFILLER"):
            return "io_filler"
        return "signal_pad"
    if clas.startswith("ENDCAP") or master.startswith("PCORNER"):
        return "corner"
    if clas.startswith("CORE"):
        return "physical" if any(tag in clas for tag in ("SPACER", "WELLTAP", "ANTENNACELL")) or master.startswith(("FILL", "TAP", "DCAP")) else "logic"
    if clas.startswith(("BLOCK", "RING")):
        return "macro"
    return "other"


def prepare_geometry(data, macros):
    missing = sorted({c["master"] for c in data["components"]} - set(macros))
    if missing:
        raise ValueError("Missing LEF MACRO sizes (no substitute markers allowed): " + ", ".join(missing[:30]))
    counts = Counter()
    for c in data["components"]:
        if c["status"] == "UNPLACED":
            counts["unplaced"] += 1
            continue
        item = macros[c["master"]]
        w, h = item["size"]
        if c["orient"] in {"E", "W", "FE", "FW"}:
            w, h = h, w
        c["bbox_um"] = (c["x"], c["y"], c["x"]+w, c["y"]+h)
        c["category"] = category(c, item)
        counts[c["category"]] += 1
    return counts


def render(args, data, samples, counts, provenance):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise RuntimeError("Pillow is required; use an existing course/bundled Python with Pillow") from error
    width, height, aa = 2200, 1840, args.supersample
    image = Image.new("RGB", (width*aa, height*aa), "#f7f9fc")
    draw = ImageDraw.Draw(image)
    font_candidates = [args.font] if args.font else []
    font_candidates += ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"]
    def font(size):
        for path in font_candidates:
            if path:
                try:
                    return ImageFont.truetype(str(path), round(size*aa))
                except OSError:
                    pass
        return ImageFont.load_default()
    def text(x, y, value, size=22, color="#233649"):
        draw.text((round(x*aa), round(y*aa)), str(value), fill=color, font=font(size))
    def line(points, color, thickness=1):
        draw.line([(round(x*aa), round(y*aa)) for x, y in points], fill=color, width=max(1, round(thickness*aa)))
    def rect(box, fill=None, outline=None, thickness=1):
        draw.rectangle(tuple(round(v*aa) for v in box), fill=fill, outline=outline, width=max(1, round(thickness*aa)))

    die = data["die_points_um"]
    bounds = (min(x for x, y in die), min(y for x, y in die), max(x for x, y in die), max(y for x, y in die))
    dx, dy = bounds[2]-bounds[0], bounds[3]-bounds[1]
    if min(dx, dy) <= 0:
        raise ValueError("Degenerate DIEAREA")
    viewport = (105, 200, 1540, 1635)
    scale = min((viewport[2]-viewport[0])/dx, (viewport[3]-viewport[1])/dy)
    ox = (viewport[0]+viewport[2]-dx*scale)/2
    oy = (viewport[1]+viewport[3]+dy*scale)/2
    def point(x, y):
        return ox+(x-bounds[0])*scale, oy-(y-bounds[1])*scale
    def box(b):
        x0, y1 = point(b[0], b[1]); x1, y0 = point(b[2], b[3])
        return (x0, y0, x1, y1)

    text(78, 45, data.get("design", "Design") + "  |  " + args.stage, 39)
    text(80, 101, "Actual DEF / LEF geometry rendering - not an EDA GUI screenshot", 25)
    unplaced = counts.get("unplaced", 0)
    text(80, 143, "Placed components: {:,}   |   Unplaced: {:,}   |   Die: {:.3f} x {:.3f} um".format(len(data["components"])-unplaced, unplaced, dx, dy), 22,
         "#a04732" if unplaced else "#53687b")
    draw.polygon([(round(x*aa), round(y*aa)) for x, y in (point(x, y) for x, y in die)], fill="#eef2f6")
    if data["core_um"]:
        rect(box(data["core_um"]), fill="#e4ebf1")
    for rb in data["rows"]:
        b = box(rb)
        line([(b[0], b[3]), (b[2], b[3])], "#dce5ec", .35)
    # Draw every actual placed component. Fillers first, real logic next, and
    # larger periphery/macros last. No synthetic density tiles are substituted.
    ordered = sorted((c for c in data["components"] if "bbox_um" in c), key=lambda c: {"physical": 0, "logic": 1, "io_filler": 2, "other": 3, "macro": 4, "signal_pad": 5, "power_pad": 5, "corner": 5, "bond": 6}[c["category"]])
    for c in ordered:
        cat = c["category"]
        rect(box(c["bbox_um"]), fill=COLORS[cat], outline="#f1f4f8" if cat not in {"logic", "physical", "io_filler"} else None, thickness=.6)

    # Alpha-blended centre-lines; width is a readable visualization stroke,
    # not the fabricated wire width. Original widths remain in parsed samples.
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    route_draw = ImageDraw.Draw(overlay)
    layer_names = sorted({layer for s in samples.values() for layer in s.layers}, key=lambda name: (int(re.search(r"\d+", name)[0]) if re.search(r"\d+", name) else 999, name))
    layer_palette = {layer: METAL_COLORS[i % len(METAL_COLORS)] for i, layer in enumerate(layer_names)}
    def rgb(color, alpha):
        return tuple(int(color[k:k+2], 16) for k in (1, 3, 5)) + (alpha,)
    if args.routes != "none":
        kinds = ["SPECIALNETS", "NETS"] if args.routes == "all" else ["NETS"]
        for kind in kinds:
            for layer, x0, y0, x1, y1, wire_width in samples[kind].items:
                p0, p1 = point(x0, y0), point(x1, y1)
                route_draw.line([tuple(round(v*aa) for v in p0), tuple(round(v*aa) for v in p1)], fill=rgb(layer_palette[layer], 90 if kind == "SPECIALNETS" else 120), width=max(1, round((.85 if kind == "SPECIALNETS" else .5)*aa)))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)
    polygon = [point(x, y) for x, y in die]
    line(polygon+[polygon[0]], "#233649", 2.5)
    if data["core_um"]:
        rect(box(data["core_um"]), outline="#5a6c7c", thickness=1.4)
    for c in ordered:
        if c["category"] == "macro":
            b = box(c["bbox_um"])
            label = c["master"]
            size = 19 if (b[2]-b[0]) > 200 else 13
            text(b[0]+10, (b[1]+b[3])/2-22, label, size, "#ffffff")
            text(b[0]+10, (b[1]+b[3])/2+8, "{:.3f} x {:.3f} um".format(c["bbox_um"][2]-c["bbox_um"][0], c["bbox_um"][3]-c["bbox_um"][1]), 15, "#ffffff")
    for i in range(6):
        x = bounds[0]+i*dx/5; px, py = point(x, bounds[1])
        line([(px, py), (px, py+8)], "#5d7182")
        text(px-26, py+14, "{:.0f}".format(x), 17)
        y = bounds[1]+i*dy/5; px, py = point(bounds[0], y)
        line([(px-8, py), (px, py)], "#5d7182")
        text(px-74, py-9, "{:.0f}".format(y), 17)
    text((viewport[0]+viewport[2])/2-45, viewport[3]+54, "x (um)", 20)
    text(28, 177, "y (um)", 19)

    sx, sy = 1615, 210
    text(sx, sy, "Placed geometry", 28); sy += 53
    for key in LABELS:
        if counts[key]:
            rect((sx, sy+4, sx+24, sy+24), fill=COLORS[key])
            text(sx+39, sy, LABELS[key], 21)
            text(sx+39, sy+26, "{:,} instances".format(counts[key]), 18, "#667d8e")
            sy += 64
    text(sx, sy+8, "Core / rows", 25); sy += 49
    text(sx, sy, "{:,} exported placement rows".format(len(data["rows"])), 20); sy += 30
    if data["core_um"]:
        c = data["core_um"]
        text(sx, sy, "Core {:.3f} x {:.3f} um".format(c[2]-c[0], c[3]-c[1]), 20); sy += 30
    text(sx, sy, "DEF core box" if data["core_source"].startswith("DEF") else "ROW envelope / no core box", 18, "#667d8e"); sy += 48
    text(sx, sy, "Actual route centre-lines", 25); sy += 40
    for kind, label in (("NETS", "Signal"), ("SPECIALNETS", "Special / supply")):
        s = samples[kind]
        shown = len(s.items) if args.routes == "all" or args.routes == "signal" and kind == "NETS" else 0
        text(sx, sy, "{}: {:,} / {:,}".format(label, shown, s.total), 20); sy += 29
    text(sx, sy, "Drawn / parsed path segments", 18, "#667d8e"); sy += 27
    text(sx, sy, "Vias, patches and pin metal omitted", 17, "#667d8e"); sy += 27
    text(sx, sy, "Readable strokes; not physical wire widths", 17, "#667d8e"); sy += 42
    for i, layer in enumerate(layer_names[:12]):
        col = i % 3; row = i // 3
        xx, yy = sx+col*165, sy+row*29
        line([(xx, yy+13), (xx+24, yy+13)], layer_palette[layer], 2)
        text(xx+32, yy, layer, 17)
    sy += math.ceil(min(len(layer_names), 12)/3)*29+25

    # Select the densest spatial bin of actual logic cells for an honest zoom.
    logic = [c for c in ordered if c["category"] == "logic"]
    zoom_bounds = None
    if logic and sy < 1410:
        bins = Counter()
        for c in logic:
            b = c["bbox_um"]; x, y = (b[0]+b[2])/2, (b[1]+b[3])/2
            bins[(math.floor((x-bounds[0])/dx*18), math.floor((y-bounds[1])/dy*18))] += 1
        ix, iy = min(bins, key=lambda key: (-bins[key], key))
        zoom_bounds = (bounds[0]+ix*dx/18, bounds[1]+iy*dy/18,
                       bounds[0]+(ix+1)*dx/18, bounds[1]+(iy+1)*dy/18)
        zb = box(zoom_bounds)
        rect(zb, outline="#f7e36d", thickness=2)
        text(sx, sy, "Real cell placement: magnified", 23); sy += 39
        zw, zh = min(470, 1615-sy), min(470, 1615-sy)
        if zw >= 120:
            qscale = min(zw/(zoom_bounds[2]-zoom_bounds[0]), zh/(zoom_bounds[3]-zoom_bounds[1]))
            panel = Image.new("RGB", (round(zw*aa), round(zh*aa)), "#e4ebf1")
            pd = ImageDraw.Draw(panel)
            for c in ordered:
                b = c["bbox_um"]
                if b[2] <= zoom_bounds[0] or b[0] >= zoom_bounds[2] or b[3] <= zoom_bounds[1] or b[1] >= zoom_bounds[3]:
                    continue
                pb = (round((b[0]-zoom_bounds[0])*qscale*aa), round((zoom_bounds[3]-b[3])*qscale*aa),
                      round((b[2]-zoom_bounds[0])*qscale*aa), round((zoom_bounds[3]-b[1])*qscale*aa))
                pd.rectangle(pb, fill=COLORS[c["category"]], outline="#eff5f9", width=max(1, round(.6*aa)))
            image.paste(panel, (round(sx*aa), round(sy*aa)))
            rect((sx, sy, sx+zw, sy+zh), outline="#657a8c")
            sy += zh+12
            text(sx, sy, "Yellow box in overview; actual LEF outlines", 16, "#667d8e")
    text(80, 1720, "DEF: " + Path(args.def_path).name, 20)
    text(80, 1753, "SHA-256: " + provenance["def"]["sha256"], 21)
    text(80, 1792, "Geometric overview only. No GUI capture, internal transistor shapes or signoff claim.  |  " + provenance["created_utc"], 18, "#596e80")
    if aa > 1:
        resampling = getattr(Image, "Resampling", Image)
        image = image.resize((width, height), resampling.LANCZOS)
    image.save(str(args.out), format="PNG")
    return {"image_size_px": [width, height], "die_bbox_um": bounds, "placement_zoom_bbox_um": zoom_bounds,
            "category_classification": "LEF CLASS; IO supply/filler/bond names refine the displayed categories",
            "outline_geometry": "Actual DEF lower-left placement and oriented LEF SIZE; no substitute location markers"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--def", dest="def_path", type=Path, required=True)
    parser.add_argument("--lef", type=Path, action="append", required=True, help="Repeat for technology/cell/IO/bond/SRAM LEFs")
    parser.add_argument("--out", type=Path, required=True, help="Output PNG; provenance is written alongside as .json")
    parser.add_argument("--stage", required=True, help="Honest exported stage label, e.g. floorplan, placement, CTS, postroute")
    parser.add_argument("--routes", choices=("none", "signal", "all"), default="all")
    parser.add_argument("--max-route-segments", type=int, default=24000)
    parser.add_argument("--max-special-segments", type=int, default=4000)
    parser.add_argument("--supersample", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--font", type=Path, help="Optional existing TrueType font")
    args = parser.parse_args(argv)
    if min(args.max_route_segments, args.max_special_segments) < 0:
        parser.error("Segment budgets must be nonnegative")
    if args.out.suffix.lower() != ".png":
        parser.error("--out must end in .png")
    sources = [args.def_path] + args.lef
    if args.out.resolve() in {p.resolve() for p in sources}:
        parser.error("Output must not overwrite a source")
    provenance = {"created_utc": datetime.now(timezone.utc).isoformat(), "stage_label": args.stage,
                  "kind": "Actual DEF/LEF geometry rendering; not an EDA GUI screenshot",
                  "def": {"path": str(args.def_path.resolve()), "sha256": sha256(args.def_path)},
                  "lefs": [{"path": str(p.resolve()), "sha256": sha256(p)} for p in args.lef]}
    macros, sites, widths, vias = read_lefs(args.lef)
    data, samples = parse_def(args.def_path, sites, widths, vias, args.max_route_segments, args.max_special_segments)
    counts = prepare_geometry(data, macros)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    details = render(args, data, samples, counts, provenance)
    # Catch concurrent changes instead of publishing a misleading source hash.
    if sha256(args.def_path) != provenance["def"]["sha256"] or any(sha256(p) != item["sha256"] for p, item in zip(args.lef, provenance["lefs"])):
        raise RuntimeError("A source changed while rendering; image is not accepted")
    provenance.update(details)
    provenance.update(design=data.get("design"), embedded_def_stage=data["embedded_stage"],
                      core_um=data["core_um"], core_source=data["core_source"],
                      exported_row_count=len(data["rows"]), component_counts=dict(counts),
                      total_components=len(data["components"]), route_mode=args.routes,
                      route_sampling="Deterministic reservoir sampling; seeds 20261021 and 20261022",
                      route_omissions=dict(data["route_details"]),
                      route_segments={kind: {"parsed": s.total, "sampled": len(s.items),
                                             "drawn": len(s.items) if args.routes == "all" or args.routes == "signal" and kind == "NETS" else 0,
                                             "parsed_by_layer": dict(s.layers)} for kind, s in samples.items()},
                      image={"path": str(args.out.resolve()), "sha256": sha256(args.out)},
                      scope="Component outlines / path centre-lines only; not full mask geometry or DRC/LVS/signoff")
    args.out.with_suffix(".json").write_text(json.dumps(provenance, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": "RENDERED", "image": str(args.out), "provenance": str(args.out.with_suffix(".json")),
                      "components": len(data["components"]), "unplaced": counts.get("unplaced", 0),
                      "def_sha256": provenance["def"]["sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print("RENDER ERROR: " + str(error), file=sys.stderr)
        sys.exit(1)
