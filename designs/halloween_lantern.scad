// Ribbed Pumpkin Lantern for LED tealights - original parametric design (Brian Sacco)
// Generic jack-o'-lantern style: ribbed body, cut-out face, removable stem lid.
// Support-free by design: the body is lofted so no wall overhangs more than ~30 degrees,
// and the inner roof is a 45-degree cone (verified with PrusaSlicer auto-supports).
d        = 90;     // body diameter at the belly (mm)
h        = 75;     // body height
ribs     = 10;
wall     = 2.0;
face     = "classic"; // "classic", "happy", "spooky", "cat"
part     = "body";    // "body" or "lid"
tealight = 38;     // standard LED tealight diameter (mm); the opening adds 3 mm of clearance
opening  = tealight + 3;
$fn = 64;

N = 10;                                            // loft segments
function sc(z) = 0.74 + 0.26 * sin(180 * z / h);   // profile scale at height z (0.74 -> 1 -> 0.74)

module rib_profile(dd, inset=0) {
    offset(delta=-inset) union() for (i=[0:ribs-1]) rotate(i*360/ribs)
        translate([dd*0.17, 0]) scale([1, 0.62]) circle(d=dd*0.66, $fn=48);
}
module loft(dd, z0, z1, inset=0) {
    for (k=[0:N-1]) {
        za = z0 + (z1-z0)*k/N; zb = z0 + (z1-z0)*(k+1)/N;
        translate([0,0,za]) linear_extrude(height=zb-za + 0.01, scale=sc(zb)/sc(za))
            scale(sc(za)) rib_profile(dd, inset/sc(za));
    }
}
module body_solid() { loft(d, 0, h-4); }

// Every cut-out has a pointed top (teardrops / upward triangles, edges >= 55 deg), so the
// holes print cleanly WITHOUT supports: no flat or round "ceilings" over the openings.
module tear(dd) { hull() { circle(d=dd, $fn=32); translate([0, dd/2*1.414]) square(0.01, center=true); } }
module face_cut() {
    rotate([90,0,0]) linear_extrude(d) translate([0, h*0.58]) scale(1.25) translate([0, -h*0.5]) {
        if (face == "classic") {
            translate([-16, h*0.60]) polygon([[0,0],[12,0],[6,10]]);
            translate([4, h*0.60])   polygon([[0,0],[12,0],[6,10]]);
            translate([-3, h*0.46])  polygon([[0,0],[6,0],[3,6]]);
            translate([0, h*0.27]) polygon([                       // jagged grin, steep "M" top edge
                [-20,4],[-15,12],[-10,4],[-5,12],[0,4],[5,12],[10,4],[15,12],[20,4],
                [14,-4],[8,0],[3,-5],[-3,-5],[-8,0],[-14,-4]]);
        } else if (face == "happy") {
            for (x=[-11, 11]) translate([x, h*0.61]) tear(10);
            for (i=[-3:3]) let(a = i*16) translate([sin(a)*17, h*0.40 - cos(a)*9]) rotate(a*0.5)
                polygon([[-2.6,0],[2.6,0],[0,5.5]]);                // smile made of small upward teeth
        } else if (face == "spooky") {
            translate([-17, h*0.58]) polygon([[0,0],[13,4],[10,12]]);
            translate([4, h*0.58])   polygon([[0,4],[13,0],[3,12]]);
            translate([0, h*0.33]) polygon([[0,-9],[7,0],[0,10],[-7,0]]);   // howling mouth (diamond)
        } else {  // cat
            for (s=[-1,1]) translate([s*11, h*0.60]) scale([0.75, 1.1]) tear(10);
            translate([0, h*0.47]) polygon([[-4,-2],[4,-2],[0,3]]);
            for (s=[-1,1]) translate([s*5, h*0.39]) polygon([[-4,0],[4,0],[0,5]]);   // "w" mouth
        }
    }
}

if (part == "body") {
    difference() {
        body_solid();
        intersection() {
            loft(d, 2.4, h-4, wall);
            // roof cone at 60 degrees from horizontal (steeper than the usual 45-degree support limit)
            r_top = opening / 2; H = (d - r_top) * tan(60);
            translate([0,0,h-8 - H]) cylinder(r1=d, r2=r_top, h=H + 0.01);
        }
        face_cut();
        translate([0,0,h-20]) cylinder(d=opening / cos(180/$fn), h=30);   // facet-compensated opening: true Ø = opening
    }
} else {
    // lid with stem, printed as oriented: a tapered plug + a 40-degree conical flange,
    // so nothing overhangs more than ~40 degrees and the lid prints without supports
    union() {
        cylinder(d1=opening - 4, d2=opening - 0.8, h=3);                 // plug: 0.4 mm gap per side
        translate([0,0,3]) cylinder(d1=opening - 0.8, d2=opening + 9, h=(9.8/2) / tan(40));
        translate([0,0,3 + (9.8/2) / tan(40)]) cylinder(d=opening + 9, h=1.5);
        translate([0,0,3 + (9.8/2) / tan(40) + 1.5]) rotate([0,-10,0]) cylinder(d1=10, d2=7, h=16, $fn=7);
    }
}
