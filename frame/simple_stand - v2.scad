include <vars.scad>

screw_width = 2;

function height_to_rod_len (h) = 
    h / cos(stand_angle);
    
module rod () {
    r = stand_height / 2;
    
    translate([r, -stand_width/2, 0])
        cube([stand_length-r, stand_width, stand_height]);
    
    translate([r, 0, r])
        rotate([90, 0, 0])
          cylinder(h=stand_width, r=r, center=true);
    };
    
module flatten_foot() {
    
  x1 = stand_height * tan(90-stand_angle);
  
  translate([0, stand_width, 0])
    rotate([90,0,0])
        linear_extrude(stand_width * 2)
            polygon([[0,0], [0, stand_height], [x1, 0]]);
  };
    
module rod_stop() {
    stop_width = stand_width * 3;  // was 4
    stop_height = stand_height * 2.5; // was 2.75
    
    translate([stand_length - 25, -stop_width/2, 0]) 
        rotate([0, stand_angle, 0])
            cube([2, stop_width, stop_height]);
    };

module remove_end() {
    translate([stand_length - 15, -stand_width/2, 0]) 
        rotate([0, stand_angle, 0])
            cube([20, stand_width, stand_height * 2]);
    };

// TODO: FIXME:  This is a HACK
module screw_hole() {
   translate([stand_length - 8, 0, stand_height * 0.5])
        rotate([0, -stand_angle, 0])
            cylinder(d=screw_width, h=10, center=true);
   };

module expansion_slot() {
   translate([stand_length-24, 0, -2]) 
        translate([0, -0.25, 0]) // center on y
            rotate([0, stand_angle, 0])
                cube([12, 0.5, stand_height * 2.7]);
    };

// Remove all material below the z-axis
module remove_below() {
    translate([-10,-20,-10])
        cube([200, 40, 10]);
    };


module thru_hole(x, h, w) {
    d = 1.85; // A little bigger than a 1.75mm filament
    
    translate([x, 0, h/2])
        rotate([90, 0, 0])
            cylinder(d=d, h=w, center=true);
    };

module stand() {
    difference() {
        union() {
            rod_stop();
            rod();
            };
            
        // flatten_foot();
        //thru_hole(stand_length-5, stand_height, stand_width);  // was -4
        remove_end();
        screw_hole(); 
        #expansion_slot();
        remove_below();
        };
    };
    
 stand();