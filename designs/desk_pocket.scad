// Desk-side pocket organizer: adhesive-tape or screw mount, pocket open at the top - original design (Brian Sacco)
// Prints standing: the pocket floor sits on the bed and the mounting plate rises vertically. No overhangs, no supports.
pocket_w = 82;     // inner width of the pocket along the desk (mm)
pocket_d = 13;     // inner depth, away from the desk: 13 = phone + normal case, 18 = rugged case
pocket_h = 60;     // pocket wall height
wall     = 1.6;
floor_t  = 2.4;
plate_t  = 3.2;    // mounting plate thickness
screw_d  = 4.5;    // screw clearance hole (for a 4 mm wood or drywall screw)
$fn = 48;

w_out  = pocket_w + 2 * wall;
d_out  = pocket_d + 2 * wall;
plate_h = pocket_h + 26;          // 26 mm of plate above the pocket for the two screws
hole_z  = pocket_h + 13;
hole_x  = w_out / 2 - 9;

module tear(d) {   // circle with a 45 degree pointed top
    circle(d = d);
    polygon([[-d / 2 * 0.7071, d / 2 * 0.7071], [0, d / 2 * 1.4142], [d / 2 * 0.7071, d / 2 * 0.7071]]);
}

difference() {
    union() {
        // mounting plate (the rear face is flat for adhesive foam tape, y = 0)
        translate([-w_out / 2, 0, 0]) cube([w_out, plate_t, plate_h]);
        // pocket
        translate([-w_out / 2, plate_t - 0.01, 0]) cube([w_out, d_out + 0.01, pocket_h]);
    }
    // pocket cavity
    translate([-pocket_w / 2, plate_t + wall, floor_t]) cube([pocket_w, pocket_d, pocket_h]);
    // two screw holes with a counterbore for the head; teardrop shaped (pointed top at 45 degrees) so no supports
    for (s = [-1, 1]) {
        translate([s * hole_x, plate_t + 1, hole_z]) rotate([90, 0, 0]) linear_extrude(plate_t + 2) tear(screw_d);
        translate([s * hole_x, plate_t + 0.01, hole_z]) rotate([90, 0, 0]) linear_extrude(2.2) tear(screw_d + 4.5);
    }
}
