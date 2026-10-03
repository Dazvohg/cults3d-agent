// Modular Hex Desk Organizer - original parametric design
// Author: Brian Sacco. License: see listing.
// Each cell is a hexagonal cup; cups sit side by side in a honeycomb cluster.

cells       = 5;      // 1..7 cells in a honeycomb cluster
cell_flat   = 60;     // flat-to-flat inner width of each cell (mm)
wall        = 2.0;    // wall thickness (mm)
base        = 2.0;    // floor thickness (mm)
heights     = [100, 80, 60, 90, 70, 110, 50]; // height of each cell (mm)
chamfer     = 1.0;    // bottom edge chamfer to avoid elephant foot
$fn = 6;

// axial offsets for a 7-cell honeycomb (center + ring)
function pitch() = cell_flat + wall;
offsets = [[0,0],[1,0],[0.5,0.866],[-0.5,0.866],[-1,0],[-0.5,-0.866],[0.5,-0.866]];

module hex(flat, h) {
    // cylinder with $fn=6 is measured corner-to-corner; convert flat->corner
    cylinder(d = flat / cos(30), h = h, $fn = 6);
}

module outer(h) {
    hull() {
        hex(cell_flat + 2*wall - 2*chamfer, h);
        translate([0,0,chamfer]) hex(cell_flat + 2*wall, h - chamfer);
    }
}

// Union every outer shell first, then carve every cavity: shared walls stay manifold.
n = min(cells, 7);
difference() {
    union() for (i = [0 : n-1])
        translate([offsets[i][0]*pitch(), offsets[i][1]*pitch(), 0]) rotate([0,0,30]) outer(heights[i]);
    for (i = [0 : n-1])
        translate([offsets[i][0]*pitch(), offsets[i][1]*pitch(), base]) rotate([0,0,30]) hex(cell_flat, heights[i] + 1);
}
