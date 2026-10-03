// Parametric Movement Tray for tabletop wargames - original design (Brian Sacco)
// Holds round-based miniatures in a grid; optional magnet pockets under each base.
cols        = 5;      // bases per row
rows        = 2;      // rows
base_d      = 25;     // round base diameter (mm). Standard sizes: 25, 28.5, 32, 40, 50
clearance   = 0.6;    // extra diameter so bases drop in easily
spacing     = 1.2;    // gap between neighbouring bases
floor_t     = 1.6;    // tray floor thickness
recess      = 1.8;    // how deep each base sits
border      = 3.0;    // rim around the grid
magnet_d    = 0;      // 0 = no magnets; magnet size + 0.3 (5.3 for 5x2 mm, 6.3 for 6x2 mm)
magnet_h    = 2.2;
stagger     = false;  // true = skirmish (offset) formation
$fn = 48;

// magnet versions get a thicker floor so the pocket never pierces the bottom
floor_r = magnet_d > 0 ? max(floor_t, magnet_h + 0.8) : floor_t;
hole  = base_d + clearance;
pitch = hole + spacing;
W = cols * pitch - spacing + 2*border + (stagger ? pitch/2 : 0);
D = rows * pitch - spacing + 2*border;
H = floor_r + recess;

function pos(c, r) = [border + hole/2 + c*pitch + ((stagger && r % 2 == 1) ? pitch/2 : 0),
                      border + hole/2 + r*pitch];

module rounded_plate(w, d, h, r=3) {
    hull() for (x=[r, w-r], y=[r, d-r]) translate([x, y, 0]) cylinder(r=r, h=h);
}

difference() {
    // body with a 45-degree chamfered top edge so it looks finished on the table
    hull() {
        rounded_plate(W, D, H - 0.8);
        translate([0.8, 0.8, 0]) rounded_plate(W - 1.6, D - 1.6, H);
    }
    for (c=[0:cols-1], r=[0:rows-1]) translate(pos(c, r)) {
        translate([0, 0, floor_r]) cylinder(d=hole / cos(180/$fn), h=H);   // facet-compensated: true min width = hole
        // lead-in chamfer at the top of every pocket
        translate([0, 0, H - 0.6]) cylinder(d1=hole, d2=hole + 1.2, h=0.61);
        if (magnet_d > 0) translate([0, 0, floor_r - magnet_h])
            cylinder(d=magnet_d / cos(180/$fn), h=magnet_h);
    }
    // finger notch on both short sides for easy lifting
    for (x=[0, W]) translate([x, D/2, H]) scale([1, 2.2, 1]) sphere(r=5);
}
