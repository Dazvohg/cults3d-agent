// Parametric Corner Bracket with side gussets - original design (Brian Sacco)
// Output is in PRINT orientation: standing on the horizontal arm, gussets as vertical walls,
// so it prints without supports (verified with PrusaSlicer). Inner corner fillet adds strength.
arm       = 60;    // arm length from the outer corner (mm)
width     = 30;    // bracket width (mm)
t         = 5;     // plate thickness (mm)
gusset_t  = 3;     // thickness of each side gusset
screw     = 4;     // metric screw size: 3, 4 or 5
holes     = 1;     // screw holes per arm: 1 or 2
$fn = 48;

clear = screw == 3 ? 3.4 : screw == 4 ? 4.5 : 5.5;   // clearance hole
// ISO 10642 max head diameter dk (M3 6.72 / M4 8.96 / M5 11.20) + 0.4 mm so the head sits flush.
// Clearance holes per ISO 273 medium (3.4 / 4.5 / 5.5). Also fits 4 and 5 mm wood screws (DIN 7997 heads <= 10 mm).
head  = (screw == 3 ? 6.72 : screw == 4 ? 8.96 : 11.20) + 0.4;  // countersink diameter at the surface
g_len = arm - 2;                                     // gusset leg length

// hole positions measured from the outer corner, kept clear of the inner corner
function hole_pos(i) = holes == 1 ? t + (arm - t) * 0.6
                                  : t + (arm - t) * (i == 0 ? 0.38 : 0.78);

module profile() {                 // the L seen from the side
    square([arm, t]);              // horizontal arm (outer face at y = 0)
    square([t, arm]);              // vertical arm   (outer face at x = 0)
}
module fillet(r = 4) {           // rounded inner corner (less stress concentration)
    translate([t, t]) difference() { square(r); translate([r, r]) circle(r=r, $fn=40); }
}
module gusset() { polygon([[t, t], [g_len, t], [t, g_len]]); }

module tear2d(dd) { hull() { circle(d=dd); translate([0, dd/2*1.414]) square(0.01, center=true); } }
// Same countersunk hole with a pointed (teardrop) top, for holes whose axis is horizontal when printed:
// the pointed roof is self-supporting. The point faces local +Y (= up in print orientation).
module countersunk_tear(len) {
    translate([0, 0, -1]) linear_extrude(len + 2) tear2d(clear);
    hull() {
        translate([0, 0, len - (head - clear) / 2]) cylinder(d1=clear, d2=head, h=(head - clear) / 2 + 0.01);
        translate([0, head/2*1.414, len]) cube(0.01, center=true);
    }
    translate([0, 0, len]) linear_extrude(1) tear2d(head);
}
module countersunk(len) {          // axis along +Z, head at z = len
    translate([0, 0, -1]) cylinder(d = clear, h = len + 2);
    translate([0, 0, len - (head - clear) / 2]) cylinder(d1 = clear, d2 = head, h = (head - clear) / 2 + 0.01);
    translate([0, 0, len]) cylinder(d = head, h = 1);
}

rotate([90, 0, 0]) translate([0, 0, -width]) difference() {
    union() {
        linear_extrude(width) profile();
        linear_extrude(width) fillet();
        linear_extrude(gusset_t) gusset();                       // bottom gusset (bed side)
        translate([0, 0, width - gusset_t]) linear_extrude(gusset_t) gusset();  // top gusset
    }
    for (i = [0 : holes - 1]) {
        // horizontal arm: hole along Y, countersink on the inner face (y = t)
        translate([hole_pos(i), 0, width / 2]) rotate([-90, 0, 0]) countersunk(t);
        // vertical arm: hole along X, countersink on the inner face (x = t)
        translate([0, hole_pos(i), width / 2]) rotate([0, 90, 0]) countersunk_tear(t);
    }
}
