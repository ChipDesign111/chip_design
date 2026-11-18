# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0xf07fd931
    printf "FPGA_CHECK_FAIL: wrong image tag for raw_tail_b4_cpu\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001e20 & 0xffffffff
      if $soc_actual != 0x04050342
        printf "Mismatch at 0x80001e20: got=0x%08x expected=0x04050342 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e24 & 0xffffffff
      if $soc_actual != 0x090c28a9
        printf "Mismatch at 0x80001e24: got=0x%08x expected=0x090c28a9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e28 & 0xffffffff
      if $soc_actual != 0xd20c31b9
        printf "Mismatch at 0x80001e28: got=0x%08x expected=0xd20c31b9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e2c & 0xffffffff
      if $soc_actual != 0xeb7746e8
        printf "Mismatch at 0x80001e2c: got=0x%08x expected=0xeb7746e8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e30 & 0xffffffff
      if $soc_actual != 0xba2aee0f
        printf "Mismatch at 0x80001e30: got=0x%08x expected=0xba2aee0f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e34 & 0xffffffff
      if $soc_actual != 0xf4d8250c
        printf "Mismatch at 0x80001e34: got=0x%08x expected=0xf4d8250c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e38 & 0xffffffff
      if $soc_actual != 0x0d1458fe
        printf "Mismatch at 0x80001e38: got=0x%08x expected=0x0d1458fe mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e3c & 0xffffffff
      if $soc_actual != 0x17f84be9
        printf "Mismatch at 0x80001e3c: got=0x%08x expected=0x17f84be9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e40 & 0x000000ff
      if $soc_actual != 0x00000049
        printf "Mismatch at 0x80001e40: got=0x%08x expected=0x00000049 mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e44 & 0xffffffff
      if $soc_actual != 0xfd080319
        printf "Mismatch at 0x80001e44: got=0x%08x expected=0xfd080319 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e48 & 0xffffffff
      if $soc_actual != 0x01000ed5
        printf "Mismatch at 0x80001e48: got=0x%08x expected=0x01000ed5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e4c & 0xffffffff
      if $soc_actual != 0xf6081de1
        printf "Mismatch at 0x80001e4c: got=0x%08x expected=0xf6081de1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e50 & 0xffffffff
      if $soc_actual != 0x01282303
        printf "Mismatch at 0x80001e50: got=0x%08x expected=0x01282303 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e54 & 0xffffffff
      if $soc_actual != 0xdd18050c
        printf "Mismatch at 0x80001e54: got=0x%08x expected=0xdd18050c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e58 & 0xffffffff
      if $soc_actual != 0x01f31100
        printf "Mismatch at 0x80001e58: got=0x%08x expected=0x01f31100 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e5c & 0xffffffff
      if $soc_actual != 0x00f9210f
        printf "Mismatch at 0x80001e5c: got=0x%08x expected=0x00f9210f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e60 & 0xffffffff
      if $soc_actual != 0x07f81bfd
        printf "Mismatch at 0x80001e60: got=0x%08x expected=0x07f81bfd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e64 & 0x000000ff
      if $soc_actual != 0x00000028
        printf "Mismatch at 0x80001e64: got=0x%08x expected=0x00000028 mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e68 & 0xffffffff
      if $soc_actual != 0xf50b04f2
        printf "Mismatch at 0x80001e68: got=0x%08x expected=0xf50b04f2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e6c & 0xffffffff
      if $soc_actual != 0xf8f4f401
        printf "Mismatch at 0x80001e6c: got=0x%08x expected=0xf8f4f401 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e70 & 0xffffffff
      if $soc_actual != 0x19040909
        printf "Mismatch at 0x80001e70: got=0x%08x expected=0x19040909 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e74 & 0xffffffff
      if $soc_actual != 0x16daff1d
        printf "Mismatch at 0x80001e74: got=0x%08x expected=0x16daff1d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e78 & 0xffffffff
      if $soc_actual != 0x00051b0a
        printf "Mismatch at 0x80001e78: got=0x%08x expected=0x00051b0a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e7c & 0xffffffff
      if $soc_actual != 0x0d0efef4
        printf "Mismatch at 0x80001e7c: got=0x%08x expected=0x0d0efef4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e80 & 0xffffffff
      if $soc_actual != 0xf3dfea20
        printf "Mismatch at 0x80001e80: got=0x%08x expected=0xf3dfea20 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e84 & 0xffffffff
      if $soc_actual != 0xf8f8ec10
        printf "Mismatch at 0x80001e84: got=0x%08x expected=0xf8f8ec10 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e88 & 0x000000ff
      if $soc_actual != 0x00000006
        printf "Mismatch at 0x80001e88: got=0x%08x expected=0x00000006 mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e8c & 0xffffffff
      if $soc_actual != 0xed0f05c9
        printf "Mismatch at 0x80001e8c: got=0x%08x expected=0xed0f05c9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e90 & 0xffffffff
      if $soc_actual != 0xf0e8da2d
        printf "Mismatch at 0x80001e90: got=0x%08x expected=0xf0e8da2d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e94 & 0xffffffff
      if $soc_actual != 0x3c00f631
        printf "Mismatch at 0x80001e94: got=0x%08x expected=0x3c00f631 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e98 & 0xffffffff
      if $soc_actual != 0x2c8bdb37
        printf "Mismatch at 0x80001e98: got=0x%08x expected=0x2c8bdb37 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e9c & 0xffffffff
      if $soc_actual != 0x22f33107
        printf "Mismatch at 0x80001e9c: got=0x%08x expected=0x22f33107 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea0 & 0xffffffff
      if $soc_actual != 0x1a2aeae8
        printf "Mismatch at 0x80001ea0: got=0x%08x expected=0x1a2aeae8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea4 & 0xffffffff
      if $soc_actual != 0xe7c4b330
        printf "Mismatch at 0x80001ea4: got=0x%08x expected=0xe7c4b330 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea8 & 0xffffffff
      if $soc_actual != 0xe8f8bc24
        printf "Mismatch at 0x80001ea8: got=0x%08x expected=0xe8f8bc24 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eac & 0x000000ff
      if $soc_actual != 0x000000e4
        printf "Mismatch at 0x80001eac: got=0x%08x expected=0x000000e4 mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb0 & 0xffffffff
      if $soc_actual != 0x84838281
        printf "Mismatch at 0x80001eb0: got=0x%08x expected=0x84838281 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb4 & 0xffffffff
      if $soc_actual != 0x88878685
        printf "Mismatch at 0x80001eb4: got=0x%08x expected=0x88878685 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb8 & 0xffffffff
      if $soc_actual != 0x8c8b8a89
        printf "Mismatch at 0x80001eb8: got=0x%08x expected=0x8c8b8a89 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ebc & 0xffffffff
      if $soc_actual != 0x908f8e8d
        printf "Mismatch at 0x80001ebc: got=0x%08x expected=0x908f8e8d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec0 & 0xffffffff
      if $soc_actual != 0x94939291
        printf "Mismatch at 0x80001ec0: got=0x%08x expected=0x94939291 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec4 & 0xffffffff
      if $soc_actual != 0x98979695
        printf "Mismatch at 0x80001ec4: got=0x%08x expected=0x98979695 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec8 & 0xffffffff
      if $soc_actual != 0x9b9a9a99
        printf "Mismatch at 0x80001ec8: got=0x%08x expected=0x9b9a9a99 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ecc & 0xffffffff
      if $soc_actual != 0x9f9e9d9c
        printf "Mismatch at 0x80001ecc: got=0x%08x expected=0x9f9e9d9c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed0 & 0xffffffff
      if $soc_actual != 0xa3a2a1a0
        printf "Mismatch at 0x80001ed0: got=0x%08x expected=0xa3a2a1a0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed4 & 0xffffffff
      if $soc_actual != 0xa7a6a5a4
        printf "Mismatch at 0x80001ed4: got=0x%08x expected=0xa7a6a5a4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed8 & 0xffffffff
      if $soc_actual != 0xabaaa9a8
        printf "Mismatch at 0x80001ed8: got=0x%08x expected=0xabaaa9a8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001edc & 0xffffffff
      if $soc_actual != 0xafaeadac
        printf "Mismatch at 0x80001edc: got=0x%08x expected=0xafaeadac mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee0 & 0xffffffff
      if $soc_actual != 0xb3b2b1b0
        printf "Mismatch at 0x80001ee0: got=0x%08x expected=0xb3b2b1b0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee4 & 0xffffffff
      if $soc_actual != 0xb7b6b5b4
        printf "Mismatch at 0x80001ee4: got=0x%08x expected=0xb7b6b5b4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee8 & 0xffffffff
      if $soc_actual != 0xbbbab9b8
        printf "Mismatch at 0x80001ee8: got=0x%08x expected=0xbbbab9b8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eec & 0xffffffff
      if $soc_actual != 0xbfbebdbc
        printf "Mismatch at 0x80001eec: got=0x%08x expected=0xbfbebdbc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef0 & 0x000000ff
      if $soc_actual != 0x000000c0
        printf "Mismatch at 0x80001ef0: got=0x%08x expected=0x000000c0 mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef4 & 0xffffffff
      if $soc_actual != 0xc4c3c2c1
        printf "Mismatch at 0x80001ef4: got=0x%08x expected=0xc4c3c2c1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef8 & 0xffffffff
      if $soc_actual != 0xc8c7c6c5
        printf "Mismatch at 0x80001ef8: got=0x%08x expected=0xc8c7c6c5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001efc & 0xffffffff
      if $soc_actual != 0xcccbcac9
        printf "Mismatch at 0x80001efc: got=0x%08x expected=0xcccbcac9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f00 & 0xffffffff
      if $soc_actual != 0xcfcecdcd
        printf "Mismatch at 0x80001f00: got=0x%08x expected=0xcfcecdcd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f04 & 0xffffffff
      if $soc_actual != 0xd3d2d1d0
        printf "Mismatch at 0x80001f04: got=0x%08x expected=0xd3d2d1d0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f08 & 0xffffffff
      if $soc_actual != 0xd7d6d5d4
        printf "Mismatch at 0x80001f08: got=0x%08x expected=0xd7d6d5d4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f0c & 0xffffffff
      if $soc_actual != 0xdbdad9d8
        printf "Mismatch at 0x80001f0c: got=0x%08x expected=0xdbdad9d8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f10 & 0xffffffff
      if $soc_actual != 0xdfdedddc
        printf "Mismatch at 0x80001f10: got=0x%08x expected=0xdfdedddc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f14 & 0xffffffff
      if $soc_actual != 0xe3e2e1e0
        printf "Mismatch at 0x80001f14: got=0x%08x expected=0xe3e2e1e0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f18 & 0xffffffff
      if $soc_actual != 0xe7e6e5e4
        printf "Mismatch at 0x80001f18: got=0x%08x expected=0xe7e6e5e4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f1c & 0xffffffff
      if $soc_actual != 0xebeae9e8
        printf "Mismatch at 0x80001f1c: got=0x%08x expected=0xebeae9e8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f20 & 0xffffffff
      if $soc_actual != 0xefeeedec
        printf "Mismatch at 0x80001f20: got=0x%08x expected=0xefeeedec mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f24 & 0xffffffff
      if $soc_actual != 0xf3f2f1f0
        printf "Mismatch at 0x80001f24: got=0x%08x expected=0xf3f2f1f0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f28 & 0xffffffff
      if $soc_actual != 0xf7f6f5f4
        printf "Mismatch at 0x80001f28: got=0x%08x expected=0xf7f6f5f4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f2c & 0xffffffff
      if $soc_actual != 0xfbfaf9f8
        printf "Mismatch at 0x80001f2c: got=0x%08x expected=0xfbfaf9f8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f30 & 0xffffffff
      if $soc_actual != 0xfffefdfc
        printf "Mismatch at 0x80001f30: got=0x%08x expected=0xfffefdfc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f34 & 0x000000ff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001f34: got=0x%08x expected=0x00000000 mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f38 & 0xffffffff
      if $soc_actual != 0x03020100
        printf "Mismatch at 0x80001f38: got=0x%08x expected=0x03020100 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f3c & 0xffffffff
      if $soc_actual != 0x07060504
        printf "Mismatch at 0x80001f3c: got=0x%08x expected=0x07060504 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f40 & 0xffffffff
      if $soc_actual != 0x0b0a0908
        printf "Mismatch at 0x80001f40: got=0x%08x expected=0x0b0a0908 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f44 & 0xffffffff
      if $soc_actual != 0x0f0e0d0c
        printf "Mismatch at 0x80001f44: got=0x%08x expected=0x0f0e0d0c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f48 & 0xffffffff
      if $soc_actual != 0x13121110
        printf "Mismatch at 0x80001f48: got=0x%08x expected=0x13121110 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f4c & 0xffffffff
      if $soc_actual != 0x17161514
        printf "Mismatch at 0x80001f4c: got=0x%08x expected=0x17161514 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f50 & 0xffffffff
      if $soc_actual != 0x1b1a1918
        printf "Mismatch at 0x80001f50: got=0x%08x expected=0x1b1a1918 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f54 & 0xffffffff
      if $soc_actual != 0x1f1e1d1c
        printf "Mismatch at 0x80001f54: got=0x%08x expected=0x1f1e1d1c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f58 & 0xffffffff
      if $soc_actual != 0x23222120
        printf "Mismatch at 0x80001f58: got=0x%08x expected=0x23222120 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f5c & 0xffffffff
      if $soc_actual != 0x27262524
        printf "Mismatch at 0x80001f5c: got=0x%08x expected=0x27262524 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f60 & 0xffffffff
      if $soc_actual != 0x2b2a2928
        printf "Mismatch at 0x80001f60: got=0x%08x expected=0x2b2a2928 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f64 & 0xffffffff
      if $soc_actual != 0x2f2e2d2c
        printf "Mismatch at 0x80001f64: got=0x%08x expected=0x2f2e2d2c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f68 & 0xffffffff
      if $soc_actual != 0x33323130
        printf "Mismatch at 0x80001f68: got=0x%08x expected=0x33323130 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f6c & 0xffffffff
      if $soc_actual != 0x36353433
        printf "Mismatch at 0x80001f6c: got=0x%08x expected=0x36353433 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f70 & 0xffffffff
      if $soc_actual != 0x3a393837
        printf "Mismatch at 0x80001f70: got=0x%08x expected=0x3a393837 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f74 & 0xffffffff
      if $soc_actual != 0x3e3d3c3b
        printf "Mismatch at 0x80001f74: got=0x%08x expected=0x3e3d3c3b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f78 & 0x000000ff
      if $soc_actual != 0x0000003f
        printf "Mismatch at 0x80001f78: got=0x%08x expected=0x0000003f mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f7c & 0xffffffff
      if $soc_actual != 0x43424140
        printf "Mismatch at 0x80001f7c: got=0x%08x expected=0x43424140 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f80 & 0xffffffff
      if $soc_actual != 0x47464544
        printf "Mismatch at 0x80001f80: got=0x%08x expected=0x47464544 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f84 & 0xffffffff
      if $soc_actual != 0x4b4a4948
        printf "Mismatch at 0x80001f84: got=0x%08x expected=0x4b4a4948 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f88 & 0xffffffff
      if $soc_actual != 0x4f4e4d4c
        printf "Mismatch at 0x80001f88: got=0x%08x expected=0x4f4e4d4c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f8c & 0xffffffff
      if $soc_actual != 0x53525150
        printf "Mismatch at 0x80001f8c: got=0x%08x expected=0x53525150 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f90 & 0xffffffff
      if $soc_actual != 0x57565554
        printf "Mismatch at 0x80001f90: got=0x%08x expected=0x57565554 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f94 & 0xffffffff
      if $soc_actual != 0x5b5a5958
        printf "Mismatch at 0x80001f94: got=0x%08x expected=0x5b5a5958 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f98 & 0xffffffff
      if $soc_actual != 0x5f5e5d5c
        printf "Mismatch at 0x80001f98: got=0x%08x expected=0x5f5e5d5c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f9c & 0xffffffff
      if $soc_actual != 0x63626160
        printf "Mismatch at 0x80001f9c: got=0x%08x expected=0x63626160 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa0 & 0xffffffff
      if $soc_actual != 0x66666564
        printf "Mismatch at 0x80001fa0: got=0x%08x expected=0x66666564 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa4 & 0xffffffff
      if $soc_actual != 0x6a696867
        printf "Mismatch at 0x80001fa4: got=0x%08x expected=0x6a696867 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa8 & 0xffffffff
      if $soc_actual != 0x6e6d6c6b
        printf "Mismatch at 0x80001fa8: got=0x%08x expected=0x6e6d6c6b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fac & 0xffffffff
      if $soc_actual != 0x7271706f
        printf "Mismatch at 0x80001fac: got=0x%08x expected=0x7271706f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb0 & 0xffffffff
      if $soc_actual != 0x76757473
        printf "Mismatch at 0x80001fb0: got=0x%08x expected=0x76757473 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb4 & 0xffffffff
      if $soc_actual != 0x7a797877
        printf "Mismatch at 0x80001fb4: got=0x%08x expected=0x7a797877 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb8 & 0xffffffff
      if $soc_actual != 0x7e7d7c7b
        printf "Mismatch at 0x80001fb8: got=0x%08x expected=0x7e7d7c7b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fbc & 0x000000ff
      if $soc_actual != 0x0000007f
        printf "Mismatch at 0x80001fbc: got=0x%08x expected=0x0000007f mask=0x000000ff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS raw_tail_b4_cpu checked_words=104 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
