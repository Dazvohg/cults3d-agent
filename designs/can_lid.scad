// Beverage can lid / cover - original parametric design (Brian Sacco)
// Prints upside-down (flat top on the bed, skirt pointing up): no supports.
// Fits the double seam of standard aluminium can ends: 202 = 2 2/16" (54.0 mm), 200 = 2 0/16" (50.8 mm), 204 = 2 4/16" (57.2 mm).
rim_d   = 54.0;   // nominal can-end diameter (mm)
clr     = 0.8;    // FDM clearance on the diameter
skirt_h = 12;     // skirt height
wall    = 1.6;
top_t   = 2.0;    // disc thickness
straw_d = 0;      // 0 = solid lid; 8 = straw hole (fits 6 mm straws)
bead    = 0.6;    // snap bead protrusion (45 deg above and below); catches just under the can seam
$fn = 96;

id = rim_d + clr;
od = id + 2 * wall;
bz = top_t + 3.2;   // bead sits just under the can seam (seam height ~3 mm)

difference() {
    hull() {   // outer body with a 0.8 mm 45-degree chamfer on the bed edge
        cylinder(d = od - 1.6, h = 0.01);
        translate([0, 0, 0.8]) cylinder(d = od, h = 0.01);
        translate([0, 0, top_t + skirt_h - 0.01]) cylinder(d = od, h = 0.01);
    }
    translate([0, 0, top_t]) cylinder(d = id, h = skirt_h + 1);                                  // cavity
    translate([0, 0, top_t + skirt_h - 0.8]) cylinder(d1 = id, d2 = id + 1.6, h = 0.81);         // lead-in chamfer
    if (straw_d > 0) translate([0, 0, -1]) cylinder(d = straw_d, h = top_t + 2);
}
// snap bead: ring with 45 deg slopes above and below (self-supporting), embedded 0.5 mm into the wall
translate([0, 0, bz]) rotate_extrude() polygon([
    [id / 2 + 0.5, 0], [id / 2, 0], [id / 2 - bead, bead],
    [id / 2 - bead, bead + 0.4], [id / 2, 2 * bead + 0.4], [id / 2 + 0.5, 2 * bead + 0.4]]);
