// Compact passive radiation shield for I2C breakout boards (BME280, BMP280, SHT31, SHT4x, AHT20) - original design (Brian Sacco)
// 3 louver plates + cap on three M3 threaded rods. Every part prints as oriented, no supports (cones 44 deg from vertical).
part   = "plate";   // "plate", "cap", "spacers", "base_s", "base_m"
rim_r  = 40;        // OD 80 mm
flat   = 7;
cone_a = 46;        // cone angle from horizontal (44 deg from vertical: self-supporting)
t      = 2.4;
r_in   = 14;        // chimney radius (28 mm hole)
rod_d  = 3.4;       // M3 clearance
pitch  = 10;
base_t = 4;
$fn = 100;

rod_r = rim_r - flat / 2;
tv    = t / cos(cone_a);
sl    = tan(cone_a);
r0    = rim_r - flat;
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
module spacers() {   // 12 sleeves (3 rods x 4 gaps)
    for (i = [0 : 3], j = [0 : 2]) translate([i * 9, j * 9, 0]) difference() {
        cylinder(d = 7, h = spacer_len, $fn = 48);
        translate([0, 0, -1]) cylinder(d = rod_d, h = spacer_len + 2, $fn = 32);
    }
}
// board pocket w x l (+clearance), two zip-tie slots, cable slot through the floor
module base(w, l) {
    difference() {
        union() {
            cylinder(r = rim_r, h = base_t);
            translate([-(w + 8) / 2, -(l + 8) / 2, 0]) cube([w + 8, l + 8, 9]);
        }
        rods(base_t);
        translate([-w / 2, -l / 2, 2]) cube([w, l, 10]);                    // board pocket (floor 2 mm)
        translate([-4, l / 2 - 5, -1]) cube([8, 6, 12]);                     // cable slot, open to the top (no bridge)
        for (s = [-1, 1]) translate([s * (w / 2 + 2.4) - 1.2, -3, -1]) cube([2.4, 6, 12]); // zip-tie slits (2.4 wide)
    }
}
if (part == "plate") plate();
else if (part == "cap") cap();
else if (part == "spacers") spacers();
else if (part == "base_s") base(13.5, 18);    // GY-BME280 / BMP280 / AHT20 class boards
else if (part == "base_m") base(18.5, 26);    // Adafruit-size SHT31 / BME280 boards
