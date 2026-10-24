// Display risers and plinths for action figures, models and collectibles - original parametric design (Brian Sacco).
// part: "riser" (stepped riser), "plinth_round", "plinth_hex". All print flat on the bed, no supports.
part   = "riser";
steps  = 3;      // riser: number of steps
tread  = 40;     // riser: depth of each step (mm), fits a 15 cm (6 in) figure's feet
rise   = 18;     // riser: height of each step (mm)
w      = 150;    // riser: width (mm)
d      = 80;     // plinth: diameter (round) or across corners (hex)
h      = 14;     // plinth: height
peg    = 0;      // plinth: centre hole diameter (0 = none)
$fn = 96;

module riser() {
    pts = concat([[0, 0], [steps * tread, 0]],
                 [for (i = [steps - 1 : -1 : 0]) each [[(i + 1) * tread, (i + 1) * rise], [i * tread, (i + 1) * rise]]]);
    translate([-w / 2, 0, 0]) rotate([90, 0, 90]) linear_extrude(w) polygon(pts);
}
module plinth_body(sides) {
    hull() {
        cylinder(d = d, h = h - 3, $fn = sides);
        translate([0, 0, h - 0.01]) cylinder(d = d - 6, h = 0.01, $fn = sides);   // 45 deg top chamfer
    }
}
module plinth(sides) {
    difference() {
        plinth_body(sides);
        translate([0, 0, h - 0.6]) difference() {   // decorative ring groove
            cylinder(d = d - 18, h = 1, $fn = sides);
            translate([0, 0, -0.1]) cylinder(d = d - 20, h = 1.2, $fn = sides);
        }
        if (peg > 0) translate([0, 0, h - 10]) cylinder(d = peg, h = 11);
    }
}
if (part == "riser") riser();
if (part == "plinth_round") plinth(96);
if (part == "plinth_hex") plinth(6);
