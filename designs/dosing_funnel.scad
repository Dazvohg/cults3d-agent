// Espresso dosing funnel for 51 / 53 / 54 / 58 mm portafilters - original design (Brian Sacco)
// A plug ring drops into the basket, a 45-degree seat rests on the basket edge and a wide hopper catches the grounds.
// Prints standing on the plug ring: the hopper leans out at 39 degrees from vertical, so no supports.
basket   = 58;     // nominal portafilter size (mm): 51, 53, 54 or 58
plug_h   = 6;      // plug ring height that goes into the basket
cone_h   = 26;     // hopper height (the cone)
collar_h = 6;      // straight collar at the top, for stiffness
flare    = 0.8;    // hopper growth per mm of height (0.8 = 39 deg from vertical)
under    = 1.0;    // plug ring is this much under the nominal size so it always drops in
wall     = 2.56;   // radial wall (about 2 mm measured perpendicular to the cone)
$fn = 120;

ro = (basket - under) / 2;
ri = ro - wall;
total = plug_h + cone_h + collar_h;
rt = ro + flare * cone_h;

outer = [[0, 0], [ro - 0.8, 0], [ro, 0.8], [ro, plug_h], [rt, plug_h + cone_h], [rt, total], [0, total]];
inner = [[0, -1], [ri, -1], [ri, plug_h], [ri + flare * cone_h, plug_h + cone_h], [ri + flare * cone_h, total + 1], [0, total + 1]];

difference() {
    rotate_extrude() polygon(outer);
    rotate_extrude() polygon(inner);
}
