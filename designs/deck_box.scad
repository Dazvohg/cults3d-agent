// Snug-fit card deck box (base + sliding cap) - original parametric design.
// Sizes are SLEEVED cards: standard TCG/poker 66 x 91, mini Euro 47 x 71, tarot 73 x 123.
// Cards stand on edge; the cap slides over the top `ov` mm of the base. Both parts print open side up, no supports.
part    = "base";  // "base" | "cap"
card_w  = 66;      // sleeved card width (mm)
card_h  = 91;      // sleeved card height (mm)
cards   = 100;     // number of sleeved cards
thk     = 0.65;    // thickness of one sleeved card (mm)
clr     = 1.0;     // free play around the stack (mm)
wall    = 2.4;
floor_t = 2.4;
top_t   = 2.4;
fit     = 0.3;     // gap between base and cap walls (FDM friction fit)
ov      = 22;      // how far the cap slides down over the base (mm)
notch_r = 12;      // thumb notch radius in the front/back walls
$fn = 48;

iw = card_w + clr;            // inner width
id = cards * thk + clr;       // inner depth (stack thickness)
ih = card_h + clr;            // inner height available for the cards
bw = iw + 2*wall;             // base outer width
bd = id + 2*wall;             // base outer depth
bh = floor_t + ih - ov;       // base outer height (cards stick out `ov` into the cap)
r  = 3;                       // vertical corner radius
echo(str("DECK_BOX base=", bw, "x", bd, "x", bh, " cap=", bw + 2*(fit+wall), "x", bd + 2*(fit+wall), "x", ov + top_t));

module rbox(w, d, h, rr) {
    hull() for (sx = [-1, 1], sy = [-1, 1])
        translate([sx*(w/2 - rr), sy*(d/2 - rr), 0]) cylinder(r = rr, h = h);
}

module base() {
    difference() {
        rbox(bw, bd, bh, r);
        translate([0, 0, floor_t]) rbox(iw, id, bh, max(r - wall, 0.6));
        // thumb notch through the front and back walls, centred on the rim
        translate([0, 0, bh]) rotate([90, 0, 0]) cylinder(r = notch_r, h = bd + 2, center = true);
    }
}

module cap() {
    cw = bw + 2*fit; cd = bd + 2*fit;
    difference() {
        rbox(cw + 2*wall, cd + 2*wall, ov + top_t, r + fit + wall - 0.0);
        translate([0, 0, top_t]) rbox(cw, cd, ov + 1, r + fit);
    }
}

if (part == "cap") cap(); else base();
