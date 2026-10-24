// Car cup-holder adapter for a mate (adaptador de posavasos para mate) - original design (Brian Sacco)
// A tapered plug drops into the car cup holder; a wider well on top holds an 80 mm steel mate (Stanley, Hudson, Coleman).
// Prints upright with no supports: 45 deg flare between plug and well, hollow plug with a 45 deg pointed roof.
plug = 72;          // plug diameter at the top of the cup holder (variants 66 / 72 / 78)
md   = 86;          // mate well inner diameter
wall = 2.6;  $fn = 120;
ph = 55;            // plug height
taper = 3;          // plug is 3 mm narrower at the bottom (cup holders are tapered)
wo = md + 2 * wall; // well outer diameter
fh = (wo - plug) / 2 * 1.25;   // flare about 39 deg from vertical (safe without supports)
wh = 45;            // well depth
fl = 3;
z_floor = ph + fh;
module solid() {
    cylinder(d1 = plug - taper, d2 = plug, h = ph);
    translate([0, 0, ph]) cylinder(d1 = plug, d2 = wo, h = fh);
    translate([0, 0, z_floor]) cylinder(d = wo, h = wh + fl);
}
difference() {
    solid();
    translate([0, 0, z_floor + fl]) cylinder(d = md, h = wh + 1);                          // mate well
    ci = plug - taper - 2 * wall;                                                           // hollow plug, pointed roof
    translate([0, 0, -1]) cylinder(d = ci, h = ph - ci / 2 + 1);
    translate([0, 0, ph - ci / 2]) cylinder(d1 = ci, d2 = 0, h = ci * 0.65);   // roof steeper than 45 deg
    for (a = [0, 120, 240]) rotate(a) translate([md / 4, 0, ph - 25]) cylinder(d = 5, h = z_floor + fl - ph + 26, $fn = 24);   // drain into the hollow plug
    for (a = [0, 90, 180, 270]) rotate(a) rotate([90, 0, 90]) linear_extrude(plug) polygon([[-1, 6], [1, 6], [1, ph - 14], [0, ph - 13], [-1, ph - 14]]);   // slits with pointed tops: the plug flexes to grip
}
