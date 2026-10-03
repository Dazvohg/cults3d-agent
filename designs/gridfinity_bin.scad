// Gridfinity-compatible storage bin - original parametric model (Brian Sacco)
// Independent implementation of the open Gridfinity standard (Zack Freedman):
//   grid 42 mm, bin footprint 41.5 mm (0.25 mm clearance per side), height unit 7 mm,
//   total height = 7 mm x units (base included) + 4.4 mm stacking lip,
//   foot profile from the bottom: 0.8 mm @45°, 1.8 mm vertical, 2.15 mm @45° (4.75 mm),
//   foot outline 35.6 -> 37.2 -> 41.5 mm, corner radii 0.8 / 1.6 / 3.75 mm.
gx        = 2;      // grid units in X
gy        = 1;      // grid units in Y
gz        = 3;      // height units (7 mm each, base included)
dividers  = 0;      // internal dividers along X
label     = true;   // label shelf on the back wall
scoop     = true;   // curved front floor to scoop small parts
wall      = 1.2;
insert    = "none"; // "none", "bits" (1/4" hex bits), "aa", "aaa" (batteries)
$fn = 48;

pitch = 42; clr = 0.5; r_out = 3.75;
W = gx*pitch - clr; D = gy*pitch - clr;
TOP = 7 * gz;              // top of the walls (lip starts here)
base_h = 5;                // 4.75 mm foot profile + 0.25 mm straight
floor_z = 7;               // inner floor: usable depth = (units - 1) x 7 mm, as in the standard
LIP = 4.4;

module rrect(w, d, h, r) { linear_extrude(h) offset(r) offset(-r) square([w, d], center=true); }
module ring(w, d, r, z) { translate([0, 0, z]) rrect(w, d, 0.01, r); }

module foot() {
    hull() { ring(35.6, 35.6, 0.8, 0);   ring(37.2, 37.2, 1.6, 0.8); }
    hull() { ring(37.2, 37.2, 1.6, 0.8); ring(37.2, 37.2, 1.6, 2.6); }
    hull() { ring(37.2, 37.2, 1.6, 2.6); ring(41.5, 41.5, r_out, 4.75); }
    translate([0, 0, 4.75]) rrect(41.5, 41.5, base_h - 4.75 + 0.01, r_out);
}

// Stacking lip: inner surface mirrors the baseplate profile so the next bin's feet seat in it.
// Insets from the outer wall, top to bottom: 0.5 flat, 1.9 @45°, 1.8 vertical, 0.7 @45°.
module lip_cut() {
    a0 = 0.5; a1 = a0 + 1.9; a2 = a1 + 0.7;
    r = function(a) max(0.4, r_out - a);
    hull() { ring(W-2*a0, D-2*a0, r(a0), TOP+LIP+0.1); ring(W-2*a0, D-2*a0, r(a0), TOP+LIP); ring(W-2*a1, D-2*a1, r(a1), TOP+LIP-1.9); }
    hull() { ring(W-2*a1, D-2*a1, r(a1), TOP+LIP-1.9); ring(W-2*a1, D-2*a1, r(a1), TOP+LIP-3.7); }
    hull() { ring(W-2*a1, D-2*a1, r(a1), TOP+LIP-3.7); ring(W-2*a2, D-2*a2, r(a2), TOP); }
    // 45° chamfer under the lip ledge back out to the inner wall (self-supporting)
    hull() { ring(W-2*a2, D-2*a2, r(a2), TOP); ring(W-2*wall, D-2*wall, r_out-wall, TOP-(a2-wall)); }
}

union() {
    difference() {
        union() {
            for (i=[0:gx-1], j=[0:gy-1]) translate([(i-(gx-1)/2)*pitch, (j-(gy-1)/2)*pitch, 0]) foot();
            // multi-unit: the solid body starts where the flares below have closed every gap
            translate([0, 0, gx * gy > 1 ? 6.75 : base_h]) rrect(W, D, TOP + LIP - (gx * gy > 1 ? 6.75 : base_h), r_out);
            // between feet (multi-unit bins): ~54° flare above the foot top (z 4.75, higher than the
            // baseplate ridge at 4.65) so the gaps close with pointed roofs, steeper than 45°, never a flat ceiling
            if (gx * gy > 1) intersection() {
                rrect(W, D, floor_z, r_out);
                for (i=[0:gx-1], j=[0:gy-1]) translate([(i-(gx-1)/2)*pitch, (j-(gy-1)/2)*pitch, 0])
                    hull() { ring(41.5, 41.5, r_out, 4.75); ring(44.4, 44.4, r_out, 6.75); }   // 1.45 out over 2 up (~54°)
            }
        }
        // cavity up to the lip, then the lip profile
        translate([0, 0, floor_z]) rrect(W-2*wall, D-2*wall, TOP - floor_z - (3.1 - wall) + 0.01, r_out-wall);  // meets the 45° chamfer under the lip (a2 = 3.1): no flat ceiling
        lip_cut();
    }
    // scoop, dividers, label shelf (fused to walls and floor)
    intersection() {
        translate([0, 0, floor_z - 0.6]) rrect(W-2*wall+1, D-2*wall+1, TOP - floor_z, r_out-wall);
        union() {
            if (scoop) translate([0, -(D/2-wall), floor_z]) difference() {
                translate([-W/2, -0.6, -0.6]) cube([W, 9.6, 9.6]);
                translate([-W/2-1, 9.4, 9.4]) rotate([0,90,0]) cylinder(r=9.4, h=W+2, $fn=60);
            }
            if (dividers > 0) for (k=[1:dividers])
                translate([-W/2 + k*W/(dividers+1) - wall/2, -D/2, floor_z - 0.6]) cube([wall, D, (TOP - floor_z)*0.85]);
            if (label) translate([-W/2, D/2 - wall - 12, TOP - 4]) hull() {
                cube([W, 12, 1.2]);
                translate([0, 12, -14]) cube([W, 0.5, 1]);   // underside ~50°, bottom edge buried in the back wall: self-supporting
            }
        }
    }
    // ---- specialised inserts: a block with a grid of holes sized to the item's standard
    //   1/4" hex bit: 6.35 mm across flats -> 6.75 mm hole (0.4 mm FDM clearance)
    //   AA (IEC LR6, max Ø 14.5 mm) -> 15.1 mm   |   AAA (IEC LR03, max Ø 10.5 mm) -> 11.1 mm
    if (insert != "none") {
        af    = 6.35 + 0.40;
        hole  = insert == "bits" ? af / cos(30) : insert == "aa" ? 15.1 : 11.1;
        pitch_h = insert == "bits" ? 10 : insert == "aa" ? 17 : 13;
        blk_h = insert == "bits" ? 12 : insert == "aa" ? 22 : 18;
        depth = blk_h - 1.6;
        nx = floor((W - 2*wall - 4) / pitch_h); ny = floor((D - 2*wall - 4) / pitch_h);
        echo(str("HOLES=", nx * ny));
        difference() {
            translate([0, 0, floor_z - 0.6]) rrect(W-2*wall+1, D-2*wall+1, blk_h, r_out-wall);
            for (i=[0:nx-1], j=[0:ny-1])
                translate([(i-(nx-1)/2)*pitch_h, (j-(ny-1)/2)*pitch_h, floor_z - 0.6 + blk_h - depth])
                    rotate([0, 0, 30]) cylinder(d=hole, h=depth+1, $fn = insert == "bits" ? 6 : 64);
        }
    }
}
