include <vars.scad>

oversize_hole = 1.00;   // was 1% oversized


// ------------------------------------------------------

module text_line(x, y, z, s, size, height) {

   translate([x, y, z]) 
        linear_extrude(height)
            text(s, size, font="Arial", valign="top");
  };

module name_plate (x, y, l, w, depth=0.5) {
    z_offset = backplate_depth - depth;
    
    translate([x, y, z_offset]) cube([l, w, depth]);
    };

module name_text(x, y, z, height=0.5) {
   
    text_line(x, y, z, "WeatherToo", 6, height);
    line_y2 = y - 8;
    
    text_line(x, line_y2, z, "  by Mark Monnin", 4, height);
    //line_y3 = line_y2 - 5;
    line_y3 = y;
    line_x3 = x + 46;
    text_line(line_x3, line_y3, z, "v2.0", 3, height);
    
    //text_line(x, line_y3, z, 
    //          "https://github.com/monnin/quickglance", 3, height);
};

// ------------------------------------------------------


module screw_relief_hole(x, y) {
    z_offset = backplate_depth - backplate_pocket_depth;
    d = box_screw_diameter * 1.05; // A little extra wiggle room - screw should bind on back_half but not backplate
    
    translate([x+box_corner_post_radius, y+box_corner_post_radius, z_offset])
        cylinder(h=backplate_pocket_depth, d=box_screw_head_diameter * 1.25);
    
    translate([x+box_corner_post_radius, y+box_corner_post_radius, 0])
        cylinder(h=backplate_depth, d=d);
    };

module screw_relief_holes() {

    screw_relief_hole(0, 0);
    screw_relief_hole(box_width-box_corner_post_radius*2, 0);
    screw_relief_hole(0, box_height-box_corner_post_radius*2);
    screw_relief_hole(box_width-box_corner_post_radius*2, box_height-box_corner_post_radius*2);
    };
      

// ------------------------------------------------------

module key_hole (x, y, l, w) {
   cube_l = l - w/2;
   circle_d = w * 2;
    
    translate([x-w/2, y-w/2, 0])
       cube([w, cube_l, backplate_depth]);
    
    translate([x,y-cube_l/2, 0])
       cylinder(d=circle_d, h=backplate_depth);
   };
   
   
// ------------------------------------------------------
   
 module stand_hole(x, y) {
    cube_depth = backplate_depth * 8;
    
    w = stand_width * oversize_hole;  // allow for a little bit bigger
    h = stand_height * oversize_hole; // allow for a little bit bigger
     
    translate([x, y, 0])
       rotate([stand_angle, 0, 0])
         translate([-w/2, -h/2, -cube_depth/2])
            cube([w, h, cube_depth]);
    };
    
// ------------------------------------------------------

module plate_corner_post(x, y) {
  //top_radius = min(box_corner_post_radius, backplate_depth/2);
  //x_offset = box_corner_post_radius - top_radius;
  top_radius = 0;
    
  translate([x+box_corner_post_radius, y+box_corner_post_radius, 0])
    cylinder(h=backplate_depth-top_radius, r=box_corner_post_radius);

  //translate([x+x_offset, y+x_offset, backplate_depth-top_radius]) 
  //  sphere(r=top_radius);
 
  
};

// ------------------------------------------------------


module base_plate() {

  difference () {
      hull() {
          plate_corner_post(0, 0);
          
          plate_corner_post(box_width-box_corner_post_radius*2, 0);
          plate_corner_post(0, box_height-box_corner_post_radius*2);
          plate_corner_post(box_width-box_corner_post_radius*2, 
                            box_height-box_corner_post_radius*2);
          };
      
      // cut off the space below zero (in z axis)
      translate([0, 0, -10]) cube([box_width, box_height, 10]);
      };
    };

// ------------------------------------------------------


module backplate() {
    name_plate_depth = 0.8;
    
    difference () {
        base_plate();
        
        key_hole(box_width/2, box_height * 0.80, 9, 4);
        screw_relief_holes();
     
        name_plate( box_width * 0.55, box_height * 0.05, 
                    box_width * 0.4, box_height * 0.15,
                    name_plate_depth);
        
        stand_hole(box_width * 0.15, box_height * 0.75);
        stand_hole(box_width * 0.85, box_height * 0.75);
        };
        
    name_text(box_width * 0.55 + 1, box_height * 0.2 - 1, 
              backplate_depth - name_plate_depth);
        
};

backplate();

// plate_corner_post(-10,-10);