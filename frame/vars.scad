// FRAME = The outer dimension of the matte and backing board
//         (Use the inner dimension of the wooden frame as the basis, but remove 0.5-1mm for wiggle room)

// PANEL = The size of the electronic board with the screen
//         (Measure it or get it from the manufacturer's website)

// VIEWPORT = The size of portion that has the pixels to be shown
//           (Best to start with the manufacturer's website - might need a tad modified)

// PIN = The four round holes/pins that connect the matte to the backboard

// BOX = The container for the electronics behind the frame (part of the backing board)

// RIBBON (CUTOUT) = The ribbon cable that goes to the eInk display.  
//				     Cutout = the space to go between the matte and the backing board

// TAB = The connectors that keep the back/matte into the wooden frame (1 stationary, 3 moving tabs)


// All numbers (length/width/etc.) are in millimeter

frame_width = 176; // 6 7/8" + 1mm
frame_height = 126;  // 4 7/8" + 2mm

matte_depth = 3; // was 3 mm (2.75mm is too thin)

backboard_depth = 3; // 3mm

panel_width = 170.2 + 1;// add a 1mm clearance
panel_height = 111.2 + 1;// add a 1mm clearance
panel_depth = 2.25;

viewport_width = 163.2 + 2; 
viewport_height = 97.92 + 2; 

viewport_to_panel_width_offset = 0;
viewport_to_panel_height_offset = -3;

ribbon_cutout_width = 25; // width of cutout for ribbon cable
ribbon_cutout_height = 2;
ribbon_cutout_width_offset = 1;  // + = move right, - = move left (looking from the back)

ribbon_slot_height = 6;

// Alignment pins (which line up the matte with the back board)
pin_width = 3;
pin_offset = 3.5;
pin_up = 3;
pin_back_indent = 3;  // Indent the back pins so that there is only one way the two sides match

// The electronics box (mounted on the back board)
box_width = 140;
box_height = 100;
box_depth  = 23;
box_thickness = 2;

box_corner_post_radius = 5;
box_screw_head_diameter = 5;
box_screw_diameter = 3;

frame_to_box_height_offset = 6;

// Tab - goes into the slot of the frame
backboard_tab_width = 60;
backboard_tab_height = 2.5;
backboard_tab_depth = 1;

// Movable tabs - the round pins connecting the three other sides (beyond the primary tab)
movable_tab_width = 6;
movable_tab_offset = 8;
movable_tab_depth = 4;


// Power Cord cutout (the place where the power cord goes)
power_cord_slot_diameter = 5; // 5mm space for the cable
power_cord_slot_height   = 6; // 10mm of vertical spacing for the slot
power_cord_slot_offset = 30;  // How far the power cord cutout is from the bottom

// Standoffs (for electronic boards)
standoff_screw_diameter = 2.5;
standoff_depth = 4.5;


// backplate
backplate_depth = 4;
backplate_pocket_depth = 1.5;

// stand
stand_angle = 55;
stand_length = 90;  // the size (length) of the rectangular "rod" (was 100)
stand_width = 4;     // the size of the rectangular "rod"
stand_height = 9;    // the size of the rectangular "rod"

// Control how "good" the circles are
$fn = $preview ? 20 : 40;


// Computed items below
frame_bottom_border_height = (frame_height - panel_height)/2 + viewport_to_panel_height_offset;
frame_top_border_height    = (frame_height - panel_height)/2 - viewport_to_panel_height_offset;
pin_height = backboard_depth;

latch_width =  2 * movable_tab_width;