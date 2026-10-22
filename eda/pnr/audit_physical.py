"""Independently audit exported Innovus physical evidence without changing it.

Inputs are listed in a JSON configuration (see audit_config.example.json).
The immediate post-IO snapshot proves preservation of the original core pins;
the final netlist may legitimately differ after CTS, buffering and hold repair.
This checks exported geometry/connectivity and hashes, not foundry signoff.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import sys


SIGNALS = {
    "clk_i": ("i_pad_clk", "input", "N"),
    "rst_ni": ("i_pad_rst_n", "input", "N"),
    "tck_i": ("i_pad_tck", "input", "S"),
    "tms_i": ("i_pad_tms", "input", "S"),
    "td_i": ("i_pad_tdi", "input", "S"),
    "td_o": ("i_pad_tdo", "output", "S"),
}
SUPPLIES = {"VDD": "POWER", "VSS": "GROUND", "VDDPST": "POWER", "VSSPST": "GROUND"}
ORIENT = {"R0": "N", "R180": "S", "R90": "W", "R270": "E", "MX": "FS", "MY": "FN"}
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_name(name):
    return name.strip().lstrip("\\").replace("\\[", "[").replace("\\]", "]")


def strip_comments(text):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


class Audit:
    def __init__(self, config, config_path):
        self.config = config
        self.base = config_path.resolve().parent
        self.files = {}
        self.checks = {}
        self.epsilon = float(config.get("geometry_tolerance_um", 0.0011))

    def path(self, value):
        p = Path(value)
        return p if p.is_absolute() else self.base / p

    def read(self, value):
        p = self.path(value)
        self.files[str(p.resolve())] = digest(p)
        return p.read_text(errors="replace")

    def check(self, name, function):
        try:
            details = function()
            self.checks[name] = {"status": "PASS", "details": details}
        except (AssertionError, ValueError, KeyError, IndexError, OSError, ImportError) as error:
            self.checks[name] = {"status": "FAIL", "error": str(error)}

    def missing(self, name, reason):
        self.checks[name] = {"status": "NOT_CHECKED", "reason": reason}


def parse_named_instances(body):
    instances = {}
    for match in re.finditer(r"(?m)^\s*([A-Za-z_$][\w$]*)\s+(\\[^\s]+|[A-Za-z_$][\w$]*)\s*\((.*?)\);", body, re.S):
        master, name, ports = match.groups()
        if master in {"input", "output", "inout", "wire", "assign"}:
            continue
        pairs = []
        for pin in re.finditer(r"\.([^\s(]+)\s*\(", ports):
            depth, index = 1, pin.end()
            while index < len(ports) and depth:
                depth += (ports[index] == "(") - (ports[index] == ")")
                index += 1
            assert depth == 0, (name, "Unbalanced connection expression")
            pairs.append((pin[1], ports[pin.end():index-1]))
        assert pairs or not ports.strip(), (name, "Unsupported positional instance")
        name = clean_name(name)
        assert name not in instances, f"Duplicate instance {name}"
        pins = {clean_name(p): n.strip() for p, n in pairs}
        assert len(pins) == len(pairs), f"Duplicate pin {name}"
        instances[name] = (master, pins)
    return instances


def alias_resolver(body):
    parent = {}

    def find(net):
        net = clean_name(net)
        if net in parent:
            parent[net] = find(parent[net])
        return parent.get(net, net)

    for a, b in re.findall(r"\bassign\s+([^=;]+)=\s*([^;]+);", body):
        a, b = a.strip(), b.strip()
        simple = r"(?:\\\S+|[A-Za-z_$][\w$]*(?:\[\d+\])?|1\s*'\s*[bBhHdD]\s*[01]|[01])"
        if re.fullmatch(simple, a) and re.fullmatch(simple, b):
            a, b = find(a), find(b)
            if a != b:
                parent[a] = b
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[a] = b
    find.union = union
    return find


class ParsedNetlist:
    """Module-local nets and tuple instance identities, never global net names."""
    def __init__(self, modules, top):
        self.modules, self.top = modules, top
        self.leaf_masters = set()
        self.cache = {}

    def __iter__(self):
        # Preserve the existing root-instance/find interface for PAD/DEF checks.
        yield self.modules[self.top][0]
        yield self.modules[self.top][1]

    def resolve_boundary_aliases(self):
        """Propagate proven child assign aliases back into the parent module.

        The exported CPU clock wrapper is a transparent assign module. Its
        input/output are the same wire; merely walking downward misses loads on
        the output's parent net. Constant-equal ports are deliberately not
        merged: equal values alone do not establish physical wire identity.
        """
        done, active = set(), set()
        def visit(name):
            if name in done:
                return
            assert name not in active, ("Recursive module hierarchy", name)
            active.add(name)
            instances, find, _, complex_edges = self.modules[name]
            for _, (master, pins) in instances.items():
                if master not in self.modules:
                    continue
                visit(master)
                child_find = self.modules[master][1]
                groups = defaultdict(list)
                for pin, expression in pins.items():
                    if re.fullmatch(r"(?:\\\S+|[A-Za-z_$][\w$]*(?:\[-?\d+\])?)", expression.strip()):
                        equivalent = child_find(pin)
                        if not re.fullmatch(r"(?:[01]|1\s*'\s*[bBhHdD]\s*[01])", equivalent):
                            groups[equivalent].append(expression)
                for nets in groups.values():
                    for net in nets[1:]:
                        find.union(nets[0], net)
            by_net = defaultdict(list)
            for instance, (_, pins) in instances.items():
                for pin, expression in pins.items():
                    if expression.strip() and re.fullmatch(r"(?:\\\S+|[A-Za-z_$][\w$]*(?:\[-?\d+\])?|1\s*'\s*[bBhHdD]\s*[01]|[01])", expression.strip()):
                        by_net[find(expression)].append((instance, pin))
            self.modules[name] = (instances, find, by_net, complex_edges)
            active.remove(name)
            done.add(name)
        for name in list(self.modules):
            visit(name)

    def leaf_pins(self, net, exclude=()):
        def visit(module, target, ancestors):
            assert module not in ancestors, ("Recursive module hierarchy", module)
            instances, find, by_net, complex_edges = self.modules[module]
            target = find(target)
            key = (module, target)
            if key in self.cache:
                return self.cache[key]
            for instance, pin, atoms in complex_edges:
                assert not any(find(a) == target or find(re.sub(r"\[-?\d+\]$", "", a)) == target for a in atoms), ("Cannot safely trace scalar signal through selected/vector/expression connection", module, target, instance, pin)
            result = set()
            for instance, pin in by_net.get(target, []):
                master = instances[instance][0]
                if master in self.modules and master not in self.leaf_masters:
                    for path, leaf_pin, leaf_master in visit(master, pin, ancestors+(module,)):
                        result.add(((instance,)+path, leaf_pin, leaf_master))
                else:
                    result.add(((instance,), pin, master))
            self.cache[key] = result
            return result
        return {endpoint for endpoint in visit(self.top, net, ()) if endpoint[0][0] not in exclude}


def parse_verilog(text, top):
    """Parse each module separately and trace scalar nets to physical leaf pins.

    A renamed or unused hierarchical formal is not a hardware endpoint. Exact
    leaf instance/pin/master identities must survive immediate PAD insertion.
    """
    text = strip_comments(text)
    modules = {}
    atom = r"(?:\\\S+|[A-Za-z_$][\w$]*(?:\[-?\d+\])?|1\s*'\s*[bBhHdD]\s*[01]|[01])"
    for match in re.finditer(r"\bmodule\s+(\\\S+|[A-Za-z_$][\w$]*)\s*\(.*?\)\s*;(.*?)\bendmodule", text, re.S):
        name, body = clean_name(match[1]), match[2]
        assert name not in modules, ("Duplicate module", name)
        instances, find = parse_named_instances(body), alias_resolver(body)
        by_net, complex_edges = defaultdict(list), []
        for instance, (_, pins) in instances.items():
            for pin, expression in pins.items():
                if not expression.strip():
                    continue
                if re.fullmatch(atom, expression.strip()):
                    by_net[find(expression)].append((instance, pin))
                    # Selected vectors must not silently evade scalar tracing.
                    if re.search(r"\[-?\d+\]$", expression.strip()) and not expression.strip().startswith("\\"):
                        complex_edges.append((instance, pin, [expression.strip()]))
                else:
                    atoms = re.findall(r"\\\S+|[A-Za-z_$][\w$]*(?:\[-?\d+\])?", expression)
                    complex_edges.append((instance, pin, atoms))
        modules[name] = (instances, find, by_net, complex_edges)
    assert top in modules and modules[top][0], f"Missing/empty top module {top}"
    parsed = ParsedNetlist(modules, top)
    parsed.resolve_boundary_aliases()
    return parsed


def constant_resolver(instances, find, tie_cells):
    values = {}
    for _, (master, pins) in instances.items():
        for pin, value in tie_cells.get(master, {}).items():
            if pin in pins:
                net = find(pins[pin])
                assert net not in values or values[net] == int(value), f"Conflicting tie drivers {net}"
                values[net] = int(value)

    def resolve(net):
        net = find(net)
        compact = re.sub(r"\s+", "", net).lower()
        literals = {"1'b0": 0, "1'h0": 0, "1'd0": 0, "0": 0,
                    "1'b1": 1, "1'h1": 1, "1'd1": 1, "1": 1}
        return literals.get(compact, values.get(net))
    return resolve


def audit_pad_connections(before, after, cfg):
    old, old_find = before
    new, new_find = after
    const = constant_resolver(new, new_find, cfg.get("tie_cells", {"TIEHBWP7T": {"Z": 1}, "TIELBWP7T": {"ZN": 0}}))
    result = {}
    for port, (default_pad, direction, side) in SIGNALS.items():
        pad = cfg.get("signal_pads", {}).get(port, default_pad)
        master, pins = new[pad]
        assert master == cfg.get("signal_pad_master", "PDDW0204CDG"), (pad, master)
        assert new_find(pins["PAD"]) == new_find(port), (port, "PAD disconnected")
        core_pin = "I" if direction == "output" else "C"
        core = new_find(pins[core_pin])
        assert core != new_find(port), (port, "PAD bypassed")
        expected = {"OEN": 0 if direction == "output" else 1, "IE": 0 if direction == "output" else 1, "PE": 0, "DS": 0}
        if direction == "input":
            expected["I"] = 0
        for pin, value in expected.items():
            assert const(pins[pin]) == value, (port, pin, pins.get(pin), "expected", value)
        before_pins = before.leaf_pins(port)
        after_pins = after.leaf_pins(core, exclude=(pad,))
        assert before_pins, (port, "no original core connections")
        assert before_pins == after_pins, {"port": port, "lost": sorted(before_pins - after_pins), "added": sorted(after_pins - before_pins)}
        result[port] = {"pad": pad, "direction": direction, "side": side, "core_net": core,
                        "preserved_core_pin_count": len(before_pins), "original_core_pins": sorted(before_pins),
                        "endpoint_scope": "Exact hierarchical physical leaf instance/pin/master identities; renamed or unused module formals are resolved, not waived"}
    return result


def audit_final_pads(parsed, cfg):
    instances, find = parsed
    const = constant_resolver(instances, find, cfg.get("tie_cells", {"TIEHBWP7T": {"Z": 1}, "TIELBWP7T": {"ZN": 0}}))
    result = {}
    for port, (default_pad, direction, _) in SIGNALS.items():
        pad = cfg.get("signal_pads", {}).get(port, default_pad)
        master, pins = instances[pad]
        assert master == cfg.get("signal_pad_master", "PDDW0204CDG"), (pad, master)
        assert find(pins["PAD"]) == find(port), (port, "PAD disconnected")
        core = find(pins["I" if direction == "output" else "C"])
        assert core != find(port), (port, "PAD bypassed")
        controls = {"OEN": int(direction == "input"), "IE": int(direction == "input"), "PE": 0, "DS": 0}
        if direction == "input":
            controls["I"] = 0
        assert all(const(pins[p]) == v for p, v in controls.items()), (port, "control/tie mismatch", pins)
        connected = sorted(parsed.leaf_pins(core, exclude=(pad,)))
        assert connected, (port, "no final core connection")
        exposed = sorted(parsed.leaf_pins(port, exclude=(pad,)))
        assert not exposed, (port, "core bypasses PAD", exposed[:20])
        result[port] = {"pad": pad, "core_net": core, "final_core_pin_count": len(connected), "controls": controls}
    assert sum(m == cfg.get("signal_pad_master", "PDDW0204CDG") for m, _ in instances.values()) == 6, "Unexpected signal PAD count"
    return result


def parse_lefs(texts):
    macros, sites = {}, {}
    for text in texts:
        for m in re.finditer(r"(?m)^\s*SITE\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$", text, re.S):
            size = re.search(r"\bSIZE\s+(" + NUMBER + r")\s+BY\s+(" + NUMBER + r")\s*;", m[2])
            if size:
                sites[m[1]] = tuple(map(float, size.groups()))
        for m in re.finditer(r"(?m)^\s*MACRO\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$", text, re.S):
            size = re.search(r"\bSIZE\s+(" + NUMBER + r")\s+BY\s+(" + NUMBER + r")\s*;", m[2])
            clas = re.search(r"\bCLASS\s+([^;]+);", m[2])
            pins = {}
            for p in re.finditer(r"(?m)^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$", m[2], re.S):
                use = re.search(r"\bUSE\s+(\S+)\s*;", p[2])
                pins[p[1]] = use[1] if use else None
            item = {"size": tuple(map(float, size.groups())) if size else None, "class": clas[1].strip() if clas else "", "pins": pins}
            if m[1] in macros:
                old = macros[m[1]]
                assert old["size"] is None or item["size"] is None or old["size"] == item["size"], (m[1], "LEF size mismatch")
                assert not old["class"] or not item["class"] or old["class"] == item["class"], (m[1], "LEF class mismatch")
                item["size"] = item["size"] or old["size"]
                item["class"] = item["class"] or old["class"]
                merged = dict(old["pins"])
                for pin, use in item["pins"].items():
                    assert pin not in merged or merged[pin] is None or use is None or use == merged[pin], (m[1], pin, "LEF pin USE mismatch")
                    merged[pin] = use or merged.get(pin)
                item["pins"] = merged
            macros[m[1]] = item
    assert macros and sites, "LEF macros and placement SITE definitions are required"
    for name, item in macros.items():
        assert item["size"] is not None, (name, "Missing base LEF SIZE")
        item["pins"] = {pin: use or "SIGNAL" for pin, use in item["pins"].items()}
    return macros, sites


def def_section(text, name):
    m = re.search(r"(?m)^" + name + r"\s+\d+\s*;(.*?)^END\s+" + name + r"\b", text, re.S)
    if not m:
        return []
    return re.findall(r"(?m)^-\s+(\S+)\s+(.*?);", m[1], re.S)


def parse_def(text):
    units = int(re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)\s*;", text)[1])
    die = re.search(r"DIEAREA\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*;", text)
    assert die, "A rectangular DIEAREA is required"
    components = {}
    for name, body in def_section(text, "COMPONENTS"):
        master = body.split()[0]
        pos = re.search(r"\+\s+(FIXED|PLACED|COVER)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", body)
        components[clean_name(name)] = {"master": master, "status": pos[1] if pos else "UNPLACED",
                                        "xy": (int(pos[2]) / units, int(pos[3]) / units) if pos else None,
                                        "orient": ORIENT.get(pos[4], pos[4]) if pos else None}
    rows = []
    for m in re.finditer(r"(?m)^ROW\s+(\S+)\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s+(\S+)\s+DO\s+(\d+)\s+BY\s+(\d+)\s+STEP\s+(-?\d+)\s+(-?\d+)\s*;", text):
        name, site, x, y, orient, nx, ny, dx, dy = m.groups()
        rows.append({"name": name, "site": site, "x": int(x)/units, "y": int(y)/units,
                     "orient": ORIENT.get(orient, orient), "nx": int(nx), "ny": int(ny), "dx": int(dx)/units, "dy": int(dy)/units})
    props = dict((p, float(v)) for p, v in re.findall(r"DESIGN\s+(FE_CORE_BOX_\w+)\s+REAL\s+(" + NUMBER + r")\s*;", text))
    core = tuple(props["FE_CORE_BOX_" + p] for p in ("LL_X", "LL_Y", "UR_X", "UR_Y")) if len(props) == 4 else None
    pins = dict((clean_name(n), b) for n, b in def_section(text, "PINS"))
    nets = {}
    for kind in ("NETS", "SPECIALNETS"):
        for name, body in def_section(text, kind):
            # Only the connection prefix can contain instance/pin pairs. Route
            # coordinate tuples must never be mistaken for electrical terminals.
            prefix = body.split("+", 1)[0]
            conns = {(clean_name(i), clean_name(p)) for i, p in re.findall(r"\(\s*(\S+)\s+(\S+)\s*\)", prefix)}
            name = clean_name(name)
            if name in nets:
                prior = nets[name]
                assert kind not in prior["sections"], (name, "Duplicate net entry within DEF section", kind)
                # Native IO supplies have ordinary SIGNAL-pin terminals in NETS
                # and a POWER/GROUND declaration without wires in SPECIALNETS.
                # Both records describe the same named electrical net.
                conns |= prior["connections"]
                sections = prior["sections"] + [kind]
                body = prior["body"] + "\n" + body
            else:
                sections = [kind]
            nets[name] = {"kind": "SPECIALNETS" if "SPECIALNETS" in sections else kind,
                          "sections": sections, "connections": conns, "body": body}
    assert components and rows, "No components or rows parsed"
    return {"units": units, "die": tuple(int(v)/units for v in die.groups()), "core": core,
            "components": components, "rows": rows, "pins": pins, "nets": nets}


def bbox(component, macros):
    w, h = macros[component["master"]]["size"]
    if component["orient"] in {"E", "W", "FE", "FW"}:
        w, h = h, w
    x, y = component["xy"]
    return (x, y, x+w, y+h)


def within(a, b, eps):
    return a[0] >= b[0]-eps and a[1] >= b[1]-eps and a[2] <= b[2]+eps and a[3] <= b[3]+eps


def intersect(a, b, eps):
    return min(a[2], b[2])-max(a[0], b[0]) > eps and min(a[3], b[3])-max(a[1], b[1]) > eps


def audit_floorplan(data, macros, sites, cfg, eps):
    core, die = data["core"], data["die"]
    assert core and within(core, die, eps), ("Missing/invalid core box", core, die)
    macro_name = cfg.get("sram_instance", "i_mainmem/i_sram/i_macro")
    macro_master = cfg.get("sram_master", "RA1SHD_2048x32M8")
    bond_master = cfg.get("bond_master", "PAD60LU_OBV")
    blocks = [(n, c) for n, c in data["components"].items() if macros[c["master"]]["class"].split()[0] in {"BLOCK", "RING"} and c["master"] != bond_master]
    assert len(blocks) == 1 and blocks[0][0] == macro_name and blocks[0][1]["master"] == macro_master, ("Wrong block instances", [(n, c["master"]) for n, c in blocks])
    macro = blocks[0][1]
    assert macro["status"] == "FIXED", "SRAM must be fixed"
    mb = bbox(macro, macros)
    halo = float(cfg.get("minimum_macro_halo_um", 26))
    hb = (mb[0]-halo, mb[1]-halo, mb[2]+halo, mb[3]+halo)
    assert within(hb, core, eps), ("Macro halo outside core", hb, core)
    row_map = defaultdict(list)
    row_area = 0
    for row in data["rows"]:
        sw, sh = sites[row["site"]]
        assert row["ny"] == 1 and abs(row["dx"]-sw) <= eps and row["dy"] == 0, ("Unsupported/invalid row", row)
        rb = (row["x"], row["y"], row["x"]+row["nx"]*sw, row["y"]+sh)
        assert within(rb, core, eps), ("Row outside core", row["name"], rb)
        row_map[round(row["y"], 5)].append((row, rb, sw, sh))
        row_area += (rb[2]-rb[0])*sh
    occupied = defaultdict(list)
    standard_count = 0
    standard_area = 0
    for name, c in data["components"].items():
        assert c["status"] != "UNPLACED", ("Unplaced instance", name)
        item = macros[c["master"]]
        if not item["class"].startswith("CORE"):
            continue
        standard_count += 1
        cb = bbox(c, macros)
        assert within(cb, core, eps), ("Core cell outside core", name, cb)
        assert not intersect(cb, hb, eps), ("Core cell intersects SRAM halo", name, cb)
        rows = row_map.get(round(cb[1], 5), [])
        legal = [(r, rb, sw, sh) for r, rb, sw, sh in rows if cb[0] >= rb[0]-eps and cb[2] <= rb[2]+eps and abs((cb[0]-rb[0])/sw-round((cb[0]-rb[0])/sw))*sw <= eps]
        assert legal, ("Cell not aligned to any row/site", name, cb)
        row, _, sw, sh = legal[0]
        allowed = {"N", "FN"} if row["orient"] == "N" else {"FS", "S"} if row["orient"] == "FS" else {row["orient"]}
        assert c["orient"] in allowed, ("Cell orientation conflicts with row", name, c["orient"], row["orient"])
        height_rows = round((cb[3]-cb[1])/sh)
        assert height_rows >= 1 and abs(height_rows*sh-(cb[3]-cb[1])) <= eps, ("Cell height not row multiple", name)
        for k in range(height_rows):
            occupied[round(cb[1]+k*sh, 5)].append((cb[0], cb[2], name))
        standard_area += (cb[2]-cb[0])*(cb[3]-cb[1])
    for y, intervals in occupied.items():
        previous_end, previous_name = -math.inf, None
        for start, end, name in sorted(intervals):
            assert start >= previous_end-eps, ("Standard cells overlap", y, previous_name, name, previous_end-start)
            previous_end, previous_name = max(previous_end, end), name
    available = (core[2]-core[0])*(core[3]-core[1])-(hb[2]-hb[0])*(hb[3]-hb[1])
    return {"die_um": die, "core_um": core, "sram_instance": macro_name, "sram_master": macro_master,
            "sram_bbox_um": mb, "minimum_halo_bbox_um": hb, "row_count": len(data["rows"]),
            "exported_row_area_um2": row_area, "core_cell_count_including_fillers": standard_count,
            "core_cell_area_including_fillers_um2": standard_area,
            "geometry_occupancy_including_fillers": standard_area/available,
            "scope": "Exported rectangular cell geometry/site/orientation/overlap; not routing or foundry DRC"}


def audit_io_geometry(data, macros, cfg, eps):
    die = data["die"]
    cx, cy = macros[cfg.get("corner_master", "PCORNER")]["size"]
    assert abs(cx-cy) <= eps, "This ring checker requires square corners"
    side_items = defaultdict(list)
    sides_by_instance = {}
    corners, bonds, real_pads = [], [], []
    for name, c in data["components"].items():
        master = c["master"]
        if master == cfg.get("corner_master", "PCORNER"):
            assert c["status"] == "FIXED", (name, "corner not fixed")
            corners.append((name, *c["xy"], c["orient"]))
            continue
        is_bond = master == cfg.get("bond_master", "PAD60LU_OBV")
        is_ring = master.startswith("PFILLER") or master in cfg.get("ring_pad_masters", ["PDDW0204CDG", "PVDD1CDG", "PVSS1CDG", "PVDD2CDG", "PVSS2CDG", "PVDD2POC"])
        if not is_bond and not is_ring:
            continue
        box = bbox(c, macros)
        assert within(box, die, eps), (name, "outside DIEAREA", box)
        touches = {"S": abs(box[1]-die[1]) <= eps, "N": abs(box[3]-die[3]) <= eps,
                   "W": abs(box[0]-die[0]) <= eps, "E": abs(box[2]-die[2]) <= eps}
        found = [s for s, yes in touches.items() if yes]
        assert len(found) == 1, (name, "not on exactly one die side", found, box)
        side = found[0]
        assert c["orient"] == {"S": "N", "N": "S", "W": "E", "E": "W"}[side], (name, side, c["orient"])
        assert c["status"] == "FIXED" or master.startswith("PFILLER"), (name, "IO not fixed")
        start, end = (box[0], box[2]) if side in {"N", "S"} else (box[1], box[3])
        sides_by_instance[name] = side
        if is_bond:
            bonds.append((name, side, start, end))
        else:
            side_items[side].append((start, end, name))
            if not master.startswith("PFILLER"):
                real_pads.append((name, side, start, end))
    expected = [(die[0], die[1], "N"), (die[2]-cx, die[1], "FN"), (die[0], die[3]-cy, "FS"), (die[2]-cx, die[3]-cy, "S")]
    assert len(corners) == 4, ("Corner count", len(corners))
    for x, y, orient in expected:
        assert sum(abs(px-x) <= eps and abs(py-y) <= eps and po == orient for _, px, py, po in corners) == 1, ("Corner mismatch", x, y, orient, corners)
    for side in ("N", "S", "W", "E"):
        start = (die[0] if side in {"N", "S"} else die[1])+cx
        stop = (die[2] if side in {"N", "S"} else die[3])-cx
        for a, b, name in sorted(side_items[side]):
            assert abs(a-start) <= eps, (side, name, "IO ring gap/overlap um", a-start)
            start = b
        assert abs(start-stop) <= eps, (side, "IO ring not closed", start, stop)
    assert len(bonds) == len(real_pads), ("Bond count differs from ordinary pads", len(bonds), len(real_pads))
    for name, side, a, b in real_pads:
        matches = [bn for bn, bs, ba, bb in bonds if bs == side and abs(ba-a) <= eps and abs(bb-b) <= eps]
        assert len(matches) == 1, (name, "missing/duplicate aligned bond", matches)
    for port, (pad, _, side) in SIGNALS.items():
        pad = cfg.get("signal_pads", {}).get(port, pad)
        assert sides_by_instance.get(pad) == side, (port, "unexpected side", sides_by_instance.get(pad))
    return {"actual_die_um": die, "corner_size_um": (cx, cy), "side_component_counts": {s: len(side_items[s]) for s in ("N", "S", "W", "E")},
            "ordinary_pad_counts_by_side": dict(Counter(s for _, s, _, _ in real_pads)),
            "ordinary_pad_count": len(real_pads), "bond_count": len(bonds), "corners": corners,
            "scope": "All native IO/filler side abutments and one aligned bond overlay per ordinary pad; no fixed die coordinate/count reuse"}


def audit_def_connections(data, final, macros, cfg, eps):
    instances, find = final
    # These IO supply endpoints are USE SIGNAL in the native LEF and are
    # explicitly attached by the production power stage, not global pgpins.
    native_supply_pins = {"PVDD1CDG": {"VDD"}, "PVSS1CDG": {"VSS"},
                          "PVDD2CDG": {"VDDPST"}, "PVDD2POC": {"VDDPST"}, "PVSS2CDG": {"VSSPST"}}
    assert set(data["pins"]) == set(SIGNALS) | set(SUPPLIES), ("Unexpected physical top pins", sorted(data["pins"]))
    physical_boxes = {}
    for pin, body in data["pins"].items():
        net = re.search(r"\+\s+NET\s+(\S+)", body)
        assert net and clean_name(net[1]) == pin, (pin, "wrong physical pin net")
        expected_use = SUPPLIES.get(pin, "SIGNAL")
        use = re.search(r"\+\s+USE\s+(\S+)", body)
        assert use and use[1] == expected_use, (pin, "wrong/missing USE")
        direction = re.search(r"\+\s+DIRECTION\s+(\S+)", body)
        expected_direction = "INOUT" if pin in SUPPLIES else SIGNALS[pin][1].upper()
        assert direction and direction[1] == expected_direction, (pin, "wrong/missing DIRECTION")
        anchors = re.findall(r"\+\s+(?:FIXED|PLACED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", body)
        assert len(anchors) == 1, (pin, "one physical pin placement anchor required")
        ax, ay, orientation = anchors[0]
        ax, ay = int(ax)/data["units"], int(ay)/data["units"]
        orientation = ORIENT.get(orientation, orientation)
        transforms = {"N": lambda x, y: (x, y), "S": lambda x, y: (-x, -y),
                      "E": lambda x, y: (y, -x), "W": lambda x, y: (-y, x),
                      "FN": lambda x, y: (-x, y), "FS": lambda x, y: (x, -y),
                      "FE": lambda x, y: (y, x), "FW": lambda x, y: (-y, -x)}
        rects = re.findall(r"\+\s+LAYER\s+(\S+)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", body)
        assert rects, (pin, "no physical pin metal rectangle")
        boxes = []
        for layer, x1, y1, x2, y2 in rects:
            transformed = [transforms[orientation](int(x)/data["units"], int(y)/data["units"]) for x, y in ((x1, y1), (x1, y2), (x2, y1), (x2, y2))]
            box = (ax+min(x for x, y in transformed), ay+min(y for x, y in transformed), ax+max(x for x, y in transformed), ay+max(y for x, y in transformed))
            assert within(box, data["die"], eps), (pin, "physical pin outside DIEAREA", box)
            if pin in SIGNALS:
                pad = cfg.get("signal_pads", {}).get(pin, SIGNALS[pin][0])
                candidates = [(pad, data["components"][pad])]
            else:
                candidates = [(n, c) for n, c in data["components"].items() if macros[c["master"]]["class"].startswith("PAD") and pin in macros[c["master"]]["pins"] and (macros[c["master"]]["pins"][pin] == expected_use or pin in native_supply_pins.get(c["master"], set()))]
            assert any(within(box, bbox(c, macros), eps) for n, c in candidates), (pin, "physical pin rectangle is not inside an appropriate IO pad", box)
            boxes.append({"layer": layer, "bbox_um": box})
        physical_boxes[pin] = boxes
    for port, (pad, direction, _) in SIGNALS.items():
        pad = cfg.get("signal_pads", {}).get(port, pad)
        assert data["components"][pad]["master"] == instances[pad][0], (pad, "DEF/netlist master mismatch")
        connections = data["nets"][port]["connections"]
        assert ("PIN", port) in connections and (pad, "PAD") in connections, (port, "DEF PAD/port disconnected", sorted(connections))
        assert connections == {("PIN", port), (pad, "PAD")}, (port, "physical net bypasses PAD", sorted(connections))
        core_pin = "I" if direction == "output" else "C"
        core = find(instances[pad][1][core_pin])
        net_matches = [(n, net) for n, net in data["nets"].items() if (pad, core_pin) in net["connections"]]
        assert len(net_matches) == 1, (port, "DEF core-side PAD connection missing/ambiguous", core)
        net_name, net = net_matches[0]
        assert find(net_name) == core and len(net["connections"]) >= 2, (port, "DEF/netlist core-side net differs", net_name, core)
    power_pin_count = Counter()
    native_pin_count = Counter()
    for name, component in data["components"].items():
        for pin, use in macros[component["master"]]["pins"].items():
            explicit_native = pin in native_supply_pins.get(component["master"], set())
            if (use not in {"POWER", "GROUND"} and not explicit_native) or pin not in SUPPLIES:
                continue
            net = data["nets"].get(pin)
            assert net and net["kind"] == "SPECIALNETS", (pin, "missing special net")
            assert (name, pin) in net["connections"] or ("*", pin) in net["connections"], (name, pin, "PG not bound in DEF")
            if explicit_native:
                assert name in instances and pin in instances[name][1] and find(instances[name][1][pin]) == find(pin), (name, pin, "Native IO supply mismatch between final netlist and DEF")
                native_pin_count[pin] += 1
            power_pin_count[pin] += 1
    for pin in SUPPLIES:
        assert power_pin_count[pin] > 0, (pin, "no macro PG pins checked")
    return {"top_pin_count": len(data["pins"]), "six_PAD_nets_have_no_bypass": True,
            "physical_pin_rectangles": physical_boxes, "PG_pin_binding_counts": dict(power_pin_count),
            "explicit_native_IO_supply_pin_counts": dict(native_pin_count),
            "scope": "DEF electrical binding; routed PG continuity is checked separately by native geometry and tool connectivity reports"}


def audit_native_gds(path, data, macros, cfg, eps):
    try:
        import gdstk
    except ImportError as error:
        raise ImportError("Native IO geometry requires gdstk in this Python environment") from error
    lib = gdstk.read_gds(path)
    assert abs(lib.unit-1e-6) < 1e-15, ("GDS coordinates are not micrometres", lib.unit)
    cells = {c.name: c for c in lib.cells}
    layer = int(cfg.get("native_io_m4_gds_layer", 31))
    datatype = int(cfg.get("native_io_m4_gds_datatype", 0))
    rail_samples = cfg.get("native_io_rail_samples_um", {"VSSPST": 20.95, "VDDPST": 63.92})
    masters = sorted({c["master"] for c in data["components"].values() if c["master"].startswith("PFILLER") or c["master"] in cfg.get("ring_pad_masters", ["PDDW0204CDG", "PVDD1CDG", "PVSS1CDG", "PVDD2CDG", "PVSS2CDG", "PVDD2POC"])})
    precision = max(lib.precision/lib.unit, 0.0001)
    for master in masters:
        polygons = cells[master].get_polygons(layer=layer, datatype=datatype)
        width = macros[master]["size"][0]
        for net, y in rail_samples.items():
            strip = gdstk.rectangle((0, y-.01), (width, y+.01))
            assert not gdstk.boolean([strip], polygons, "not", precision=precision), (master, net, "native rail does not span full width")
    corner_name = cfg.get("corner_master", "PCORNER")
    corner_size = macros[corner_name]["size"][0]
    merged = gdstk.boolean(cells[corner_name].get_polygons(layer=layer, datatype=datatype), [], "or", precision=precision)
    for net, y in rail_samples.items():
        assert any(all(gdstk.inside([(corner_size-.001, y), (y, corner_size-.001)], [polygon])) for polygon in merged), (corner_name, net, "native perpendicular rail edges disconnected")
    return {"native_masters_checked": masters + [corner_name], "GDS_unit_m": lib.unit,
            "GDS_precision_m": lib.precision, "rail_layer_datatype": [layer, datatype], "rail_samples_um": rail_samples,
            "scope": "Native rail metal plus complete DEF abutments imply geometric IO-ring continuity; not extraction, LVS, ESD or IR/EM signoff"}


def audit_reports(audit, data):
    cfg = audit.config
    output = {}
    for kind in ("placement", "special_connectivity", "signal_connectivity", "route_drc"):
        key = kind + "_report"
        assert cfg.get(key), f"Missing {key}"
        text = audit.read(cfg[key])
        if kind == "placement":
            unplaced = re.search(r"Number of Unplaced Instances\s*=\s*(\d+)", text)
            assert unplaced and int(unplaced[1]) == 0, "Placement report missing zero-unplaced evidence"
            # Tool checkPlace often reports the deliberate Bond/IO overlay. It
            # is not silently treated as a clean placement report; our geometry
            # checks independently exclude ordinary-IO overlap and prove bonds.
            lists = {}
            for name, contents in re.findall(r"set\s+(pchk\w+List)\s+\[list(.*?)\]", text, re.S):
                names = re.findall(r"\{([^}]+)\}", contents)
                if names:
                    lists[name] = names
            unexpected = {n: v for n, v in lists.items() if "IoOverlap" not in n}
            assert not unexpected, ("Placement violation lists", unexpected)
            allowed_overlap_masters = set(cfg.get("ring_pad_masters", ["PDDW0204CDG", "PVDD1CDG", "PVSS1CDG", "PVDD2CDG", "PVSS2CDG", "PVDD2POC"])) | {cfg.get("bond_master", "PAD60LU_OBV")}
            for names in lists.values():
                assert all(n in data["components"] and data["components"][n]["master"] in allowed_overlap_masters for n in names), ("Unexpected cells in IO-overlap list", names)
            output[kind] = {"unplaced_instances": 0, "tool_IO_overlap_lists": lists,
                            "note": "IO overlap entries require independently verified aligned Bond overlay and zero ordinary-IO overlap"}
        elif kind == "route_drc":
            assert re.search(r"No DRC violations were found", text, re.I), "No zero-DRC conclusion found"
            output[kind] = {"tool_route_DRC_violations": 0, "scope": "Innovus reported checks, not foundry signoff"}
        else:
            if "Found no problems or warnings." in text:
                output[kind] = {"reported_problems": 0}
                continue
            allowed = set(cfg.get("native_io_unrouted_net_allowlist", [])) if kind == "signal_connectivity" else set()
            no_route = re.findall(r"^Net\s+(\S+): no routing\s*$", text, re.M)
            counts = re.findall(r"(\d+)\s+Problem\(s\)\s*\(([^)]+)\):\s*([^\n]+)", text)
            assert allowed and set(no_route) == allowed and len(no_route) == len(allowed), (kind, "nonzero connectivity report", no_route)
            assert len(counts) == 1 and int(counts[0][0]) == len(allowed) and counts[0][1] == "IMPVFC-98" and "no global routing and no special routing" in counts[0][2], (kind, "unexpected problem summary", counts)
            output[kind] = {"reported_problems": len(allowed), "accepted_native_rail_unrouted_nets": sorted(allowed),
                            "scope": "Only these named native IO rails are geometrically proved by native_io_geometry; not a zero-connectivity report"}
    return output


def audit_stage_hashes(audit):
    entries = audit.config.get("stage_artifacts", [])
    assert entries, "Explicit frozen stage artifact SHA256 values are required"
    result = []
    for item in entries:
        path = audit.path(item["path"])
        expected = item["sha256"].lower()
        assert re.fullmatch(r"[a-f0-9]{64}", expected), (item.get("label"), "invalid expected SHA256")
        actual = digest(path)
        audit.files[str(path.resolve())] = actual
        assert actual == expected, (item.get("label"), "SHA256 mismatch", expected, actual)
        result.append({"label": item["label"], "path": str(path.resolve()), "sha256": actual})
    required = {str(audit.path(audit.config[k]).resolve()) for k in ("pre_io_netlist", "post_io_netlist", "final_netlist", "def")}
    assert required <= {x["path"] for x in result}, "Stage hashes must cover pre-IO, immediate post-IO, final netlist and final DEF"
    return {"artifacts": result, "note": "Hashes match frozen caller-provided identities; collection must bind exports to the same completed checkpoint"}


def run(config_path):
    cfg = json.loads(config_path.read_text())
    audit = Audit(cfg, config_path)
    audit.files[str(config_path.resolve())] = digest(config_path)
    audit.files[str(Path(__file__).resolve())] = digest(Path(__file__))
    top = cfg.get("top", "my_soc_top")
    try:
        old = parse_verilog(audit.read(cfg["pre_io_netlist"]), top)
        post = parse_verilog(audit.read(cfg["post_io_netlist"]), top)
        final = parse_verilog(audit.read(cfg["final_netlist"]), top)
        data = parse_def(audit.read(cfg["def"]))
        macros, sites = parse_lefs([audit.read(p) for p in cfg["lef_files"]])
        for parsed in (old, post, final):
            parsed.leaf_masters = set(macros)
        missing = sorted({c["master"] for c in data["components"].values()}-set(macros))
        assert not missing, ("Missing component LEF", missing[:50])
    except (AssertionError, ValueError, KeyError, IndexError, OSError) as error:
        audit.checks["input_parsing"] = {"status": "FAIL", "error": str(error)}
        return {"status": "FAIL", "checks": audit.checks, "sha256": audit.files}
    audit.check("post_IO_pin_preservation", lambda: audit_pad_connections(old, post, cfg))
    audit.check("final_PAD_connections_and_ties", lambda: audit_final_pads(final, cfg))
    audit.check("core_rows_macro_and_legal_placement", lambda: audit_floorplan(data, macros, sites, cfg, audit.epsilon))
    audit.check("IO_ring_and_bond_geometry", lambda: audit_io_geometry(data, macros, cfg, audit.epsilon))
    audit.check("DEF_signal_and_power_bindings", lambda: audit_def_connections(data, final, macros, cfg, audit.epsilon))
    if cfg.get("native_io_gds"):
        path = audit.path(cfg["native_io_gds"])
        if path.exists():
            audit.files[str(path.resolve())] = digest(path)
        audit.check("native_IO_power_rail_geometry", lambda: audit_native_gds(path, data, macros, cfg, audit.epsilon))
    else:
        audit.missing("native_IO_power_rail_geometry", "native_io_gds was not supplied")
    audit.check("tool_physical_reports", lambda: audit_reports(audit, data))
    audit.check("frozen_stage_artifact_hashes", lambda: audit_stage_hashes(audit))
    statuses = {c["status"] for c in audit.checks.values()}
    status = "FAIL" if "FAIL" in statuses else "INCOMPLETE" if "NOT_CHECKED" in statuses else "PASS"
    return {"schema": "chip-design-physical-audit-v1", "status": status,
            "scope": "Independent exported netlist/DEF/LEF/native-IO-GDS and report audit; not timing, formal equivalence, LVS, foundry DRC, ESD or IR/EM signoff",
            "checks": audit.checks, "sha256": audit.files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({"status": result["status"], "checks": {k: v["status"] for k, v in result["checks"].items()}, "output": str(args.output)}))
    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
