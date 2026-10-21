# Loaded-design stage. Inputs: project_root, output_root, die_size,
# macro_instance. No RTL, timing constraint or technology data is modified.
foreach required {project_root output_root die_size macro_instance} {
    if {![info exists $required]} {error "Missing floorplan input: $required"}
}
source [file join $pnr_script_root geometry_helpers.tcl]
foreach directory {reports outputs backup} {file mkdir [file join $output_root $directory]}
pnr4::assert {[dbGet top.name] eq "my_soc_top"} "Expected complete my_soc_top design"
pnr4::assert {[string is double -strict $die_size] && $die_size > 1000} "Invalid initial die size"
set requested_core [expr {$die_size-300.0}]
floorPlan -site core7T -coreMarginsBy die -s $requested_core $requested_core 150 150 150 150
set pnr4::die [pnr4::flat_list [dbGet top.fPlan.box] 4 die]
set pnr4::core [pnr4::flat_list [dbGet top.fPlan.coreBox] 4 core]
pnr4::inside $pnr4::core $pnr4::die "Core"
lassign $pnr4::core cx0 cy0 cx1 cy1
set macro_pointer [pnr4::inst $macro_instance]
pnr4::assert {[dbGet $macro_pointer.cell.name] eq "RA1SHD_2048x32M8"} "Unexpected SRAM master"
lassign [pnr4::size RA1SHD_2048x32M8] macro_width macro_height
# Leave a 100 um channel at the left core edge and center the SRAM vertically.
# The larger logic area remains contiguous on its right.
set macro_x [pnr4::grid [expr {$cx0+100.0}]]
set macro_y [pnr4::grid [expr {($cy0+$cy1-$macro_height)/2.0}]]
placeInstance $macro_instance $macro_x $macro_y R0 -fixed
addHaloToBlock 26 26 26 26 $macro_instance -snapToSite
set pnr4::macro_box [pnr4::box $macro_pointer]
set pnr4::macro_halo [pnr4::flat_list [dbGet $macro_pointer.pHaloBox] 4 "SRAM halo"]
pnr4::inside $pnr4::macro_box $pnr4::core SRAM
pnr4::inside $pnr4::macro_halo $pnr4::core "SRAM halo"
lassign $pnr4::macro_box mx0 my0 mx1 my1
lassign $pnr4::macro_halo hx0 hy0 hx1 hy1
# Innovus snaps the requested 26 um halo to row/site boundaries. Its actual
# clearance must still cover the 20 um outer macro power-ring envelope.
foreach clearance [list [expr {$mx0-$hx0}] [expr {$my0-$hy0}] [expr {$hx1-$mx1}] [expr {$hy1-$my1}]] {
    pnr4::assert {$clearance >= 20.0-$pnr4::tol} "Snapped SRAM halo is too small for its power ring"
}
set geometry_file [open [file join $output_root reports floorplan_geometry.rpt] w]
foreach item {die core macro_box macro_halo} {puts $geometry_file "$item [set pnr4::$item]"}
puts $geometry_file "requested_die $die_size requested_halo 26"
close $geometry_file
checkFPlan -reportUtil -outFile [file join $output_root reports floorplan_check.rpt]
defOut [file join $output_root outputs my_soc_top_floorplan.def]
pnr4::checkpoint floorplan
puts "PNR_FLOORPLAN_FINISHED die=$pnr4::die core=$pnr4::core macro=$pnr4::macro_box"
