include <vars.scad>

module latch_base() {
   hole_width = movable_tab_width * 1.1;
   length = movable_tab_offset * 1.25 + hole_width;
   depth = movable_tab_depth;
   
   translate([movable_tab_offset * 0.1, 0, 0])
    difference() {
        
        intersection() {
            cube([length, latch_width, depth]);
            translate([latch_width * 0.6, latch_width/2,0]) 
                cylinder(d=latch_width*1.25, h=depth);
            };
            
    translate([movable_tab_offset, latch_width/2, 0]) 
        cylinder(d=hole_width, h=depth);
   };
};

module latch_tab_extension() {
   x_diff_percent = 0.68;   // why 0.68?
    
   length = backboard_tab_height * 2; // underneath is same length as tab itself (from tip)
   depth = backboard_tab_depth;
   
   z_diff = backboard_depth - backboard_tab_depth;
   x_diff = backboard_tab_height * x_diff_percent;  
    
   translate([-backboard_tab_height, 0, -backboard_depth])
     intersection() {
        cube([length, latch_width, depth]);
        translate([latch_width * 0.98, latch_width/2, -0]) // allow for a slightly flat top (<1 = flat top)
            cylinder(r=latch_width, h=backboard_tab_depth);
        };     
    
    if (z_diff > 0) {
        translate([(1-x_diff_percent) * backboard_tab_height, 0, -z_diff])
            intersection() {
                cube([x_diff, latch_width, z_diff]);
                translate([latch_width * 0.6, latch_width/2, 0]) 
                    cylinder(d=latch_width*1.25, h=backboard_depth); // match top part's roundness
                };
        
        };    

};

module latch_handle() {
   length = movable_tab_offset;
   width = 3;
   depth = 4;
   r = 3;
  
   translate([3.5, 0, movable_tab_depth])
      hull() {
        cube([length, width, depth/2]);
        rotate([90,0,0]) translate([r, depth-r, -width]) cylinder(h=width, r=r);
        rotate([90,0,0]) translate([length-r, depth-r, -width]) cylinder(h=width, r=r);
        };
};

module latch() {
    rotate([90, 0, 0]) {
        latch_base();
        latch_tab_extension();
        latch_handle();
        };
    };

latch();