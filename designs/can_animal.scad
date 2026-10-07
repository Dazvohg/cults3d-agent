// Animal can cover - original parametric design (Brian Sacco)
// Snap-on lid for aluminium beverage cans with a flat animal silhouette (ears / wings / eyes) and an engraved face.
// Prints upside-down (animal face on the bed, skirt pointing up): NO supports. The face lines are 0.4 mm deep grooves
// on the bed side (1 mm wide, so the next layer just bridges over them).
// Fits the double seam of standard aluminium can ends: 202 = 54.0 mm, 200 = 50.8 mm, 204 = 57.2 mm.
animal  = "cat";  // "cat", "frog", "bat", "bear"
rim_d   = 54.0;   // nominal can-end diameter (mm)
clr     = 0.8;
skirt_h = 12;
wall    = 1.6;
top_t   = 2.0;
bead    = 0.6;
ear_t   = 3.0;    // thickness of the flat silhouette parts outside the lid wall
gw      = 1.0;    // groove width of the engraved face
gd      = 0.4;    // groove depth (two layers)
$fn = 96;

id = rim_d + clr;
od = id + 2 * wall;
r  = od / 2;
bz = top_t + 3.2;
s  = rim_d / 54;   // scale of the face art

// ---------- 2D helpers
module ring(d, w = gw) { difference() { circle(d = d); circle(d = d - 2 * w); } }
module seg(a, b, w = gw) { hull() { translate(a) circle(d = w, $fn = 16); translate(b) circle(d = w, $fn = 16); } }
module pol(pts, w = gw) { for (i = [0 : len(pts) - 2]) seg(pts[i], pts[i + 1], w); }
module mirror_x() { children(); mirror([1, 0]) children(); }
function P(a, k) = [a[0] * k, a[1] * k];

// ---------- silhouette (flat, same plane as the lid top)
module ear_tri(ang, base_a = 20, tip_r = 1.38, base_r = 0.9, lean = 6) {
    polygon([[r * base_r * cos(ang - base_a), r * base_r * sin(ang - base_a)],
             [r * base_r * cos(ang + base_a), r * base_r * sin(ang + base_a)],
             [r * tip_r * cos(ang + lean), r * tip_r * sin(ang + lean)]]);
}
module silhouette() {
    if (animal == "cat") { ear_tri(54, base_a = 19, tip_r = 1.45, lean = -5); ear_tri(126, base_a = 19, tip_r = 1.45, lean = 5); }
    if (animal == "bear") for (a = [50, 130]) translate([r * 0.98 * cos(a), r * 0.98 * sin(a)]) circle(d = r * 0.62);
    if (animal == "frog") for (a = [58, 122]) translate([r * 0.92 * cos(a), r * 0.92 * sin(a)]) circle(d = r * 0.66);
    if (animal == "bat") {
        ear_tri(72, base_a = 11, tip_r = 1.3, lean = 3); ear_tri(108, base_a = 11, tip_r = 1.3, lean = -3);
        mirror_x() polygon([[r * 0.80, r * 0.50], [r * 1.25, r * 0.78], [r * 1.78, r * 0.62], [r * 1.60, r * 0.30],
                            [r * 1.48, r * 0.40], [r * 1.40, r * 0.08], [r * 1.22, r * 0.20], [r * 1.12, r * -0.12],
                            [r * 0.90, r * -0.05]]);
    }
}

// ---------- engraved face (2D grooves)
module face() {
    k = s;
    if (animal == "cat") {
        mirror_x() { translate([9.5 * k, 5 * k]) ring(9 * k); translate([9.5 * k, 5 * k]) circle(d = 3.2 * k);
                     pol([[7 * k, -7 * k], [22 * k, -4 * k]]); pol([[7 * k, -9.5 * k], [23 * k, -10.5 * k]]);
                     pol([[6 * k, -12 * k], [19 * k, -16 * k]]); }
        translate([0, -4 * k]) rotate(-90) circle(d = 4.4 * k, $fn = 3);
        mirror_x() translate([r * 1.05 * cos(52), r * 1.05 * sin(52)]) rotate(-38) ring(r * 0.42, 1.0, $fn = 3);
        pol([[0, -6.5 * k], [0, -9.5 * k]]); pol([[0, -9.5 * k], [-3.5 * k, -12 * k]]); pol([[0, -9.5 * k], [3.5 * k, -12 * k]]);
    }
    if (animal == "bear") {
        mirror_x() { translate([10 * k, 6 * k]) circle(d = 4.2 * k); }
        translate([0, -5 * k]) ring(17 * k);
        translate([0, -2.5 * k]) rotate(-90) circle(d = 5 * k, $fn = 3);
        pol([[0, -5 * k], [0, -9 * k]]); pol([[0, -9 * k], [-3.5 * k, -11.5 * k]]); pol([[0, -9 * k], [3.5 * k, -11.5 * k]]);
        mirror_x() translate([r * 0.98 * cos(50) - r * 0.98 * cos(50) + (r * 0.98 * cos(50)), r * 0.98 * sin(50)]) ring(r * 0.30);
    }
    if (animal == "frog") {
        mirror_x() translate([r * 0.92 * cos(58), r * 0.92 * sin(58)]) { ring(r * 0.42); circle(d = r * 0.14); }
        mirror_x() { translate([3 * k, 4 * k]) circle(d = 2.2 * k, $fn = 24); }
        pol([for (t = [-70 : 10 : 70]) [t / 70 * 19 * k, -8 * k + 7 * k * (t / 70) * (t / 70)] ]);
        pol([[-19 * k, -8 * k + 7 * k], [-21.5 * k, -8 * k + 9.5 * k]]); pol([[19 * k, -8 * k + 7 * k], [21.5 * k, -8 * k + 9.5 * k]]);
    }
    if (animal == "bat") {
        mirror_x() { translate([8 * k, 2 * k]) ring(8 * k); translate([8 * k, 2 * k]) circle(d = 2.8 * k); }
        pol([[-4 * k, -7 * k], [-2 * k, -10 * k], [0, -7 * k], [2 * k, -10 * k], [4 * k, -7 * k]]);
        pol([[-3 * k, -7 * k], [-3 * k, -9 * k]]); pol([[3 * k, -7 * k], [3 * k, -9 * k]]);
        translate([0, -2 * k]) rotate(-90) circle(d = 3.4 * k, $fn = 3);
    }
}

difference() {
    union() {
        difference() {
            hull() {
                cylinder(d = od - 1.6, h = 0.01);
                translate([0, 0, 0.8]) cylinder(d = od, h = 0.01);
                translate([0, 0, top_t + skirt_h - 0.01]) cylinder(d = od, h = 0.01);
            }
            translate([0, 0, top_t]) cylinder(d = id, h = skirt_h + 1);
            translate([0, 0, top_t + skirt_h - 0.8]) cylinder(d = id, d2 = id + 1.6, h = 0.81);
        }
        // flat silhouette: full ear_t outside the can seam, top_t thick over the cavity
        difference() {
            linear_extrude(ear_t) silhouette();
            translate([0, 0, top_t]) cylinder(d = id + 0.01, d2 = id + 0.01, h = ear_t);
        }
    }
    translate([0, 0, -0.01]) linear_extrude(gd + 0.01) face();   // engraved face on the bed side
}
translate([0, 0, bz]) rotate_extrude() polygon([
    [id / 2 + 0.5, 0], [id / 2, 0], [id / 2 - bead, bead],
    [id / 2 - bead, bead + 0.4], [id / 2, 2 * bead + 0.4], [id / 2 + 0.5, 2 * bead + 0.4]]);