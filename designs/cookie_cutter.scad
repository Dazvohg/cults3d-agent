// Christmas cookie cutter - original parametric design (Brian Sacco)
// Flat flange on the bed, thin cutting wall pointing up: no overhangs, no supports.
kind     = "tree";   // "tree", "star", "bell", "person", "bauble"
size     = 75;       // longest side of the cookie shape (mm)
wall     = 1.2;      // cutting wall (3 perimeters of a 0.4 mm nozzle)
h        = 16;       // total height
flange_w = 4;        // pressing flange, outwards from the wall
flange_t = 2.5;      // flange thickness
$fn = 48;

// all shapes are drawn in a 100 mm reference box and scaled to `size`
module tree() {
    pts = [[0,50],[-18,20],[-10,20],[-28,-5],[-16,-5],[-40,-32],[-8,-32],[-8,-50],
           [8,-50],[8,-32],[40,-32],[16,-5],[28,-5],[10,20],[18,20]];
    polygon(pts);
}
module star() {
    polygon([for (i = [0:9]) let (a = 90 + i * 36, r = i % 2 == 0 ? 50 : 21) [r * cos(a), r * sin(a)]]);
}
module bell() {
    hull() { translate([0, 14]) circle(r = 30); translate([-45, -30]) square([90, 8]); }
    translate([0, -32]) circle(r = 8);
    translate([0, 44]) circle(r = 7);
}
module person() {
    translate([0, 36]) circle(r = 14);
    hull() { translate([0, 12]) circle(r = 18); translate([0, -8]) circle(r = 16); }
    for (s = [-1, 1]) {
        hull() { translate([s * 40, 14]) circle(r = 7); translate([0, 16]) circle(r = 10); }
        hull() { translate([s * 12, -30]) circle(r = 8); translate([s * 16, -44]) circle(r = 8); }
    }
}
module bauble() {
    translate([0, -4]) circle(r = 42);
    translate([-8, 34]) square([16, 14]);
}
module shape() {
    scale(size / 100) {
        if (kind == "tree") tree();
        else if (kind == "star") star();
        else if (kind == "bell") bell();
        else if (kind == "person") person();
        else bauble();
    }
}
// cutting wall
linear_extrude(h) difference() { offset(delta = wall) shape(); shape(); }
// pressing flange (rounded outside so it is comfortable on the hand)
linear_extrude(flange_t) difference() { offset(r = wall + flange_w) shape(); shape(); }
