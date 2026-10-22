set io_segments [dict create N {} S {} W {} E {}]
foreach ip [dbGet top.insts.cell.baseClass pad -p2] {
 lassign [lindex [dbGet $ip.box] 0] x0 y0 x1 y1
 if {abs($y1-1800.4)<0.001} {set side N;set a $x0;set b $x1;set want R180} elseif {abs($y0)<0.001} {set side S;set a $x0;set b $x1;set want R0} elseif {abs($x0)<0.001} {set side W;set a $y0;set b $y1;set want R270} elseif {abs($x1-1800.4)<0.001} {set side E;set a $y0;set b $y1;set want R90} else {error "PAD not on a Die edge"}
 if {[dbGet $ip.orient] ne $want} {error "Wrong IO orientation"}
 dict lappend io_segments $side [list $a $b [dbGet $ip.name]]
}
foreach side {N S W E} {
 set last 115.0
 foreach seg [lsort -real -index 0 [dict get $io_segments $side]] {lassign $seg a b nm;if {abs($a-$last)>0.001} {error "IO gap/overlap at $side $nm : $last to $a"};set last $b}
 if {abs($last-1685.4)>0.001} {error "IO edge incomplete"}
 puts "IO_EDGE $side [llength [dict get $io_segments $side]] continuous 115-1685.4 correct_orientation"
}
saveDesign ../my_soc_top/backup/my_soc_top_postIOFiller.enc
