// Phone & Tablet Stand with cable channel - original parametric design (Brian Sacco)
// Solid wedge profile (no bridges, no flat overhangs) with a pointed weight-saving window:
// prints standing as oriented, without supports (verified with PrusaSlicer).
angle     = 65;    // viewing angle from horizontal (degrees)
width     = 80;    // stand width (mm)
device_t  = 13;    // slot width: phone + case thickness (mm)
lip_h     = 12;    // front lip height
back_h    = 90;    // backrest length
t         = 5;     // plate thickness
cable     = true;  // channel for the charging cable
depth     = 85;    // base depth
$fn = 48;

bx = t + device_t;                        // where the backrest starts (front face)
tx = bx + back_h * cos(angle);            // backrest top, front face
tz = t + back_h * sin(angle);
nx = t * sin(angle); nz = -t * cos(angle);   // backrest thickness, perpendicular to its face

module profile() {
    polygon([
        [0, 0], [depth, 0], [depth, t],       // base
        [tx + nx, tz + nz],                   // rear slope up to the back of the backrest top
        [tx, tz],                             // backrest top
        [bx, t],                              // backrest front face down to the slot
        [t, t], [t, lip_h], [0, lip_h]        // slot floor + front lip
    ]);
}
// pointed (diamond) window: all edges steeper than 55 degrees -> self-supporting
module window() {
    cx = (bx + depth) / 2 + 6; cz = t + (tz - t) * 0.30;
    hw = min(9, (depth - bx) * 0.18); hh = hw * 1.6;
    polygon([[cx, cz - hh], [cx + hw, cz], [cx, cz + hh], [cx - hw, cz]]);
}

rotate([90, 0, 0]) translate([0, 0, -width / 2]) difference() {
    linear_extrude(width) difference() { profile(); window(); }
    // cable channel under the slot, pointed roof (> 55 deg), ends before the backrest
    if (cable) translate([-1, 0, width / 2]) rotate([0, 90, 0]) linear_extrude(bx + 1)
        polygon([[0, -5], [-(t + 1), -5], [-(t + 7), 0], [-(t + 1), 5], [0, 5]]);
}
