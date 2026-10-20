#####################################################################################
# Description:  Innovus Physical Implementation Makefile
# Author:     	Mingxuan Li <mingxuanli_siris@163.com> [Peking University]
#####################################################################################

# check whether TOP is defined
ifndef TOP
$(error ERROR! TOP variable is not defined. Please define the top-level module name by TOP=<name>. Attention! TOP should be the same as rm_core_top in config/user_define.tcl)
endif

# check whether TOP equals to rm_core_top
RM_CORE_TOP = $(shell grep -oP 'set rm_core_top \K.*' ../config/user_define.tcl)
ifneq (${TOP},${RM_CORE_TOP})
$(error ERROR! Dismatch between TOP and rm_core_top. TOP=${TOP}, rm_core_top=${RM_CORE_TOP})
endif

# check validation of optimization level
OPT_LEVEL = $(shell grep -oP 'set pnr_opt_level \K.*' ../config/user_define.tcl)
ifneq (${OPT_LEVEL},standard)
ifneq (${OPT_LEVEL},express)
$(error ERROR! Unknown optimization level. Choose by "set pnr_opt_level [express | standard]" in config/user_define.tcl)
endif
endif

VALID_STAGE = Floorplan Powerplan Place CTS Route Signoff

innovus:
	mkdir -p logs ${TOP}/backup ${TOP}/reports
	cd logs && innovus -execute "source ../scripts/init_pnr.tcl; win" -log ${TOP}_init.log
