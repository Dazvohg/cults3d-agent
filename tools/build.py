"""Render the STL variants and preview images for one queue item.

Usage: python tools/build.py queue/001-xxx.yaml [--out build]
Needs OpenSCAD (and xvfb-run on headless Linux for PNG previews).
"""
import argparse
import json
import os
import zipfile
import pathlib
import shutil
import subprocess
import sys

import trimesh
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import slicer  # noqa: E402
import medidas  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]

# (label, camera) - camera = rotx,roty,rotz for --camera with viewall
VIEWS = [
    ("iso", "0,0,0,60,0,30,0"),
    ("front", "0,0,0,80,0,0,0"),
    ("side", "0,0,0,65,0,120,0"),
]
BED_MM = 220  # max footprint we promise in listings


def scad_defs(params: dict) -> list:
    args = []
    for k, v in params.items():
        args += ["-D", f"{k}={json.dumps(v)}"]
    return args


def run(cmd):
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{res.stderr}")
    return res


def fits_bed(mesh, bed, height_max=250):
    """True if the part fits on a bed x bed plate in SOME rotation around Z (checked every 1 deg)."""
    import numpy as np
    pts = mesh.convex_hull.vertices[:, :2]
    if mesh.extents[2] > height_max:
        return False
    for deg in range(0, 90):
        a = np.radians(deg)
        r = pts @ np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        w, d = r.max(axis=0) - r.min(axis=0)
        if w <= bed and d <= bed:
            return True
    return False


def fmt_time(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def spec_card(item, report, path):
    """Image with the REAL measurements of every file (no invented claims)."""
    from PIL import Image, ImageDraw, ImageFont

    def font(size, bold=False):
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        for base in ("/usr/share/fonts/truetype/dejavu/", ""):
            try:
                return ImageFont.truetype(base + name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    rows = len(report)
    img = Image.new("RGB", (1600, 1200), "#f7f7f5")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1600, 150], fill="#1f3b57")
    d.text((70, 45), "Included files & print specs", font=font(52, True), fill="white")
    y = 200
    d.text((70, y), "File", font=font(30, True), fill="#1f3b57")
    sliced = all("grams" in r for r in report)
    d.text((700, y), "Size (mm)", font=font(30, True), fill="#1f3b57")
    d.text((1010, y), "Print time" if sliced else "", font=font(30, True), fill="#1f3b57")
    d.text((1330, y), "Filament" if sliced else "~Filament", font=font(30, True), fill="#1f3b57")
    y += 55
    fs = 28 if rows <= 8 else 22
    step = min(70, int(620 / max(rows, 1)))
    for r in report:
        x, yy, z = r["size_mm"]
        d.line([70, y - 8, 1530, y - 8], fill="#dddddd", width=2)
        d.text((70, y), r["file"].replace(".stl", ""), font=font(fs), fill="#222222")
        d.text((700, y), f"{x:g} x {yy:g} x {z:g}", font=font(fs), fill="#222222")
        g = r.get("grams", r["approx_g"])
        if sliced:
            d.text((1010, y), fmt_time(r["print_minutes"]), font=font(fs), fill="#222222")
        d.text((1330, y), (f"{g:.0f} g" if g >= 1 else "< 1 g"), font=font(fs), fill="#222222")
        y += step
    settings = item.get("print_settings",
                        ["No supports", "0.2 mm layers", "3 walls, 15 % infill", "PLA or PETG"])
    y = max(y + 30, 860)
    # wrap the settings so long lists never run off the card
    lines, cur = [], "Recommended: "
    for part in settings:
        piece = part if cur.endswith(": ") else "  |  " + part
        if d.textbbox((0, 0), cur + piece, font=font(28))[2] > 1380:
            lines.append(cur)
            cur = part
        else:
            cur += piece
    lines.append(cur)
    d.rectangle([70, y, 1530, y + 110 + 45 * len(lines)], fill="#e9eef3", outline="#c9d3dd", width=2)
    for i, ln in enumerate(lines):
        d.text((100, y + 25 + 45 * i), ln, font=font(28), fill="#1f3b57")
    beds = sorted({r.get("bed_mm", 220) for r in report})
    bed_txt = f"{beds[0]:g} x {beds[0]:g} mm bed" if len(beds) == 1 else \
        f"{beds[0]:g} mm bed (larger files: {beds[-1]:g} mm bed)"
    n_dim = sum(len(r.get("dimension_checks", [])) for r in report)
    check = f"All files checked: one closed (watertight) piece, fits a {bed_txt}." + \
        (f" {n_dim} key dimensions measured on the mesh." if n_dim else "")
    if sliced:
        check = ("Slicer-verified (PrusaSlicer, 0.4 mm nozzle, 0.2 mm layers, 15 % infill): "
                 + ("no supports needed." if not any(r["needs_supports"] for r in report)
                    else "see which files need supports in the description."))
    if sliced:  # second line: bed + measured dimensions (the first line is the slicer result)
        check += f"\nOne closed piece per file, fits a {bed_txt}." + \
            (f" {n_dim} key dimensions measured on the mesh: all within tolerance." if n_dim else "")
    for k, ln in enumerate(check.split("\n")):
        d.text((100, y + 45 + 45 * len(lines) + 32 * k), ln, font=font(22), fill="#555555")
    img.save(path)


