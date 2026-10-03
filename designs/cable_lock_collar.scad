// EV / cable lock collar - two identical halves that clamp a cable, with two padlock eyes. Original design (Brian Sacco)
// A visible deterrent only (plastic): use it with a steel chain or padlock. It is NOT a security lock.
// Print ONE half per run (flat, outer side up); print it twice. Assemble with 2 x M5 bolt + nut (not included).
pair  = 1;       // 1 = both halves on one plate (print once), 0 = a single half
cable = 18;      // cable outer diameter in mm (measure yours with calipers or a string)
L     = 40;      // collar length
squeeze = 0.6;   // bore = cable - squeeze, so the halves grip the jacket
$fn = 96;

rc  = (cable - squeeze) / 2;
R   = max(rc * 1.4142 + 3, rc + 6);
ear = 8;                 // ear plate thickness
eye = 13;                // padlock / chain hole
bx  = R + 8;             // bolt distance from the axis

module profile() {
    difference() {
        union() {
            intersection() { circle(r = R); translate([-R, 0]) square([2 * R, R]); }
            translate([-(R + 16), 0]) square([2 * (R + 16), ear]);                     // both ears
            hull() { translate([R + 8, 0]) square([1, ear]); translate([R + 31, 0]) square([1, ear]); }   // long ear with eye
        }
        // bore: circle with a 45 degree peak so it prints without support
        circle(r = rc);
        polygon([[-rc * 0.7071, rc * 0.7071], [0, rc * 1.4142], [rc * 0.7071, rc * 0.7071]]);
    }
}
module half() {
    difference() {
        translate([0, L, 0]) rotate([90, 0, 0]) linear_extrude(L) intersection() {
            profile();
            translate([-200, 0]) square([400, 200]);          // keep z >= 0
        }
        // left ear: bolt hole + nut pocket (hex, 8.2 across flats)
        translate([-bx, L/2, -1]) cylinder(d = 5.5, h = ear + 2);
        translate([-bx, L/2, ear - 4.2]) cylinder(d = 8.2 / cos(30), h = 5, $fn = 6);
        // right ear: bolt hole + head counterbore
        translate([bx, L/2, -1]) cylinder(d = 5.5, h = ear + 2);
        translate([bx, L/2, ear - 3.5]) cylinder(d = 9.5, h = 5);
        // padlock / chain eye in the long ear
        translate([R + 22, L/2, -1]) cylinder(d = eye, h = ear + 2);
    }
}
half();
if (pair == 1) translate([0, L + 8, 0]) half();
