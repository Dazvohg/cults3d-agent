// Desk Cable Clip - original parametric design (Brian Sacco)
// Flat-backed clip for double-sided tape; snap-in slots hold cables.
slots        = 3;     // number of cable slots
cable_d      = 6.0;   // cable diameter (mm). Common: 3.5 phone cables, 4.5 braided USB-C, 6 laptop, 8 HDMI/monitor
fit          = 0.2;   // extra diameter so the cable can slide
opening      = 0.72;  // mouth width as fraction of cable_d (snap fit)
wall         = 2.0;
depth        = 12;    // clip length along the cable (mm)
base_t       = 2.4;   // base plate thickness (mm)
gap          = 3;     // spacing between slots
$fn = 64;

pitch = cable_d + 2*wall + gap - wall;
width = slots * pitch + wall + 2;
ring_h = base_t + cable_d/2 + 0.5; // cable centre height

module body() {
    // base plate with rounded ends
    hull() {
        translate([1.5,0,0]) cube([width-3, depth, base_t]);
        translate([0,0,0]) cube([width, depth, 0.01]);
    }
    for (i=[0:slots-1]) {
        x = wall + 1 + cable_d/2 + wall/2 + i*pitch;
        translate([x,0,ring_h]) rotate([-90,0,0])
            cylinder(d = cable_d + 2*wall, h = depth);
        // fill between ring and base so it prints without supports
        translate([x - (cable_d/2+wall)*0.7, 0, 0])
            cube([(cable_d/2+wall)*1.4, depth, ring_h]);
    }
}
difference() {
    body();
    for (i=[0:slots-1]) {
        x = wall + 1 + cable_d/2 + wall/2 + i*pitch;
        translate([x,-1,ring_h]) rotate([-90,0,0]) cylinder(d = (cable_d + fit) / cos(180/$fn), h = depth+2);
        // snap mouth on top
        translate([x - cable_d*opening/2, -1, ring_h]) cube([cable_d*opening, depth+2, cable_d/2 + wall + 1]);   // always cuts through the top of the ring
    }
}