def cover_image(item, report, render, path):
    """First gallery image: the real iso render + a badge with the hero file's REAL size."""
    from PIL import Image, ImageDraw, ImageFont

    def font(size):
        for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
        return ImageFont.load_default()

    img = Image.open(render).convert("RGB")
    d = ImageDraw.Draw(img)
    x, y, z = report[0]["size_mm"]
    lines = [f"{len(report)} STL files included", item.get("cover_badge") or f"{x:g} x {y:g} x {z:g} mm"]
    top = 40
    for i, text in enumerate(lines):
        f = font(46 if i == 0 else 38)
        w = d.textbbox((0, 0), text, font=f)[2]
        d.rounded_rectangle([40, top, 40 + w + 50, top + 76], radius=14, fill="#1f3b57" if i == 0 else "#ffffff",
                            outline="#1f3b57", width=3)
        d.text((65, top + 12), text, font=f, fill="#ffffff" if i == 0 else "#1f3b57")
        top += 96
    no_sup = (not any(r.get("needs_supports") for r in report)) if all("needs_supports" in r for r in report) \
        else any("no support" in s.lower() for s in item.get("print_settings", ["No supports"]))
    if no_sup:
        f = font(40)
        w = d.textbbox((0, 0), "NO SUPPORTS", font=f)[2]
        d.rounded_rectangle([1560 - w - 50, 1100, 1560, 1170], radius=14, fill="#2e7d32")
        d.text((1560 - w - 25, 1112), "NO SUPPORTS", font=f, fill="#ffffff")
    img.save(path)


