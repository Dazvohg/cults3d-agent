// Passive radiation shield (Stevenson-style louver stack) for weather-station sensors - original design (Brian Sacco)
// Stack of identical louver plates on three M4 threaded rods, printed as separate parts.
// Every part prints as oriented with no supports: cones lean at 40 degrees from vertical, rims sit flat on the bed.
part  = "plate";   // "plate", "cap", "spacers", "base_dht22", "base_probe"
rim_r = 58;        // outer radius (OD 116 mm)
flat  = 9;         // flat rim width that carries the rod holes
cone_a = 50;       // cone angle from horizontal (40 deg from vertical: self-supporting)
t     = 2.4;       // plate thickness measured perpendicular to the cone
r_in  = 20;        // chimney radius where the sensor sits (plate hole, 40 mm)
rod_d = 4.5;       // M4 threaded rod clearance hole
pitch = 14;        // plate to plate spacing along the rods
base_t = 4;
$fn = 120;

rod_r = rim_r - flat / 2;                     // radius of the three rod holes
tv    = t / cos(cone_a);                      // vertical thickness of the cone shell
sl    = tan(cone_a);
r0    = rim_r - flat;                         // where the flat rim ends and the cone starts
spacer_len = pitch - tv;

module rods(h) { for (a = [0, 120, 240]) rotate(a) translate([rod_r, 0, -1]) cylinder(d = rod_d, h = h + 2, $fn = 32); }

module plate() {
    difference() {
        rotate_extrude() polygon([[rim_r, 0], [r0, 0], [r_in, (r0 - r_in) * sl], [r_in, (r0 - r_in) * sl + tv], [r0, tv], [rim_r, tv]]);
        rods(tv);
    }
}
module cap() {
    difference() {
        rotate_extrude() polygon([[rim_r, 0], [r0, 0], [0, r0 * sl], [0, r0 * sl + tv], [r0, tv], [rim_r, tv]]);
        rods(tv);
    }
}
module spacers() {   // 18 sleeves (3 rods x 6 gaps) standing on the bed
    for (i = [0 : 5], j = [0 : 2]) translate([i * 11, j * 11, 0]) difference() {
        cylinder(d = 8, h = spacer_len, $fn = 48);
        translate([0, 0, -1]) cylinder(d = rod_d, h = spacer_len + 2, $fn = 32);
    }
}
module base(kind) {
    difference() {
        union() {
            cylinder(r = rim_r, h = base_t);
            cylinder(r = 22, h = 10);                       // central pad for the sensor
        }
        rods(base_t);
        if (kind == "dht22") {
            // DHT22 / AM2302 body 15.1 x 25 x 7.7 mm + 0.6 mm clearance; 6 mm cable hole down through the floor at the pin end
            translate([-15.7 / 2, -25.6 / 2, 1.8]) cube([15.7, 25.6, 10]);
            translate([0, 25.6 / 2 - 4, -1]) cylinder(d = 6, h = 5, $fn = 32);
        } else {
            translate([0, 0, -1]) cylinder(d = 6.4, h = 12);   // 6 mm stainless DS18B20 probe + 0.4 mm
        }
    }
}

if (part == "plate") plate();
else if (part == "cap") cap();
else if (part == "spacers") spacers();
else if (part == "base_dht22") base("dht22");
else base("probe");
