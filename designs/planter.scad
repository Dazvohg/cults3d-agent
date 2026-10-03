// Faceted Planter (cachepot) with drainage and matching saucer - original parametric design (Brian Sacco)
// Sized around STANDARD NURSERY POTS: set `pot` to the nursery pot's rim diameter (mm) and the
// planter is computed so the pot drops in with 14 mm of total clearance at the narrowest point
// (inscribed circle of the facets) and enough depth for the pot's height.
//   Common nursery pots (rim Ø x height): 9 cm x ~8 cm, 12 cm x ~10.5 cm, 15 cm x ~13 cm.
pot      = 120;    // nursery pot rim diameter (mm); 0 = use top_d / height below
pot_h    = 0;      // nursery pot height (0 = 0.87 x pot, typical for round nursery pots)
top_d    = 110;    // (only if pot = 0) outer diameter at the rim, corner to corner
height   = 100;    // (only if pot = 0)
taper    = 0.80;   // bottom diameter as a fraction of the top (nursery pots taper ~0.75)
sides    = 9;      // facets (6-12 look great; 60 = round)
twist    = 30;     // degrees of twist from bottom to top
wall     = 2.4;
floor_t  = 3;
clearance = 14;    // total diametral clearance around the nursery pot rim
drain_d  = 8;      // drainage hole (0 = none)
part     = "pot";  // "pot" or "saucer"

k   = cos(180 / sides);                                     // inscribed / circumscribed ratio
PH  = pot > 0 ? (pot_h > 0 ? pot_h : 0.87 * pot) : 0;
HT  = pot > 0 ? PH + floor_t + 6 : height;                  // 6 mm: pot rim sits just below the top
Z_RIM = HT - 6;                                             // height where the nursery pot's rim sits
S_RIM = taper + (1 - taper) * Z_RIM / HT;                   // loft scale there (1 = top)
// the clearance is guaranteed WHERE THE POT RIM SITS (the planter narrows towards the bottom)
TD  = pot > 0 ? ((pot + clearance) / S_RIM + 2 * wall) / k : top_d;   // outer rim, corner to corner
echo(str("PLANTER outer_rim_corner=", TD, " height=", HT, " pot_rim_z=", Z_RIM));

module shell(d_top, h) {
    linear_extrude(height=h, twist=-twist, scale=1/taper, slices=40)
        circle(d=d_top*taper, $fn=sides);
}
if (part == "pot") {
    difference() {
        shell(TD, HT);
        // inner shell: same loft (twist + scale aligned with the outside), sized so that at the RIM
        // the wall is exactly `wall` thick across the flats; only the part above the floor is removed
        intersection() {
            linear_extrude(height=HT + 0.01, twist=-twist, scale=1/taper, slices=40)
                circle(d=(TD * k - 2 * wall) / k * taper, $fn=sides);
            translate([0, 0, floor_t]) cylinder(d=TD * 2, h=HT);
        }
        if (drain_d > 0) translate([0,0,-1]) cylinder(d=drain_d, h=floor_t+2, $fn=32);
        // three drainage channels under the pot
        for (a=[0:120:240]) rotate(a) translate([0,-4,-0.01]) cube([TD, 8, 1.2]);
    }
} else {
    sd = TD*taper + 16;   // saucer: 8 mm wider than the planter base on every side
    difference() {
        cylinder(d1=sd-4, d2=sd, h=14, $fn=sides);
        translate([0,0,2.4]) cylinder(d1=sd-4-2*wall/k, d2=sd-2*wall/k, h=14, $fn=sides);
    }
}
