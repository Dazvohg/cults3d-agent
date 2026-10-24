// Key tags and luggage tag - original parametric design (Brian Sacco). Flat tags, raised text, no supports.
// part: "tag_rect", "tag_round", "tag_hex", "luggage". Everything prints flat on the bed, text facing up.
part  = "tag_rect";
label = "HOME";     // raised text ("" = blank tag)
hole  = 5;          // key ring hole diameter (mm)
t     = 3;          // plate thickness (mm)
th    = 1;          // text / rim height above the plate (mm)
$fn   = 64;

module rrect(w, d, h, r) {
    hull() for (sx = [-1, 1], sy = [-1, 1]) translate([sx * (w / 2 - r), sy * (d / 2 - r), 0]) cylinder(r = r, h = h);
}
module txt(size) {
    if (label != "") translate([0, 0, t - 0.01]) linear_extrude(th + 0.01)
        text(label, size = size, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
}
module tag_rect() {
    W = 60; D = 28;
    difference() {
        union() {
            rrect(W, D, t, 6);
            translate([0, 0, t - 0.01]) difference() {                  // raised rim
                rrect(W - 3, D - 3, th + 0.01, 4.5);
                translate([0, 0, -0.1]) rrect(W - 6, D - 6, th + 0.5, 3);
            }
        }
        translate([-W / 2 + 8, 0, -0.1]) cylinder(d = hole, h = t + th + 1);
    }
    translate([4, 0, 0]) txt(7.5);
}
module tag_round() {
    d0 = 36;
    difference() {
        union() {
            cylinder(d = d0, h = t);
            translate([0, 0, t - 0.01]) difference() {
                cylinder(d = d0 - 3, h = th + 0.01);
                translate([0, 0, -0.1]) cylinder(d = d0 - 6, h = th + 0.5);
            }
        }
        translate([0, d0 / 2 - 5.5, -0.1]) cylinder(d = hole, h = t + th + 1);
    }
    translate([0, -3, 0]) txt(11);
}
module tag_hex() {
    d0 = 40;
    difference() {
        union() {
            cylinder(d = d0, h = t, $fn = 6);
            translate([0, 0, t - 0.01]) difference() {
                cylinder(d = d0 - 4, h = th + 0.01, $fn = 6);
                translate([0, 0, -0.1]) cylinder(d = d0 - 7, h = th + 0.5, $fn = 6);
            }
        }
        translate([0, d0 * 0.866 / 2 - 6, -0.1]) rotate(0) cylinder(d = hole, h = t + th + 1);
    }
    translate([0, -3, 0]) txt(10);
}
module luggage() {
    W = 95; D = 60;
    difference() {
        rrect(W, D, t, 7);
        translate([-W / 2 + 10 - 2, -12, -0.1]) cube([4, 24, t + 1]);                       // strap slot
        translate([8, 0, t - 1.0]) rrect(62, 40, 2, 3);                                      // 1 mm recess for a printed name card
    }
}
if (part == "tag_rect") tag_rect();
if (part == "tag_round") tag_round();
if (part == "tag_hex") tag_hex();
if (part == "luggage") luggage();
