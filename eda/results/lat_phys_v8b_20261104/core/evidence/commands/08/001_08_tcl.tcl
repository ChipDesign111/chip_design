# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
set eda_term [dbGet top.terms.name clk_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet clk_i_pad
detachModulePort - clk_i
attachModulePort - clk_i clk_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name clk_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_clk PAD $eda_ext_net
attachTerm i_pad_clk C $eda_core_net
attachTerm i_pad_clk OEN 1'b1
attachTerm i_pad_clk IE 1'b1
attachTerm i_pad_clk PE 1'b0
attachTerm i_pad_clk DS 1'b0
attachTerm i_pad_clk I 1'b0
set eda_term [dbGet top.terms.name rst_ni -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet rst_ni_pad
detachModulePort - rst_ni
attachModulePort - rst_ni rst_ni_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name rst_ni -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_rst_n PAD $eda_ext_net
attachTerm i_pad_rst_n C $eda_core_net
attachTerm i_pad_rst_n OEN 1'b1
attachTerm i_pad_rst_n IE 1'b1
attachTerm i_pad_rst_n PE 1'b0
attachTerm i_pad_rst_n DS 1'b0
attachTerm i_pad_rst_n I 1'b0
set eda_term [dbGet top.terms.name tck_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet tck_i_pad
detachModulePort - tck_i
attachModulePort - tck_i tck_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name tck_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tck PAD $eda_ext_net
attachTerm i_pad_tck C $eda_core_net
attachTerm i_pad_tck OEN 1'b1
attachTerm i_pad_tck IE 1'b1
attachTerm i_pad_tck PE 1'b0
attachTerm i_pad_tck DS 1'b0
attachTerm i_pad_tck I 1'b0
set eda_term [dbGet top.terms.name tms_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet tms_i_pad
detachModulePort - tms_i
attachModulePort - tms_i tms_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name tms_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tms PAD $eda_ext_net
attachTerm i_pad_tms C $eda_core_net
attachTerm i_pad_tms OEN 1'b1
attachTerm i_pad_tms IE 1'b1
attachTerm i_pad_tms PE 1'b0
attachTerm i_pad_tms DS 1'b0
attachTerm i_pad_tms I 1'b0
set eda_term [dbGet top.terms.name td_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet td_i_pad
detachModulePort - td_i
attachModulePort - td_i td_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name td_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tdi PAD $eda_ext_net
attachTerm i_pad_tdi C $eda_core_net
attachTerm i_pad_tdi OEN 1'b1
attachTerm i_pad_tdi IE 1'b1
attachTerm i_pad_tdi PE 1'b0
attachTerm i_pad_tdi DS 1'b0
attachTerm i_pad_tdi I 1'b0
set eda_term [dbGet top.terms.name td_o -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet td_o_pad
detachModulePort - td_o
attachModulePort - td_o td_o_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name td_o -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tdo PAD $eda_ext_net
attachTerm i_pad_tdo I $eda_core_net
attachTerm i_pad_tdo OEN 1'b0
attachTerm i_pad_tdo IE 1'b0
attachTerm i_pad_tdo PE 1'b0
attachTerm i_pad_tdo DS 1'b0
saveNetlist ../my_soc_top/my_soc_top_io_connected.v

