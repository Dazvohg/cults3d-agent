// Desk mate & thermos holder (matera de escritorio) - original design (Brian Sacco)
// One flat-bottom piece: thermos well with an open front slot for the side handle, mate well, bombilla/spoon groove.
// Prints as oriented with no supports: all walls vertical, the handle slot is open at the top.
part = "stanley";   // "stanley" (thermos up to 94 mm), "slim" (thermos 84-88 mm), "big_mate" (Stanley well + mate up to 94 mm)
wall = 3;  fl = 3;  $fn = 120;
td = part == "slim" ? 90 : 97;            // thermos well inner diameter
md = part == "big_mate" ? 97 : 86;        // mate well inner diameter (Stanley / Hudson / Coleman mates are ~80 mm)
th = 70;                                   // thermos well height
mh = 45;                                   // mate well height
gap = 6;                                   // wall-to-wall gap between wells
tr = td / 2 + wall;  mr = md / 2 + wall;
mx = tr + gap + mr;                        // mate well centre
module ring(d, h) { difference() { cylinder(d = d + 2 * wall, h = h); translate([0, 0, fl]) cylinder(d = d, h = h); } }
difference() {
    union() {
        hull() { cylinder(r = tr + 2, h = fl); translate([mx, 0, 0]) cylinder(r = mr + 2, h = fl); }   // base plate
        ring(td, th);
        translate([mx, 0, 0]) ring(md, mh);
        hull() { translate([tr - 2, -10, 0]) cube([4, 20, mh * 0.6]); translate([mx - mr - 2, -10, 0]) cube([4, 20, mh * 0.6]); } // bridge web
    }
    translate([0, 0, fl]) cylinder(d = td, h = th);                 // re-open thermos well through the web
    translate([mx, 0, fl]) cylinder(d = md, h = mh);                // re-open mate well
    translate([-tr - 1, -18, 22]) cube([wall + 2, 36, th]);          // open slot on the back for a side handle (Stanley 1.4 L)
    for (a = [0, 120, 240]) translate([mx, 0, -1]) rotate(a) translate([md / 4, 0, 0]) cylinder(d = 5, h = fl + 2, $fn = 24); // drain holes for a wet mate
    translate([tr + gap / 2 - 3, -40, fl + mh * 0.6 - 6]) cube([6, 80, 10]); // groove on top of the web to rest a bombilla or spoon
}
