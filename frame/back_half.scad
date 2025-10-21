// FRAME = The inner dimension of the wooden frame
// PANEL = The size of the electronic board with the screen
// VIEWPORT = The size of portion that has the pixels to be shown
include <vars.scad>;

hole_width = pin_width * 1.20; // 20% wiggle room between pin and hole
pin_percent = 0.98;   // How much smaller (<1) or larger (>1) to make the actual hole

//------------------------------------------------------------------------------


module alignment_hole(x, y)  {  
	translate([x, y, 0])
	cylinder(backboard_depth, d=hole_width * pin_percent);
    };
    

//------------------------------------------------------------------------------


module ribbon_cutout_thru() {
	x_offset = (frame_width - ribbon_cutout_width) / 2 + ribbon_cutout_width_offset;
	y_offset = frame_to_box_height_offset + box_thickness;

    //translate([x_offset, y_offset, 0])
    //cube([ ribbon_cutout_width, ribbon_slot_height, backboard_depth]);
    
    x_middle = frame_width / 2;
    
    // slot for inserting cable & HAT
    slot_width = 14;
    translate([x_middle-slot_width/2, y_offset, 0])
        cube([slot_width, 36, backboard_depth]);
    };


module ribbon_relief_area() {
	x_offset = (frame_width - ribbon_cutout_width) / 2 + ribbon_cutout_width_offset;
	y_offset = frame_bottom_border_height - ribbon_cutout_height;

	slot_y_offset = frame_to_box_height_offset + box_thickness;
	
    translate([x_offset, y_offset, 0])
	cube([ribbon_cutout_width, slot_y_offset - y_offset, backboard_depth/2]); 
  };


//------------------------------------------------------------------------------


module frame_tab() {
   backboard_tab_radius = 5;
    
   x_offset = (frame_width - backboard_tab_width) /2;
   y_offset = 0;
   
   translate([x_offset, y_offset, 0]) {
     linear_extrude(height=backboard_tab_depth)
        hull() {
            square(1);
                      
            translate([backboard_tab_width-1, 0]) 
                square(1);
                       
            translate([0.2 * backboard_tab_width, -backboard_tab_height+backboard_tab_radius]) 
                //square(1);
                circle(backboard_tab_radius);
            
            translate([0.8 * backboard_tab_width, -backboard_tab_height+backboard_tab_radius]) 
                //square(1);
                circle(backboard_tab_radius);
        };
      };
  };


//------------------------------------------------------------------------------

module base_backboard()
    cube([frame_width, frame_height, backboard_depth]);


//------------------------------------------------------------------------------

module outer_box() {
    
 x_offset = (frame_width - box_width) / 2;
 y_offset = frame_to_box_height_offset;
 
 radius = box_corner_post_radius;

 translate([x_offset, y_offset, backboard_depth])
      hull() {
          translate([radius, radius]) cylinder(r=radius,h=box_depth);
          translate([box_width-radius, radius]) cylinder(r=radius,h=box_depth);
          translate([box_width-radius, box_height-radius]) cylinder(r=radius,h=box_depth);
          translate([radius,box_height-radius]) cylinder(r=radius,h=box_depth);
      };
};


module inner_box() {
	x_offset = (frame_width - box_width) / 2 + box_thickness;
	y_offset = frame_to_box_height_offset    + box_thickness;
	
	translate([x_offset, y_offset, backboard_depth])
	cube([box_width - 2*box_thickness, box_height-2*box_thickness, box_depth]);
	};

module box_corner_post(x,y) {
	x_offset1 = (frame_width - box_width) / 2;
	y_offset1 = frame_to_box_height_offset;
	
	translate([x+x_offset1,  y+y_offset1, backboard_depth])
	difference() {
		cylinder(r=box_corner_post_radius, h=box_depth);
		cylinder(d=box_screw_diameter, h=box_depth);
	}
  }

//-------------------------------------------------------


module electronics_box() {
   
  difference() {
    outer_box();
	inner_box();
    };
	