def variants_image(item, files, rot, out, path):
    """All variants side by side, rendered from the real STL files."""
    from PIL import Image, ImageDraw, ImageFont
    n = len(files)
    cols = 2 if n <= 4 else 3 if n <= 9 else 4
    rows_ = -(-n // cols)
    cw, ch = 1600 // cols, (1200 - 110) // rows_
    xvfb = ["xvfb-run", "-a"] if shutil.which("xvfb-run") else []
    sheet = Image.new("RGB", (1600, 1200), "#f7f7f5")
    d = ImageDraw.Draw(sheet)
    try:
        f_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
        f_lbl = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except OSError:
        f_title = f_lbl = ImageFont.load_default()
    d.rectangle([0, 0, 1600, 95], fill="#1f3b57")
    d.text((50, 22), f"All {n} versions included", font=f_title, fill="white")
    for i, stl in enumerate(files):
        tmp_scad, tmp_png = out / "_v.scad", out / "_v.png"
        tmp_scad.write_text(f"rotate({json.dumps(rot)}) import(\"{stl.as_posix()}\");\n")
        run([*xvfb, "openscad", "-q", "--render", "--viewall", "--autocenter", f"--imgsize={cw*2},{ch*2}",
             "--colorscheme=Tomorrow", f"--camera={item.get('grid_camera', '0,0,0,50,0,30,0')}", "-o", str(tmp_png), str(tmp_scad)])
        tile = Image.open(tmp_png).convert("RGB").resize((cw, ch - 34))
        x, y = (i % cols) * cw, 110 + (i // cols) * ch
        sheet.paste(tile, (x, y))
        d.text((x + 16, y + ch - 36), stl.stem.replace("_", " "), font=f_lbl, fill="#333333")
        tmp_scad.unlink(); tmp_png.unlink()
    sheet.save(path)


def blender_render(stl, png, color, angle, rot, size="1600x1200"):
    """Photoreal studio render (tools/render_blender.py). Returns False if Blender is missing."""
    exe = os.getenv("BLENDER", "blender")
    if not shutil.which(exe):
        return False
    samples = os.getenv("RENDER_SAMPLES", "64")
    run([exe, "-b", "-P", str(ROOT / "tools" / "render_blender.py"), "--", "--stl", str(stl), "--out", str(png),
         "--color", color, "--angle", str(angle), "--size", size, "--samples", samples,
         "--rot", ",".join(str(x) for x in rot)])
    return png.exists()


def sizes_block(report):
    """Every file's size in mm AND inches (US buyers think in inches)."""
    out = ["", "**Sizes** (W × D × H):"]
    for r in report:
        mm = " × ".join(f"{v:g}" for v in r["size_mm"])
        inch = " × ".join(f"{v / 25.4:.1f}" for v in r["size_mm"])
        bed = r.get("bed_mm", 220)
        extra = f" - needs a {bed:g} x {bed:g} mm bed" if bed > 220 else ""
        out.append(f"- {r['file'].replace('.stl', '')}: {mm} mm ({inch} in){extra}")
    return "\n".join(out)


def verification_block(report):
    lines = ["", "**Slicer-verified** (PrusaSlicer, 0.4 mm nozzle, 0.2 mm layers, 3 walls, 15 % infill, PLA):"]
    for r in report:
        sup = {"none": "no supports", "minimal": f"minimal supports ({r['support_pct']:.1f} % of material)",
               "needed": "supports needed"}[r.get("supports", "needed" if r["needs_supports"] else "none")]
        lines.append(f"- {r['file'].replace('.stl', '')}: {fmt_time(r['print_minutes'])}, {r['grams']:.0f} g, {sup}")
    lines.append("- Each file is also included as an oriented, ready-to-slice .3mf "
                 "(opens in Bambu Studio, OrcaSlicer and PrusaSlicer).")
    return "\n".join(lines)


def build(item_path: pathlib.Path, out: pathlib.Path) -> dict:
    item = yaml.safe_load(item_path.read_text())
    design = ROOT / item["design"]
    out = out / item["slug"]
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    files, report = [], []
    for v in item["variants"]:
        stl = out / v["file"]
        run(["openscad", "-q", "-o", str(stl), *scad_defs(v.get("params", {})), str(design)])
        mesh = trimesh.load(stl)
        ext = [round(float(x), 1) for x in mesh.extents]
        ok = bool(mesh.is_watertight)
        bed = float(v.get("bed", item.get("bed", BED_MM)))
        fits = fits_bed(mesh, bed)  # true check: some rotation on the bed fits inside bed x bed
        grams = round(mesh.volume / 1000 * 1.24 * 0.45, 0)  # fallback estimate if no slicer is available
        report.append({"file": v["file"], "watertight": ok, "size_mm": ext, "fits_bed": fits, "bed_mm": bed,
                       "approx_g": grams})
        bodies = len(mesh.split(only_watertight=False))
        report[-1]["bodies"] = bodies
        if bodies > int(v.get("parts", 1)):  # floating pieces = broken design (e.g. a detached loop)
            sys.exit(f"Quality check failed for {v['file']}: {bodies} separate bodies (expected {v.get('parts', 1)})")
        if not ok or not fits:
            sys.exit(f"Quality check failed for {v['file']}: {report[-1]}")
        # functional dimensions measured on the real mesh (pockets, holes, footprint, openings...)
        if v.get("checks"):
            dim_ok, dim_res = medidas.verificar(mesh, v["checks"])
            report[-1]["dimension_checks"] = [r["msg"] + (" OK" if r["ok"] else " FAIL") for r in dim_res]
            for r in dim_res:
                print(f"  [{'OK' if r['ok'] else 'FAIL'}] {v['file']}: {r['msg']}")
            if not dim_ok:
                sys.exit(f"Dimension check failed for {v['file']}")
        files.append(stl)

    # ---- digital print verification with PrusaSlicer + ready-to-slice 3MF files
    deliverables = list(files)
    if slicer.disponible():
        tmf_dir = out / "3mf"
        tmf_dir.mkdir()
        for r, stl in zip(report, files):
            r.update(slicer.verificar(stl, tmf_dir / (stl.stem + ".3mf")))
        tmf_zip = out / f"{item['slug']}_3mf_print_ready.zip"
        with zipfile.ZipFile(tmf_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(tmf_dir.glob("*.3mf")):
                z.write(f, f.name)
        deliverables.append(tmf_zip)
        needs = [r["file"] for r in report if r["needs_supports"]]
        # never claim "no supports" when the slicer says otherwise
        ps = [x for x in item.get("print_settings", []) if "no support" not in x.lower()]
        heavy = [r for r in report if r.get("supports") == "needed"]
        ps.insert(0, "No supports" if not needs else
                  (f"Supports needed on {len(heavy)} of {len(report)} files" if heavy
                   else "Minimal supports on some files (see description)"))
        item["print_settings"] = ps
        if needs:  # no "no supports" tag unless every file really prints without them
            item["tags"] = [t for t in item.get("tags", []) if "no support" not in t.lower()]
        item["description"] = item["description"].rstrip() + "\n" + verification_block(report)
    else:
        print("  (PrusaSlicer not installed: skipping slicer verification and 3MF export)")
    item["description"] = item["description"].rstrip() + "\n" + sizes_block(report)
    if len(deliverables) > 10:  # Cults accepts max 10 file links per request: bundle the STLs
        stl_zip = out / f"{item['slug']}_stl_files.zip"
        with zipfile.ZipFile(stl_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for f in files:
                z.write(f, f.name)
        deliverables = [stl_zip] + [d for d in deliverables if d.suffix != ".stl"]

    # ---- images
    rot = item.get("display_rotate", [0, 0, 0])
    colors = item.get("render_colors", ["#C8B69A", "#3E4A3D"])
    angles = item.get("render_angles", [30, 65])
    images, photo = [], []
    hero = out / f"{item['slug']}_hero.png"
    if blender_render(files[0], hero, colors[0], angles[0], rot):
        photo.append(hero)
        alt = out / f"{item['slug']}_alt.png"
        alt_file = files[1] if len(files) > 1 else files[0]
        if blender_render(alt_file, alt, colors[1 % len(colors)], angles[1 % len(angles)], rot):
            photo.append(alt)
    else:
        print("  (Blender not installed: using OpenSCAD previews)")
    # technical previews (OpenSCAD) - kept as secondary images
    wrapper = out / "_preview.scad"
    wrapper.write_text(f"rotate({json.dumps(rot)}) import(\"{files[0].as_posix()}\");\n")
    xvfb = ["xvfb-run", "-a"] if shutil.which("xvfb-run") else []
    tech = []
    for label, cam in (VIEWS if not photo else VIEWS[1:2]):
        png = out / f"{item['slug']}_{label}.png"
        run([*xvfb, "openscad", "-q", "--render", "--viewall", "--autocenter",
             "--imgsize=1600,1200", "--colorscheme=Tomorrow", f"--camera={cam}",
             "-o", str(png), str(wrapper)])
        tech.append(png)
    wrapper.unlink()
    base_for_cover = photo[0] if photo else tech[0]
    cover = out / f"{item['slug']}_00_cover.png"
    cover_image(item, report, base_for_cover, cover)
    images = [cover] + photo[1:] + (tech if not photo else [])
    if len(files) > 1:
        grid = out / f"{item['slug']}_variants.png"
        variants_image(item, files, rot, out, grid)
        images.append(grid)
    card = out / f"{item['slug']}_specs.png"
    spec_card(item, report, card)
    images.append(card)
    if photo:
        images += tech  # technical view last
    (out / "build_report.json").write_text(json.dumps(report, indent=2))
    return {"item": item, "files": deliverables, "stl_files": files, "images": images, "report": report}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("--out", default=str(ROOT / "build"))
    a = ap.parse_args()
    r = build(pathlib.Path(a.item), pathlib.Path(a.out))
    print(json.dumps(r["report"], indent=2))
    print("images:", [p.name for p in r["images"]])
