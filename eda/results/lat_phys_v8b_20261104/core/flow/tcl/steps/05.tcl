addInst -physical -cell PCORNER -inst corner_bottom_left -loc {0 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_bottom_right -loc {1685.4 0} -ori MY -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_top_left -loc {0 1685.4} -ori MX -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_top_right -loc {1685.4 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
foreach ci [dbGet top.insts.name corner_* -p] {puts "CORNER [dbGet $ci.name] [dbGet $ci.orient] [dbGet $ci.pStatus] [dbGet $ci.box]"}
