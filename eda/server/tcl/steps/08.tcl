saveDesign ../my_soc_top/backup/my_soc_top_preIOConnect.enc
addNet clk_i_pad
detachModulePort - clk_i
attachModulePort - clk_i clk_i_pad
set clk_i_core_net [dbGet [dbGet top.hInst.hInsts.hInstTerms.name i_dmi_jtag/clk_i -p].net.name]
set clk_i_ext_net [dbGet [dbGet top.terms.name clk_i -p].net.name]
if {$clk_i_core_net in {{} 0x0} || $clk_i_ext_net in {{} 0x0} || $clk_i_core_net eq $clk_i_ext_net} {error "Invalid core/external net split"}
attachTerm i_pad_clk PAD $clk_i_ext_net
attachTerm i_pad_clk C $clk_i_core_net
attachTerm i_pad_clk OEN 1'b1
attachTerm i_pad_clk IE 1'b1
attachTerm i_pad_clk PE 1'b0
attachTerm i_pad_clk DS 1'b0
attachTerm i_pad_clk I 1'b0

addNet rst_ni_pad
detachModulePort - rst_ni
attachModulePort - rst_ni rst_ni_pad
set rst_ni_core_net [dbGet [dbGet top.hInst.hInsts.hInstTerms.name i_dmi_jtag/rst_ni -p].net.name]
set rst_ni_ext_net [dbGet [dbGet top.terms.name rst_ni -p].net.name]
if {$rst_ni_core_net in {{} 0x0} || $rst_ni_ext_net in {{} 0x0} || $rst_ni_core_net eq $rst_ni_ext_net} {error "Invalid core/external net split"}
attachTerm i_pad_rst_n PAD $rst_ni_ext_net
attachTerm i_pad_rst_n C $rst_ni_core_net
attachTerm i_pad_rst_n OEN 1'b1
attachTerm i_pad_rst_n IE 1'b1
attachTerm i_pad_rst_n PE 1'b0
attachTerm i_pad_rst_n DS 1'b0
attachTerm i_pad_rst_n I 1'b0

addNet tck_i_pad
detachModulePort - tck_i
attachModulePort - tck_i tck_i_pad
set tck_i_core_net [dbGet [dbGet top.hInst.hInsts.hInstTerms.name i_dmi_jtag/tck_i -p].net.name]
set tck_i_ext_net [dbGet [dbGet top.terms.name tck_i -p].net.name]
if {$tck_i_core_net in {{} 0x0} || $tck_i_ext_net in {{} 0x0} || $tck_i_core_net eq $tck_i_ext_net} {error "Invalid core/external net split"}
attachTerm i_pad_tck PAD $tck_i_ext_net
attachTerm i_pad_tck C $tck_i_core_net
attachTerm i_pad_tck OEN 1'b1
attachTerm i_pad_tck IE 1'b1
attachTerm i_pad_tck PE 1'b0
attachTerm i_pad_tck DS 1'b0
attachTerm i_pad_tck I 1'b0

addNet tms_i_pad
detachModulePort - tms_i
attachModulePort - tms_i tms_i_pad
set tms_i_core_net [dbGet [dbGet top.hInst.hInsts.hInstTerms.name i_dmi_jtag/tms_i -p].net.name]
set tms_i_ext_net [dbGet [dbGet top.terms.name tms_i -p].net.name]
if {$tms_i_core_net in {{} 0x0} || $tms_i_ext_net in {{} 0x0} || $tms_i_core_net eq $tms_i_ext_net} {error "Invalid core/external net split"}
attachTerm i_pad_tms PAD $tms_i_ext_net
attachTerm i_pad_tms C $tms_i_core_net
attachTerm i_pad_tms OEN 1'b1
attachTerm i_pad_tms IE 1'b1
attachTerm i_pad_tms PE 1'b0
attachTerm i_pad_tms DS 1'b0
attachTerm i_pad_tms I 1'b0

addNet td_i_pad
detachModulePort - td_i
attachModulePort - td_i td_i_pad
set td_i_core_net [dbGet [dbGet top.hInst.hInsts.hInstTerms.name i_dmi_jtag/td_i -p].net.name]
set td_i_ext_net [dbGet [dbGet top.terms.name td_i -p].net.name]
if {$td_i_core_net in {{} 0x0} || $td_i_ext_net in {{} 0x0} || $td_i_core_net eq $td_i_ext_net} {error "Invalid core/external net split"}
attachTerm i_pad_tdi PAD $td_i_ext_net
attachTerm i_pad_tdi C $td_i_core_net
attachTerm i_pad_tdi OEN 1'b1
attachTerm i_pad_tdi IE 1'b1
attachTerm i_pad_tdi PE 1'b0
attachTerm i_pad_tdi DS 1'b0
attachTerm i_pad_tdi I 1'b0

addNet td_o_pad
detachModulePort - td_o
attachModulePort - td_o td_o_pad
set td_o_core_net [dbGet [dbGet top.hInst.hInsts.hInstTerms.name i_dmi_jtag/td_o -p].net.name]
set td_o_ext_net [dbGet [dbGet top.terms.name td_o -p].net.name]
if {$td_o_core_net in {{} 0x0} || $td_o_ext_net in {{} 0x0} || $td_o_core_net eq $td_o_ext_net} {error "Invalid core/external net split"}
attachTerm i_pad_tdo PAD $td_o_ext_net
attachTerm i_pad_tdo I $td_o_core_net
attachTerm i_pad_tdo OEN 1'b0
attachTerm i_pad_tdo IE 1'b0
attachTerm i_pad_tdo PE 1'b0
attachTerm i_pad_tdo DS 1'b0

dbGet [dbGet top.terms.name clk_i -p].net.name
dbGet [dbGet top.insts.name i_pad_clk -p].instTerms.name
dbGet [dbGet top.hInst.hInsts.hInstTerms.name i_dmi_jtag/clk_i -p].net.name
saveNetlist ../my_soc_top/my_soc_top_io_connected.v

foreach pi [dbGet top.insts.name i_pad_* -p] {puts "PAD [dbGet $pi.name]"; foreach it [dbGet $pi.instTerms] {puts "[dbGet $it.name] => [dbGet $it.net.name]"}}

saveDesign ../my_soc_top/backup/my_soc_top_postSignalPad_fixed.enc
