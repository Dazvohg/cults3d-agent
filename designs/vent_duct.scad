// VentDucts - modular twist-lock (bayonet) duct parts for ventilation, grow tents, workshop fans and 3D-printer enclosures
// Original design (Brian Sacco). Male spigot OD = nominal - 0.6 so it slides INTO a duct of that nominal inside diameter.
// Every part prints standing with the open end up and the male end down: no supports (all overhangs 45 degrees or steeper).
part    = "straight";   // straight | reducer | cap
nominal = 100;          // male spigot size in mm: 100 (4"), 125 (5"), 150 (6")
nominal_s = 0;          // socket size (0 = same as the male size); bigger than nominal = reducer
body_len = 100;         // straight part: length of plain tube between male spigot and socket
$fn = 120;

d      = nominal - 0.6;      // male spigot outer diameter
wall   = 2.4;
r_b    = d/2 - wall;         // air passage radius
lm     = 32;                 // male spigot length
S      = 30;                 // socket depth
clr    = 0.4;                // radial clearance male/socket
ds     = (nominal_s > 0 ? nominal_s : nominal) - 0.6;   // socket nominal outer diameter of the spigot it takes
r_i    = ds/2 + clr;         // socket inner radius
sw     = 3.2;                // socket wall
r_o    = r_i + sw;           // socket outer radius
zg     = 2;                  // lug / groove height above spigot tip or socket ledge
lug_w  = 8;                  // lug width (mm, tangential)
sweep  = 32;                 // twist angle to lock (deg)

lug2d = [[d/2 - 0.5, 0], [d/2 + 2.0, 2.5], [d/2 + 2.0, 4.5], [d/2 - 0.5, 7]];
function ang(w, r) = 360 * w / (2 * PI * r);

module lugs() {                      // three 45-degree-sided lugs
    for (a = [0, 120, 240]) rotate([0, 0, a - ang(lug_w, d/2) / 2])
        rotate_extrude(angle = ang(lug_w, d/2)) translate([0, zg]) polygon(lug2d);
}
module socket_cuts() {               // local z = 0 at the socket ledge
    translate([0, 0, 0]) cylinder(r = r_i, h = S + 1);
    for (a = [0, 120, 240]) rotate([0, 0, a - ang(lug_w + 1, ds/2) / 2]) {
        // twist groove with 45-degree walls (lug profile + 0.5 mm)
        rotate_extrude(angle = ang(lug_w + 1, ds/2) + sweep)
            translate([0, zg]) offset(delta = 0.5) polygon(lug2d);
        // axial entry channel up to the rim
        rotate_extrude(angle = ang(lug_w + 1, ds/2))
            translate([ds/2 - 0.4, zg + 3.5]) square([2.9, S - zg - 3.5 + 1]);
    }
}

cone_h = max(4, r_o - d/2);
module straight() {
    zl = lm + body_len + cone_h;                 // socket ledge height
    difference() {
        union() {
            cylinder(r = d/2, h = lm + body_len);
            translate([0, 0, lm + body_len]) cylinder(r1 = d/2, r2 = r_o, h = cone_h);
            translate([0, 0, zl]) cylinder(r = r_o, h = S);
        }
        translate([0, 0, -1]) cylinder(r = r_b, h = zl + 2);
        translate([0, 0, zl]) socket_cuts();
    }
    lugs();
}
module cap() {
    fl = 3;
    difference() {
        cylinder(r = r_o, h = fl + S);
        translate([0, 0, fl]) socket_cuts();
    }
}
if (part == "cap") cap(); else straight();
