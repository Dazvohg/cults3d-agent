// Modular dice tower with zig-zag ramps and a rolling tray - original parametric design.
// Chamber is 70 mm wide so a d20 (up to 29 mm) always passes the 31 mm gap at the end of every ramp.
// Ramps slope at 45 degrees with a parallel underside, so the tower prints standing up with no supports.
ramps   = 3;       // number of ramps (2 = short tower, 3 = tall tower)
cx      = 70;      // chamber width (mm)
cy      = 36;      // chamber depth (mm)
wall    = 3;
gap     = 31;      // clear gap left at the end of each ramp (mm)
rt      = 3;       // vertical ramp thickness (mm)
pitch   = 46;      // vertical distance between ramps (mm)
win_h   = 50;      // exit window height at the peak (mm), floor to apex
tray_l  = 70;      // rolling tray length in front of the tower (mm)
rim     = 4;       // tray rim height (mm)
floor_t = 3;

L  = cx - gap;                         // ramp horizontal length (45 deg drop = L)
z1 = floor_t + 34 + L - 14;         // top of the lowest ramp at its wall
H  = z1 + (ramps - 1) * pitch + 38;    // tower height
ow = cx + 2*wall; od = cy + 2*wall;
echo(str("DICE_TOWER outer=", ow, "x", od + tray_l, "x", H));

module ramp(z, from_left) {
    // polygon in XZ, extruded along Y across the chamber (overlaps the side walls so it fuses)
    xs = from_left ? -cx/2 - 0.5 : cx/2 + 0.5;
    dx = from_left ? 1 : -1;
    translate([0, cy/2 + 0.5, 0]) rotate([90, 0, 0]) linear_extrude(height = cy + 1)
        polygon([[xs, z], [xs + dx*(L + 0.5), z - L - 0.5], [xs + dx*(L + 0.5), z - L - 0.5 - rt*1.0], [xs, z - rt]]);
}

difference() {
    union() {
        // tower body
        translate([-ow/2, -od/2, 0]) cube([ow, od, H]);
        // rolling tray in front (towards -Y)
        translate([-ow/2, -od/2 - tray_l, 0]) cube([ow, tray_l + 1, floor_t + rim]);
    }
    // chamber
    translate([-cx/2, -cy/2, floor_t]) cube([cx, cy, H]);
    // exit window through the front wall
    // gable-shaped (45 deg) so the lintel needs no bridging
    translate([0, -od/2 + wall + 1, floor_t]) rotate([90, 0, 0]) linear_extrude(height = wall + 2)
        polygon([[-(cx/2 - 4), 0], [cx/2 - 4, 0], [cx/2 - 4, win_h - (cx/2 - 4)], [0, win_h], [-(cx/2 - 4), win_h - (cx/2 - 4)]]);
    // tray pocket
    translate([-ow/2 + wall, -od/2 - tray_l + wall, floor_t]) cube([ow - 2*wall, tray_l + 1, rim + 1]);
}
for (i = [0 : ramps - 1])
    ramp(z1 + i*pitch, i % 2 == 0);
