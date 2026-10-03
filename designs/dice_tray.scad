// Hexagonal Dice Rolling Tray with dice storage - original parametric design (Brian Sacco)
// Storage sized from real polyhedral sets: d6 16-18 mm, d20 23-29 mm (largest die of a set).
// Slots are 26 mm square (fits standard acrylic sets' d20 and every smaller die) and sit INSIDE
// the tray against three alternate walls, so a full 7-dice set always has a home and the tray
// keeps a compact hexagonal footprint that fits the print bed.
size      = 160;   // flat-to-flat width (mm)
height    = 28;
wall      = 3;
floor_t   = 2.4;
storage   = true;  // dice slots
die       = 26;    // slot size (mm): 26 = standard polyhedral d20; 18 = d6-only
storage_mode = "inside"; // "inside": slots inside, on 3 alternate walls | "outside": pockets outside 2 opposite walls
felt      = 1.0;   // recess depth for a felt/neoprene insert (0 = none)
$fn = 6;

corner = size / cos(30);            // corner-to-corner
flat_len = corner / 2;              // length of one side of the hexagon
pitch = die + 2;
inner_flat = (size - 2*wall) / cos(30) / 2;   // inner side length
slot_sides = storage_mode == "inside" ? 3 : 2;
slots = storage_mode == "inside"
    ? floor((inner_flat - 2*(die + 4)*tan(30) - 4) / pitch)     // keeps clear of the inner corners
    : floor((flat_len - 6) / pitch);                            // outside pocket fits the flat
echo(str("DICE_TRAY slots_per_side=", slots, " total=", storage ? slots * slot_sides : 0));

module hex(d, h) { cylinder(d=d, h=h, $fn=6); }
// one storage block inside the tray, against the +Y wall ($fn=6 cylinders have vertices on X,
// so the flats face +/-Y); it overlaps the wall so everything fuses
inner_r = size/2 - wall;                       // inner apothem
y0 = storage_mode == "inside" ? inner_r - die - 4 : size/2 - wall;     // block start (towards +Y)
module block() {
    translate([-(slots*pitch)/2 - 2, y0, 0]) cube([slots*pitch + 4, die + 4 + wall/2, height]);
}
module slot_cuts() {
    for (i=[0:slots-1])
        translate([-(slots*pitch)/2 + i*pitch + 1, y0 + 2, floor_t]) cube([die, die, height]);
}
side_angles = storage_mode == "inside" ? [0, 120, 240] : [0, 180];

difference() {
    union() {
        difference() {
            hull() { hex(corner - 4, 0.01); translate([0,0,2]) hex(corner, height - 2); }
            translate([0,0,floor_t]) hex(corner - 2*wall/cos(30), height);
            if (felt > 0) translate([0,0,floor_t - felt]) hex(corner - 2*wall/cos(30) - 6, felt + 0.01);
        }
        // storage blocks are added after the tray is hollowed, so they stay solid
        if (storage) for (k=[0:slot_sides-1]) rotate(side_angles[k]) intersection() {
            block();
            if (storage_mode == "inside") hex(corner - 0.5, height); else translate([-500, -500, 0]) cube([1000, 1000, height]);
        }
    }
    if (storage) for (k=[0:slot_sides-1]) rotate(side_angles[k]) slot_cuts();
}