  box_corner_post(box_corner_post_radius, box_corner_post_radius);
  box_corner_post(box_width-box_corner_post_radius, box_corner_post_radius);
  box_corner_post(box_width-box_corner_post_radius, box_height-box_corner_post_radius);
  box_corner_post(box_corner_post_radius, box_height-box_corner_post_radius);
};

//-------------------------------------------------------

module movable_tab_post(x,y) {
    tab_top_depth = movable_tab_depth * 0.4;
    tab_total_depth = movable_tab_depth + tab_top_depth +  + backboard_depth;
    
    // The following two lines control the shape of the
    // "mushroom top" of the post.  _width2 is the very top,
    //  while width1 is the lower portion of the top
    
    tab_top_width2 = movable_tab_width * 0.9;
    tab_top_width1 = movable_tab_width * 1.2;
    
    max_width = max(movable_tab_width, tab_top_width1, tab_top_width2);
    slot_height = movable_tab_width * 0.25;
    
    translate([x, y, 0]) 
        difference() {
            union() {
                cylinder(h=movable_tab_depth +  backboard_depth, 
                         d=movable_tab_width);
        
                translate([0, 0, movable_tab_depth +  backboard_depth])
                cylinder(h=tab_top_depth, 
                         d1=tab_top_width1,  
                         d2=tab_top_width2);
                };
            
             translate([-max_width/2, -slot_height/2, 0])
             cube([max_width, slot_height, tab_total_depth]);   
             };
    
    };

module movable_tab_posts() {
    movable_tab_post(frame_width/2, frame_height - movable_tab_offset);
    movable_tab_post(movable_tab_offset, frame_height /2);
    movable_tab_post(frame_width - movable_tab_offset, frame_height/2);
};



//------------------------------------------------------------------------------

module latch_platform(x, y, angle=0) {
    x_diff_percent = 0.68;
    
    h = backboard_depth;
    r = movable_tab_width * x_diff_percent * 1.45;
     
    b = movable_tab_offset; // base of the slider
    f = backboard_tab_height; // foot of the slider
     
    x1 = latch_width * 1.1; // 10% larger
    x2 = (f + b) * 1.1; // 10% larger than entire slider len
     
    y1 = x1;
    y2 = b;
    
    xt = x1-r;
    yt = y1-r;
    
    translate([x-x1+r, y-y1+r, 0])
      translate([xt, yt, 0])
        rotate([0,0,angle])
          translate([-xt, -yt, 0])
            hull () {
                translate([x1-r, y1-r, 0])
                    cylinder(r=r, h=h);
                
                translate([x1-1, 0, 0])
                    cube([1, 1, h]);
                
                translate([0, 0, 0])
                    cube([1, 1, h]);
                
                translate([0, y1-1, 0])
                    cube([1, 1, h]);
                };
    };

module latch_raw_cutout(x, y, angle=0) {
    
   h = backboard_depth;
   r = movable_tab_width;
     
   b = movable_tab_offset; // base of the slider
   f = backboard_tab_height; // foot of the slider
    
   x1 = b * 1 ; // was 1.1
   x2 = (f + b) * 1; // was 1.00 (and then 0.95 before that)
     
   y1 = x1;
   y2 = movable_tab_width * 2;
   
   xt = x2 - r * 0.55;
   yt = y2 - r;
    
   translate([x -x2 + r * 0.55,y-y2+r,0])  // was 0.7
       translate([xt, yt, 0])
        rotate([0,0,angle])
          translate([-xt, -yt, 0])
            cube([x1+x2, y1+y2, backboard_depth]);
   };

module latch_cutout(x, y, angle=0) {
    difference() {
        latch_raw_cutout(x,y, angle);
        latch_platform(x,y, angle);
        }
    };

//------------------------------------------------------------------------------

module movable_tab_cutouts() {
    latch_cutout(frame_width/2, frame_height - movable_tab_offset);
    latch_cutout(movable_tab_offset, frame_height /2, 90);
    latch_cutout(frame_width - movable_tab_offset, frame_height/2, -90);
};



//-------------------------------------------------------

