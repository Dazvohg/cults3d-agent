// Modular desk caddy: pen cups, phone slot, sticky-note pad, business-card slot - original design (Brian Sacco)
// One walled tray; every compartment is a rounded rectangle carved into a shared outer shell.
// Open at the top, solid floor: prints as oriented with no supports.
layout  = "full";   // "full", "work", "phone"
phone_t = 13;       // phone slot width: phone + case (13 normal, 18 rugged case)
wall    = 1.6;
base    = 2.4;
r       = 2;        // corner radius of every cavity
$fn = 40;

note = 76.2 + 1.2;  // 3 x 3 in sticky-note pad + 1.2 mm
card = [90, 9];     // 88.9 x 50.8 mm (3.5 x 2 in) card, 90 mm long, 9 mm thick (about 30 cards)
phone_len = 82;     // iPhone 16 Pro Max is 77.6 mm wide
pen = 48;           // pen cup, about 20 pens

// [x, y, w, d, h] - cavities (inner size), wall-thick shared walls between neighbours
function cavities() =
    layout == "full" ? [
        [0, 0, note, note, 14],
        [note + wall, 0, phone_t, phone_len, 70],
        [note + phone_t + 2 * wall, 0, pen, pen, 90]
    ] :
    layout == "work" ? [
        [0, 0, note, note, 14],
        [0, note + wall, card[0], card[1], 30],
        [card[0] + wall, 0, pen, pen, 90],
        [card[0] + wall, pen + wall, pen, pen, 80]
    ] : [
        [0, 0, phone_t, phone_len, 70],
        [phone_t + wall, 0, 40, 40, 14],
        [phone_t + wall, 40 + wall, 40, 40, 70]
    ];

module rr(w, d, rad) { translate([rad, rad]) offset(r = rad) square([w - 2 * rad, d - 2 * rad]); }

c = cavities();
difference() {
    union() for (k = c)
        translate([k[0] - wall, k[1] - wall, 0]) linear_extrude(k[4] + base) rr(k[2] + 2 * wall, k[3] + 2 * wall, r + wall);
    for (k = c)
        translate([k[0], k[1], base]) linear_extrude(k[4] + 1) rr(k[2], k[3], r);
}
