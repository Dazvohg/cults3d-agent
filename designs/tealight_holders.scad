// LED tealight holders - original parametric design (Brian Sacco). For LED tea lights only (never a real flame).
// part: "lattice" (diamond windows), "slots" (vertical slots), "faceted" (low cup with a twisted faceted wall).
// Everything prints upright with the open end up, no supports: diamond windows have 45 deg tops, slots have pointed 45 deg tops.
part = "lattice";
tl   = 38;      // tealight diameter (mm): 38 standard LED, 43-44 large LED
clr  = 3;       // total clearance (mm)
wall = 3;
fl   = 3;       // floor thickness
$fn  = 72;

di = tl + clr;          // pocket diameter
do = di + 2 * wall;     // outer diameter

module lattice() {
    H = 56;
    difference() {
        cylinder(d = do, h = H);
        translate([0, 0, fl]) cylinder(d = di, h = H);
        for (row = [0 : 2]) for (k = [0 : 7])
            rotate([0, 0, k * 45 + (row % 2) * 22.5]) translate([0, 0, 15 + row * 14])
                rotate([90, 0, 0]) cylinder(d = 14, h = do, $fn = 4, center = false);
    }
}
module slots() {
    H = 50;
    difference() {
        cylinder(d = do, h = H);
        translate([0, 0, fl]) cylinder(d = di, h = H);
        for (k = [0 : 11]) rotate([0, 0, k * 30]) translate([0, do, 0]) rotate([90, 0, 0])
            linear_extrude(do) polygon([[-2, 9], [2, 9], [2, 38], [0, 40], [-2, 38]]);     // slot with a 45 deg pointed top
    }
}
module faceted() {
    H = 30;
    linear_extrude(height = H, twist = -30, slices = 60, convexity = 6) difference() {
        circle(d = do + 6, $fn = 8);
        circle(d = di, $fn = 72);
    }
    cylinder(d = do + 6, h = fl, $fn = 8);       // closed floor
}
if (part == "lattice") lattice();
if (part == "slots") slots();
if (part == "faceted") faceted();
