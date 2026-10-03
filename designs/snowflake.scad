// Procedural Snowflake Ornament - every seed makes a different original 6-fold snowflake (Brian Sacco)
seed    = 1;
size    = 80;     // tip-to-tip diameter (mm)
thick   = 2.4;
arm_w   = 3.2;
loop    = true;   // hanging loop on top

r = size / 2;
rnd = rands(0, 1, 40, seed);
function R(i) = rnd[i % 40];

module arm() {
    // main spine
    translate([0, -arm_w/2]) square([r - arm_w/2, arm_w]);
    translate([r - arm_w/2, 0]) circle(d=arm_w, $fn=20);
    // 2-4 pairs of side branches, lengths and angles driven by the seed
    n = 2 + floor(R(0) * 3);
    for (k = [0 : n - 1]) {
        pos = r * (0.28 + 0.62 * (k + R(k + 1) * 0.5) / n);
        len = r * (0.18 + 0.30 * R(k + 5)) * (1 - pos / r * 0.55);
        ang = 38 + 30 * R(k + 9);
        w   = arm_w * (0.55 + 0.35 * R(k + 13));
        for (s = [-1, 1]) translate([pos, 0]) rotate(s * ang) {
            translate([0, -w/2]) square([len, w]);
            translate([len, 0]) circle(d=w, $fn=16);
            // occasional diamond tip
            if (R(k + 17) > 0.6) translate([len, 0]) rotate(45) square(w * 1.6, center=true);
        }
    }
    // optional crystal plate near the tip
    if (R(30) > 0.5) translate([r * 0.78, 0]) rotate(45) square(arm_w * 2.2, center=true);
}
linear_extrude(thick) {
    for (i = [0:5]) rotate(i * 60) arm();
    circle(d = arm_w * (2.6 + 2 * R(31)), $fn = 6);
    // hanging loop on the tip of the arm that points along +X (arms are at 0, 60, 120... deg)
    if (loop) translate([r + 3, 0]) difference() { circle(d=8, $fn=32); circle(d=4.2, $fn=32); }
    if (loop) translate([r - 3, -arm_w/2]) square([4.5, arm_w]);
}
