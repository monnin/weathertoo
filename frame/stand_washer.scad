// Control how "good" the circles are
$fn = $preview ? 20 : 40;

module main() {
    h = 1.5;
    difference() {
        cylinder(h=h, d=17, center=true);
        cylinder(h=h, d=2.4, center=true);
        };

};


main();