module electronics_standoff(x, y, h=standoff_depth, screw=standoff_screw_diameter) {
    standoff_diameter = screw * 3;
    
    translate([x, y, backboard_depth])
    difference() {
        cylinder(h, d=standoff_diameter);
        cylinder(h, d=screw * pin_percent);
        };
    };
    
module four_standoff_centered_at(x, y, length, width,
                                 h=standoff_depth, screw=standoff_screw_diameter) {
    x_offset1 = x - length / 2;
    x_offset2 = x_offset1 + length;
                                     
    y_offset1 = y - width / 2;
    y_offset2 = y_offset1 + width;
                      
    electronics_standoff(x_offset1, y_offset1, h, screw);
    electronics_standoff(x_offset2, y_offset1, h, screw);
    electronics_standoff(x_offset1, y_offset2, h, screw);
    electronics_standoff(x_offset2, y_offset2, h, screw);                                 
    };
//-------------------------------------------------------
module power_cord_cutout() {
   r = power_cord_slot_diameter / 2;
   
   x_offset = (frame_width - box_width) / 2 ;
   y_offset = r + frame_to_box_height_offset + power_cord_slot_offset;
   z_offset = backboard_depth + box_depth - power_cord_slot_height + r;
   
   translate([x_offset, y_offset, z_offset])
    rotate([0,0, 0])
    union() {
	  translate([0,-r, 0])
        cube([box_thickness, power_cord_slot_diameter, power_cord_slot_height - r]);
	  rotate([-90, 0, -90])
	    cylinder(r=r, h=box_thickness);
      };
   };
   
//-------------------------------------------------------

module small_circuit_board(h=standoff_depth, screw=standoff_screw_diameter) {
    length = 31.75 - 3.5 - 3.5;
    width = 17.5 - 3.5 - 3.5;
    
    y_opening_to_board_offset = 12;
    
    x_center = frame_width / 2 + ribbon_cutout_width_offset;
    
    y_center = frame_to_box_height_offset + box_thickness + 
               y_opening_to_board_offset + width /2 ;
    
    four_standoff_centered_at(x_center, y_center, length, width, h, screw);
};


module pi_zero(h=standoff_depth) {
    
    width = 23;   // mounting hole to mounting hole
    length = 58;  // mounting hole to mounting hole
    
    y_opening_to_board_offset = 55;
    
    x_center = frame_width / 2;
    y_center = frame_to_box_height_offset + box_thickness + 
               y_opening_to_board_offset + width /2 ;
    
    four_standoff_centered_at(x_center, y_center, length, width, h);
};

module pi_3(h=standoff_depth) {
    width = 49; // mounting hole to mounting hole
    length = 58; // mounting hole to mounting hole
    board_width = 85;  // Board edge to edge
    
    x_offset = 0; // near lhs border
    y_opening_to_board_offset = 40;
    
    x_center = frame_width/2 - box_width/2 + board_width/2 + x_offset;
    y_center = frame_to_box_height_offset + box_thickness + 
               y_opening_to_board_offset + width /2 ;
    
    four_standoff_centered_at(x_center, y_center, length, width, h);

};
//-------------------------------------------------------

module back_half () {
	difference() {
		base_backboard();
			
		// Now "insert" the holes for the four alignment pins (in each corner)
		//Front
        alignment_hole(pin_offset, pin_offset);
		alignment_hole(frame_width-pin_offset, pin_offset);
        
        // Back
		alignment_hole(frame_width-pin_offset-pin_back_indent, frame_height-pin_offset);
		alignment_hole(pin_offset+pin_back_indent, frame_height-pin_offset);
            
        //  Allow for the panel's ribbon cable to go through
        ribbon_cutout_thru();
        //ribbon_relief_area();
        
        // The space for the latch to go through
        movable_tab_cutouts();
		};
		
	difference() {
		electronics_box();
        power_cord_cutout();
		};
        
	frame_tab();
    movable_tab_posts();
    
    small_circuit_board(h=4.5); // M2.5x5mm screw 
    pi_zero(h=standoff_depth-1); // slightly shorter pins
    pi_3();
        
  	};
	
back_half();
    