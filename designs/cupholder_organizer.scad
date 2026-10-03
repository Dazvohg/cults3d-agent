// Car cup-holder organizer insert: coin cup, card slot and two pen / lip-balm holes. Original design (Brian Sacco)
// dia = the inside diameter of YOUR cup holder (measure at the narrowest point). The insert is 1.0 mm smaller.
// Prints standing, open side up, no supports (the bottom edge has a 45 degree lead-in).
dia = 74;
height = 80;
floor_t = 3;
wall = 1.6;
$fn = 120;

OD = dia - 1.0;
R  = OD / 2;
coin_d = 0.9 * R;                       // coin cup
pen_d  = 14;
cy  = -R + 2.4 + coin_d / 2;            // coin cup centre (2.4 mm wall at the bottom)
sy0 = cy + coin_d / 2 + wall;           // card slot start
sy1 = sy0 + 8;                          // card slot end (8 mm deep)
py  = sy1 + wall + pen_d / 2;           // pen holes centre

module pockets() {
    translate([0, cy, floor_t]) cylinder(d = coin_d, h = height);
    translate([-28, sy0, floor_t]) cube([56, 8, height]);                     // cards stand on the short edge
    for (sx = [-1, 1]) translate([sx * 12, py, floor_t]) cylinder(d = pen_d, h = height);
}
difference() {
    union() {
        translate([0, 0, 4]) cylinder(r = R, h = height - 4);
        cylinder(r1 = R - 4, r2 = R, h = 4);          // 45 degree lead-in
    }
    pockets();
}
