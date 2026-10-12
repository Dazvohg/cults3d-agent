// Stylised samurai kabuto desk figure - original parametric design built from primitives.
// Dome bowl, five flared neck-guard tiers, face opening and a crescent crest. Prints upright, no supports.
size   = 80;     // dome diameter (mm); everything scales with it
crest  = true;   // crescent maedate on the front
base_h = 6;
$fn = 72;

r = size/2;
module tiers() {
    // neck guard: 5 tiers flaring outward as they go down (no overhang when printed upright)
    for (i = [0:4])
        translate([0, 0, base_h + 2 + (4 - i)*5])
            cylinder(r1 = r*(1.0 + 0.10*(i+1)), r2 = r*(1.0 + 0.10*i), h = 5.2);
}
module bowl() {
    translate([0, 0, base_h + 27]) intersection() {
        sphere(r = r*0.98);
        translate([-r*2, -r*2, 0]) cube([r*4, r*4, r*2]);
    }
}
module crescent() {
    // vertical plate on the front (towards -Y), a ring minus an offset ring
    translate([0, -r*0.55, base_h + 27 + r*0.55]) rotate([90, 0, 0])
        linear_extrude(height = 3, center = true)
            difference() { circle(r = r*0.55); translate([0, -r*0.18]) circle(r = r*0.47); }
    // stem fusing the crescent to the dome (otherwise the two tips can float free of the bowl)
    translate([-2.5, -r*0.55 - 1.5, base_h + 27 + r*0.4]) cube([5, 3, r*0.55 + r*0.35 - r*0.4 + r*0.0]);
}
union() {
    // round base plate
    cylinder(r = r*1.6, h = base_h);
    difference() {
        union() { tiers(); bowl(); }
        // face opening: arch cut into the front
        translate([0, 0, base_h + 8]) rotate([90, 0, 0]) linear_extrude(height = r*1.6) {
            translate([-r*0.42, 0]) square([r*0.84, r*0.35]);
            translate([0, r*0.35]) scale([1, 0.8]) circle(r = r*0.42);
        }
    }
    if (crest) crescent();
}
