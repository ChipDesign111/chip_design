#####################################################################################
# Description:  Genus Logic Synthesis Makefile
# Author:     	Mingxuan Li <mingxuanli_siris@163.com> [Peking University]
#####################################################################################

# check whether TOP is defined
ifndef TOP
$(error ERROR! TOP variable is not defined. Please define the top-level module name by TOP=<name>. Attention! TOP should be the same as rm_core_top in config/user_define.tcl)
endif

# check whether TOP equals to rm_core_top
RM_CORE_TOP = $(shell sed -n '/^[^\#]*set rm_core_top /s/.*set rm_core_top \([^]]*\).*/\1/p' ../config/user_define.tcl)
ifneq (${TOP},${RM_CORE_TOP})
$(error ERROR! Dismatch between TOP and rm_core_top! TOP=${TOP}, rm_core_top=${RM_CORE_TOP})
endif

genus:
	cd logs && genus -abort_on_error -f ../scripts/genus_synthesis.tcl -log ${TOP}.log -overwrite

restore:
	cd logs && genus -abort_on_error -f ../${TOP}/backup/${TOP}.genus_setup.tcl -log ${TOP}_restore.log -overwrite
