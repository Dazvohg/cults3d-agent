// Minimal Headphone Stand - original parametric design (Brian Sacco)
// Printed lying flat (2D profile extruded) -> no supports, strong layer lines.
height      = 230;   // hanger height (mm). Over-ear headphones measure ~185-220 mm tall
                     // (AirPods Max 187 mm): 230 keeps the cups off the desk; 195 = compact for 220 mm beds
base_len    = 150;   // footprint length (mm)
arm_len     = 110;   // top hanger length (mm)
thick       = 12;    // profile stroke thickness (mm)
extrude     = 50;    // print height = stand width (mm)
lip         = 14;    // raised lip at end of hanger
$fn = 96;

module stroke(p1, p2, t=thick) { hull() { translate(p1) circle(d=t); translate(p2) circle(d=t); } }

module profile() {
    // base
    stroke([0,0],[base_len,0]);
    // upright slightly leaning back for balance
    stroke([base_len*0.35,0],[base_len*0.30,height - thick]);
    // hanger (curved saddle)
    for (a=[0:10:170]) {
        r = arm_len/2;
        c = [base_len*0.30 + r, height - thick];
        p1 = c + [ -r*cos(a),     r*0.18*sin(a)];
        p2 = c + [ -r*cos(a+10),  r*0.18*sin(a+10)];
        stroke(p1, p2);
    }
    // lip
    stroke([base_len*0.30 + arm_len, height - thick],[base_len*0.30 + arm_len + 4, height - thick + lip]);
    // gusset for rigidity
    stroke([base_len*0.35,thick*2.5],[base_len*0.65,0], thick*0.8);
    stroke([base_len*0.35,thick*2.5],[base_len*0.05,0], thick*0.8);
}
linear_extrude(height = extrude) profile();
