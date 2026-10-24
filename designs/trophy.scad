// Football trophy set - original parametric design (Brian Sacco).
// part: "ball_half" (hemisphere with engraved panels and 3 pin holes; print two), "ball_pins" (3 alignment pins),
//       "boot" (flat cleat silhouette with 2 tabs), "base_ball", "base_boot" (plinths with an engraved plaque text).
// No supports: halves print dome-up on their flat face, the boot prints lying on its side, bases print as they are.
part   = "base_ball";
label  = "CHAMPION";  // engraved text on the plinth ("" = blank plaque)
R      = 30;          // ball radius (mm)
bt     = 16;          // boot thickness (mm)
$fn = 96;
phi = (1 + sqrt(5)) / 2;
verts = [for (s1 = [-1, 1], s2 = [-1, 1]) each [[0, s1, s2 * phi], [s1, s2 * phi, 0], [s2 * phi, 0, s1]]];

function unit(v) = v / norm(v);
// Pentagon panel engraved 1.2 mm into the ball. The cutter walls are VERTICAL (parallel to z) so the dome never overhangs:
// the 5 corners of the patch are placed on the sphere and projected straight down.
module panel(v0) {
    v = unit(v0);
    nb = [for (w = verts) if (abs(unit(w) * v - 0.4472) < 0.01) unit(w)];       // neighbouring vertices
    a0 = unit(nb[0] - (nb[0] * v) * v);                                           // tangent towards one neighbour
    b0 = cross(v, a0);
    al = 21;                                                                     // angular radius of the patch (deg)
    pts = [for (k = [0 : 4]) let (th = 36 + 72 * k, u = a0 * cos(th) + b0 * sin(th))
           unit(v * cos(al) + u * sin(al)) * R];
    intersection() {
        hull() for (p = pts) translate([p[0], p[1], 0]) cylinder(d = 0.01, h = R + 3, $fn = 4);
        difference() { sphere(R + 3); sphere(R - 1.2); }
    }
}
module ball_half() {
    difference() {
        intersection() { sphere(R); translate([-R - 1, -R - 1, 0]) cube([2 * R + 2, 2 * R + 2, R + 1]); }
        for (v = verts) if (v[2] > -0.1) panel(v);
        for (a = [0, 120, 240]) rotate(a) translate([R * 0.45, 0, -0.1]) cylinder(d = 6.4, h = 5.1);   // pin holes (on the bed face)
    }
}
module ball_pins() { for (a = [0, 120, 240]) rotate(a) translate([8, 0, 0]) cylinder(d = 6, h = 9); }

// side view of a football cleat (x = length, y = height). Studs and 2 tabs under the sole.
boot_pts = [[3, 6], [1, 22], [3, 44], [6, 60], [20, 63], [32, 57], [44, 65], [50, 58], [62, 44], [82, 32], [100, 26],
            [116, 20], [122, 13], [118, 6]];
module boot() {
    // modelled lying on its side (as it prints): the 16 mm thickness is along z; stand it up on the plinth
    translate([-62, 0, 0]) linear_extrude(bt) union() {
        polygon(boot_pts);
        for (x = [12, 26, 82, 96, 108]) translate([x, 1]) square([6, 6]);     // studs
        for (x = [44, 62]) translate([x, 1]) square([8, 6]);                  // tabs that plug into the plinth
    }
}
module plaque_text() {
    if (label != "") translate([0, 0, 0]) linear_extrude(1.2)
        text(label, size = 9, font = "DejaVu Sans:style=Bold", halign = "center", valign = "center");
}
module base_ball() {
    W = 120; D = 100; H = 16;
    difference() {
        hull() {
            translate([-W / 2 + 6, -D / 2 + 6, 0]) cylinder(r = 6, h = H - 3);
            translate([ W / 2 - 6, -D / 2 + 6, 0]) cylinder(r = 6, h = H - 3);
            translate([-W / 2 + 6,  D / 2 - 6, 0]) cylinder(r = 6, h = H - 3);
            translate([ W / 2 - 6,  D / 2 - 6, 0]) cylinder(r = 6, h = H - 3);
            translate([-W / 2 + 9, -D / 2 + 9, H - 0.01]) cube([W - 18, D - 18, 0.01]);
        }
        translate([0, 8, H + R - 5]) sphere(R + 0.5);                  // dish: the ball sits 5 mm deep
        translate([0, -33, H - 0.6]) plaque_text();
    }
}
module base_boot() {
    W = 140; D = 60; H = 16;
    difference() {
        hull() {
            translate([-W / 2 + 6, -D / 2 + 6, 0]) cylinder(r = 6, h = H - 3);
            translate([ W / 2 - 6, -D / 2 + 6, 0]) cylinder(r = 6, h = H - 3);
            translate([-W / 2 + 6,  D / 2 - 6, 0]) cylinder(r = 6, h = H - 3);
            translate([ W / 2 - 6,  D / 2 - 6, 0]) cylinder(r = 6, h = H - 3);
            translate([-W / 2 + 9, -D / 2 + 9, H - 0.01]) cube([W - 18, D - 18, 0.01]);
        }
        for (x = [44, 62]) translate([x - 62 - 0.2, 6 - bt / 2 - 0.3, H - 7]) cube([8.4, bt + 0.6, 8]);   // slots for the 2 boot tabs
        translate([0, -D / 2 + 11, H - 0.6]) plaque_text();
    }
}
if (part == "ball_half") ball_half();
if (part == "ball_pins") ball_pins();
if (part == "boot") boot();
if (part == "base_ball") base_ball();
if (part == "base_boot") base_boot();
