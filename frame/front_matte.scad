// FRAME = The inner dimension of the wooden frame
// PANEL = The size of the electronic board with the screen
// VIEWPORT = The size of portion that has the pixels to be shown

include <vars.scad>;

module alignment_pin(x, y) {
    translate([x, y, matte_depth])
    cylinder(pin_height, d=pin_width);
	};
	
module viewport_window()  {
    // The opening is always centered in the matte 
	// The opening is always the same depth as the frame (to make a complete void)
	
    x_offset = (frame_width - viewport_width) / 2;
	y_offset = (frame_height - viewport_height) / 2;
	
    translate([x_offset, y_offset, 0])
    cube([viewport_width, viewport_height, matte_depth]);
	};
      
module panel_holder() {
    x_offset = (frame_width - panel_width) / 2   + viewport_to_panel_width_offset;
	y_offset = (frame_height - panel_height) / 2 + viewport_to_panel_height_offset;
	z_offset = matte_depth - panel_depth;
	
	translate([x_offset, y_offset, z_offset])
    cube([panel_width, panel_height, panel_depth]);
	};

module ribbon_cutout_area() {
	x_offset = (frame_width - ribbon_cutout_width) / 2 + ribbon_cutout_width_offset;
	y_offset = frame_bottom_border_height - ribbon_cutout_height;

    translate([x_offset, y_offset, matte_depth - panel_depth])
		cube([ribbon_cutout_width, ribbon_cutout_height, panel_depth]); 
    }; 
	  
module base_matte()
    cube([frame_width, frame_height, matte_depth]);
			 
module front_mat () 
    union() {
        
    // Create the frame centers x/y, but z=0

    difference() {
		base_matte();
        
        // Cut out the space for the display
        //  (aka the part you can see)
        viewport_window();

        // Cut out the space for the panel
        //  (aka whole the electronic board for the e-paper)
        panel_holder();
              
        // Leave space for ribbon cable
        ribbon_cutout_area();
    };
    
    // Front
    alignment_pin(pin_offset, pin_offset);
    alignment_pin(frame_width-pin_offset, pin_offset);
    
    // Back
    alignment_pin(frame_width-pin_offset-pin_back_indent, frame_height-pin_offset);
    alignment_pin(pin_offset+pin_back_indent, frame_height-pin_offset);   
    };
 

front_mat();