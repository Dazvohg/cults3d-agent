// Hose reducer / coupler for portable air-conditioner exhaust hose, dryer vent and duct work - original design (Brian Sacco)
// Two round spigots joined by a gentle cone. Prints standing on the large end: every surface is 45 degrees or steeper.
d_a    = 150;   // spigot A outer diameter (mm), the big end that sits on the bed
d_b    = 130;   // spigot B outer diameter (mm); same as d_a = straight coupler
len_a  = 40;    // length of spigot A
len_b  = 40;    // length of spigot B
wall   = 2.2;
ridge  = 1.0;   // grip ridge height (45 deg both sides) on each spigot
$fn = 120;

ra = d_a / 2; rb = d_b / 2;
cone_h = abs(ra - rb) < 0.01 ? 0 : max(8, abs(ra - rb) * 1.25);   // about 39 deg from vertical or steeper
z1 = len_a; z2 = len_a + cone_h; z3 = z2 + len_b;

function rid(r, z0, l) = [[r, z0 + l * 0.35], [r + ridge, z0 + l * 0.35 + ridge], [r, z0 + l * 0.35 + 2 * ridge]];

outer = concat(
    [[0, 0], [ra, 0]],
    rid(ra, 0, len_a),
    [[ra, z1]],
    cone_h > 0 ? [[rb, z2]] : [],
    rid(rb, z2, len_b),
    [[rb, z3], [0, z3]]
);
inner = [[0, -1], [ra - wall, -1], [ra - wall, z1], [rb - wall, z2], [rb - wall, z3 + 1], [0, z3 + 1]];

difference() {
    rotate_extrude() polygon(outer);
    rotate_extrude() polygon(inner);
}
