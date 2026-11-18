# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0xb93def68
    printf "FPGA_CHECK_FAIL: wrong image tag for raw_full_b3_cpu\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001ea0 & 0xffffffff
      if $soc_actual != 0x43d9d8d3
        printf "Mismatch at 0x80001ea0: got=0x%08x expected=0x43d9d8d3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea4 & 0xffffffff
      if $soc_actual != 0xe9513aef
        printf "Mismatch at 0x80001ea4: got=0x%08x expected=0xe9513aef mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea8 & 0xffffffff
      if $soc_actual != 0x0b181abc
        printf "Mismatch at 0x80001ea8: got=0x%08x expected=0x0b181abc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eac & 0xffffffff
      if $soc_actual != 0x17f9fdf4
        printf "Mismatch at 0x80001eac: got=0x%08x expected=0x17f9fdf4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb0 & 0xffffffff
      if $soc_actual != 0x8df70432
        printf "Mismatch at 0x80001eb0: got=0x%08x expected=0x8df70432 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb4 & 0xffffffff
      if $soc_actual != 0xdb9e19f4
        printf "Mismatch at 0x80001eb4: got=0x%08x expected=0xdb9e19f4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb8 & 0xffffffff
      if $soc_actual != 0x70fa4404
        printf "Mismatch at 0x80001eb8: got=0x%08x expected=0x70fa4404 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ebc & 0xffffffff
      if $soc_actual != 0xcfea01bf
        printf "Mismatch at 0x80001ebc: got=0x%08x expected=0xcfea01bf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec0 & 0xffffffff
      if $soc_actual != 0xf3f2e9f1
        printf "Mismatch at 0x80001ec0: got=0x%08x expected=0xf3f2e9f1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec4 & 0xffffffff
      if $soc_actual != 0xf0e9050b
        printf "Mismatch at 0x80001ec4: got=0x%08x expected=0xf0e9050b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec8 & 0xffffffff
      if $soc_actual != 0x1f0bffe9
        printf "Mismatch at 0x80001ec8: got=0x%08x expected=0x1f0bffe9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ecc & 0xffffffff
      if $soc_actual != 0x0e1afbf0
        printf "Mismatch at 0x80001ecc: got=0x%08x expected=0x0e1afbf0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed0 & 0xffffffff
      if $soc_actual != 0x01f0060c
        printf "Mismatch at 0x80001ed0: got=0x%08x expected=0x01f0060c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed4 & 0xffffffff
      if $soc_actual != 0x1102fafe
        printf "Mismatch at 0x80001ed4: got=0x%08x expected=0x1102fafe mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed8 & 0xffffffff
      if $soc_actual != 0x03f00e11
        printf "Mismatch at 0x80001ed8: got=0x%08x expected=0x03f00e11 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001edc & 0xffffffff
      if $soc_actual != 0x00e905f4
        printf "Mismatch at 0x80001edc: got=0x%08x expected=0x00e905f4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee0 & 0xffffffff
      if $soc_actual != 0xa30cfb0f
        printf "Mismatch at 0x80001ee0: got=0x%08x expected=0xa30cfb0f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee4 & 0xffffffff
      if $soc_actual != 0xf681d026
        printf "Mismatch at 0x80001ee4: got=0x%08x expected=0xf681d026 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee8 & 0xffffffff
      if $soc_actual != 0x34fee316
        printf "Mismatch at 0x80001ee8: got=0x%08x expected=0x34fee316 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eec & 0xffffffff
      if $soc_actual != 0x053af9ec
        printf "Mismatch at 0x80001eec: got=0x%08x expected=0x053af9ec mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef0 & 0xffffffff
      if $soc_actual != 0x74ea07e6
        printf "Mismatch at 0x80001ef0: got=0x%08x expected=0x74ea07e6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef4 & 0xffffffff
      if $soc_actual != 0x4765da08
        printf "Mismatch at 0x80001ef4: got=0x%08x expected=0x4765da08 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef8 & 0xffffffff
      if $soc_actual != 0x96e5d81e
        printf "Mismatch at 0x80001ef8: got=0x%08x expected=0x96e5d81e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001efc & 0xffffffff
      if $soc_actual != 0x32e90929
        printf "Mismatch at 0x80001efc: got=0x%08x expected=0x32e90929 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f00 & 0xffffffff
      if $soc_actual != 0x85848281
        printf "Mismatch at 0x80001f00: got=0x%08x expected=0x85848281 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f04 & 0xffffffff
      if $soc_actual != 0x8a898886
        printf "Mismatch at 0x80001f04: got=0x%08x expected=0x8a898886 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f08 & 0xffffffff
      if $soc_actual != 0x908e8d8c
        printf "Mismatch at 0x80001f08: got=0x%08x expected=0x908e8d8c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f0c & 0xffffffff
      if $soc_actual != 0x95949291
        printf "Mismatch at 0x80001f0c: got=0x%08x expected=0x95949291 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f10 & 0xffffffff
      if $soc_actual != 0x9a999896
        printf "Mismatch at 0x80001f10: got=0x%08x expected=0x9a999896 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f14 & 0xffffffff
      if $soc_actual != 0xa09e9d9c
        printf "Mismatch at 0x80001f14: got=0x%08x expected=0xa09e9d9c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f18 & 0xffffffff
      if $soc_actual != 0xa5a4a2a1
        printf "Mismatch at 0x80001f18: got=0x%08x expected=0xa5a4a2a1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f1c & 0xffffffff
      if $soc_actual != 0xaaa9a8a6
        printf "Mismatch at 0x80001f1c: got=0x%08x expected=0xaaa9a8a6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f20 & 0xffffffff
      if $soc_actual != 0xb0aeadac
        printf "Mismatch at 0x80001f20: got=0x%08x expected=0xb0aeadac mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f24 & 0xffffffff
      if $soc_actual != 0xb5b4b2b1
        printf "Mismatch at 0x80001f24: got=0x%08x expected=0xb5b4b2b1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f28 & 0xffffffff
      if $soc_actual != 0xbab9b8b6
        printf "Mismatch at 0x80001f28: got=0x%08x expected=0xbab9b8b6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f2c & 0xffffffff
      if $soc_actual != 0xc0bebdbc
        printf "Mismatch at 0x80001f2c: got=0x%08x expected=0xc0bebdbc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f30 & 0xffffffff
      if $soc_actual != 0xc5c3c2c1
        printf "Mismatch at 0x80001f30: got=0x%08x expected=0xc5c3c2c1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f34 & 0xffffffff
      if $soc_actual != 0xcac9c7c6
        printf "Mismatch at 0x80001f34: got=0x%08x expected=0xcac9c7c6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f38 & 0xffffffff
      if $soc_actual != 0xcfcecdcb
        printf "Mismatch at 0x80001f38: got=0x%08x expected=0xcfcecdcb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f3c & 0xffffffff
      if $soc_actual != 0xd5d3d2d1
        printf "Mismatch at 0x80001f3c: got=0x%08x expected=0xd5d3d2d1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f40 & 0xffffffff
      if $soc_actual != 0xdad9d7d6
        printf "Mismatch at 0x80001f40: got=0x%08x expected=0xdad9d7d6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f44 & 0xffffffff
      if $soc_actual != 0xdfdedddb
        printf "Mismatch at 0x80001f44: got=0x%08x expected=0xdfdedddb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f48 & 0xffffffff
      if $soc_actual != 0xe5e3e2e1
        printf "Mismatch at 0x80001f48: got=0x%08x expected=0xe5e3e2e1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f4c & 0xffffffff
      if $soc_actual != 0xeae9e7e6
        printf "Mismatch at 0x80001f4c: got=0x%08x expected=0xeae9e7e6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f50 & 0xffffffff
      if $soc_actual != 0xefeeedeb
        printf "Mismatch at 0x80001f50: got=0x%08x expected=0xefeeedeb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f54 & 0xffffffff
      if $soc_actual != 0xf5f3f2f1
        printf "Mismatch at 0x80001f54: got=0x%08x expected=0xf5f3f2f1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f58 & 0xffffffff
      if $soc_actual != 0xfaf9f7f6
        printf "Mismatch at 0x80001f58: got=0x%08x expected=0xfaf9f7f6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f5c & 0xffffffff
      if $soc_actual != 0xfffefdfb
        printf "Mismatch at 0x80001f5c: got=0x%08x expected=0xfffefdfb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f60 & 0xffffffff
      if $soc_actual != 0x05030201
        printf "Mismatch at 0x80001f60: got=0x%08x expected=0x05030201 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f64 & 0xffffffff
      if $soc_actual != 0x0a090706
        printf "Mismatch at 0x80001f64: got=0x%08x expected=0x0a090706 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f68 & 0xffffffff
      if $soc_actual != 0x0f0e0d0b
        printf "Mismatch at 0x80001f68: got=0x%08x expected=0x0f0e0d0b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f6c & 0xffffffff
      if $soc_actual != 0x15131211
        printf "Mismatch at 0x80001f6c: got=0x%08x expected=0x15131211 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f70 & 0xffffffff
      if $soc_actual != 0x1a191716
        printf "Mismatch at 0x80001f70: got=0x%08x expected=0x1a191716 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f74 & 0xffffffff
      if $soc_actual != 0x1f1e1d1b
        printf "Mismatch at 0x80001f74: got=0x%08x expected=0x1f1e1d1b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f78 & 0xffffffff
      if $soc_actual != 0x25232221
        printf "Mismatch at 0x80001f78: got=0x%08x expected=0x25232221 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f7c & 0xffffffff
      if $soc_actual != 0x2a292726
        printf "Mismatch at 0x80001f7c: got=0x%08x expected=0x2a292726 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f80 & 0xffffffff
      if $soc_actual != 0x2f2e2d2b
        printf "Mismatch at 0x80001f80: got=0x%08x expected=0x2f2e2d2b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f84 & 0xffffffff
      if $soc_actual != 0x35333231
        printf "Mismatch at 0x80001f84: got=0x%08x expected=0x35333231 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f88 & 0xffffffff
      if $soc_actual != 0x3a393736
        printf "Mismatch at 0x80001f88: got=0x%08x expected=0x3a393736 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f8c & 0xffffffff
      if $soc_actual != 0x3f3e3d3b
        printf "Mismatch at 0x80001f8c: got=0x%08x expected=0x3f3e3d3b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f90 & 0xffffffff
      if $soc_actual != 0x44434240
        printf "Mismatch at 0x80001f90: got=0x%08x expected=0x44434240 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f94 & 0xffffffff
      if $soc_actual != 0x4a484746
        printf "Mismatch at 0x80001f94: got=0x%08x expected=0x4a484746 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f98 & 0xffffffff
      if $soc_actual != 0x4f4e4c4b
        printf "Mismatch at 0x80001f98: got=0x%08x expected=0x4f4e4c4b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f9c & 0xffffffff
      if $soc_actual != 0x54535250
        printf "Mismatch at 0x80001f9c: got=0x%08x expected=0x54535250 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa0 & 0xffffffff
      if $soc_actual != 0x5a585756
        printf "Mismatch at 0x80001fa0: got=0x%08x expected=0x5a585756 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa4 & 0xffffffff
      if $soc_actual != 0x5f5e5c5b
        printf "Mismatch at 0x80001fa4: got=0x%08x expected=0x5f5e5c5b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa8 & 0xffffffff
      if $soc_actual != 0x64636260
        printf "Mismatch at 0x80001fa8: got=0x%08x expected=0x64636260 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fac & 0xffffffff
      if $soc_actual != 0x6a686766
        printf "Mismatch at 0x80001fac: got=0x%08x expected=0x6a686766 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb0 & 0xffffffff
      if $soc_actual != 0x6f6e6c6b
        printf "Mismatch at 0x80001fb0: got=0x%08x expected=0x6f6e6c6b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb4 & 0xffffffff
      if $soc_actual != 0x74737270
        printf "Mismatch at 0x80001fb4: got=0x%08x expected=0x74737270 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb8 & 0xffffffff
      if $soc_actual != 0x7a787776
        printf "Mismatch at 0x80001fb8: got=0x%08x expected=0x7a787776 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fbc & 0xffffffff
      if $soc_actual != 0x7f7e7c7b
        printf "Mismatch at 0x80001fbc: got=0x%08x expected=0x7f7e7c7b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS raw_full_b3_cpu checked_words=72 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
