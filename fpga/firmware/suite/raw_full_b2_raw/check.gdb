# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0xb3e99fac
    printf "FPGA_CHECK_FAIL: wrong image tag for raw_full_b2_raw\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001f00 & 0xffffffff
      if $soc_actual != 0x36d3d0d3
        printf "Mismatch at 0x80001f00: got=0x%08x expected=0x36d3d0d3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f04 & 0xffffffff
      if $soc_actual != 0xe33736f6
        printf "Mismatch at 0x80001f04: got=0x%08x expected=0xe33736f6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f08 & 0xffffffff
      if $soc_actual != 0x1e1c16b3
        printf "Mismatch at 0x80001f08: got=0x%08x expected=0x1e1c16b3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f0c & 0xffffffff
      if $soc_actual != 0x200af3ee
        printf "Mismatch at 0x80001f0c: got=0x%08x expected=0x200af3ee mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f10 & 0xffffffff
      if $soc_actual != 0x99ed0335
        printf "Mismatch at 0x80001f10: got=0x%08x expected=0x99ed0335 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f14 & 0xffffffff
      if $soc_actual != 0xe7a814f2
        printf "Mismatch at 0x80001f14: got=0x%08x expected=0xe7a814f2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f18 & 0xffffffff
      if $soc_actual != 0x62f14312
        printf "Mismatch at 0x80001f18: got=0x%08x expected=0x62f14312 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f1c & 0xffffffff
      if $soc_actual != 0xced80bb9
        printf "Mismatch at 0x80001f1c: got=0x%08x expected=0xced80bb9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f20 & 0xffffffff
      if $soc_actual != 0xaa00ee07
        printf "Mismatch at 0x80001f20: got=0x%08x expected=0xaa00ee07 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f24 & 0xffffffff
      if $soc_actual != 0xee81db26
        printf "Mismatch at 0x80001f24: got=0x%08x expected=0xee81db26 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f28 & 0xffffffff
      if $soc_actual != 0x4206e601
        printf "Mismatch at 0x80001f28: got=0x%08x expected=0x4206e601 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f2c & 0xffffffff
      if $soc_actual != 0x1042efe8
        printf "Mismatch at 0x80001f2c: got=0x%08x expected=0x1042efe8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f30 & 0xffffffff
      if $soc_actual != 0x63e106f3
        printf "Mismatch at 0x80001f30: got=0x%08x expected=0x63e106f3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f34 & 0xffffffff
      if $soc_actual != 0x4757de04
        printf "Mismatch at 0x80001f34: got=0x%08x expected=0x4757de04 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f38 & 0xffffffff
      if $soc_actual != 0xa3dfe329
        printf "Mismatch at 0x80001f38: got=0x%08x expected=0xa3dfe329 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f3c & 0xffffffff
      if $soc_actual != 0x25d71216
        printf "Mismatch at 0x80001f3c: got=0x%08x expected=0x25d71216 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f40 & 0xffffffff
      if $soc_actual != 0x87858381
        printf "Mismatch at 0x80001f40: got=0x%08x expected=0x87858381 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f44 & 0xffffffff
      if $soc_actual != 0x8f8d8b89
        printf "Mismatch at 0x80001f44: got=0x%08x expected=0x8f8d8b89 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f48 & 0xffffffff
      if $soc_actual != 0x97959391
        printf "Mismatch at 0x80001f48: got=0x%08x expected=0x97959391 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f4c & 0xffffffff
      if $soc_actual != 0x9f9d9b99
        printf "Mismatch at 0x80001f4c: got=0x%08x expected=0x9f9d9b99 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f50 & 0xffffffff
      if $soc_actual != 0xa7a5a3a1
        printf "Mismatch at 0x80001f50: got=0x%08x expected=0xa7a5a3a1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f54 & 0xffffffff
      if $soc_actual != 0xafadaba9
        printf "Mismatch at 0x80001f54: got=0x%08x expected=0xafadaba9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f58 & 0xffffffff
      if $soc_actual != 0xb7b5b3b1
        printf "Mismatch at 0x80001f58: got=0x%08x expected=0xb7b5b3b1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f5c & 0xffffffff
      if $soc_actual != 0xbfbdbbb9
        printf "Mismatch at 0x80001f5c: got=0x%08x expected=0xbfbdbbb9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f60 & 0xffffffff
      if $soc_actual != 0xc7c5c3c1
        printf "Mismatch at 0x80001f60: got=0x%08x expected=0xc7c5c3c1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f64 & 0xffffffff
      if $soc_actual != 0xcfcdcbc9
        printf "Mismatch at 0x80001f64: got=0x%08x expected=0xcfcdcbc9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f68 & 0xffffffff
      if $soc_actual != 0xd7d5d3d1
        printf "Mismatch at 0x80001f68: got=0x%08x expected=0xd7d5d3d1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f6c & 0xffffffff
      if $soc_actual != 0xdfdddbd9
        printf "Mismatch at 0x80001f6c: got=0x%08x expected=0xdfdddbd9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f70 & 0xffffffff
      if $soc_actual != 0xe7e5e3e1
        printf "Mismatch at 0x80001f70: got=0x%08x expected=0xe7e5e3e1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f74 & 0xffffffff
      if $soc_actual != 0xefedebe9
        printf "Mismatch at 0x80001f74: got=0x%08x expected=0xefedebe9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f78 & 0xffffffff
      if $soc_actual != 0xf7f5f3f1
        printf "Mismatch at 0x80001f78: got=0x%08x expected=0xf7f5f3f1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f7c & 0xffffffff
      if $soc_actual != 0xfffdfbf9
        printf "Mismatch at 0x80001f7c: got=0x%08x expected=0xfffdfbf9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f80 & 0xffffffff
      if $soc_actual != 0x07050301
        printf "Mismatch at 0x80001f80: got=0x%08x expected=0x07050301 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f84 & 0xffffffff
      if $soc_actual != 0x0f0d0b09
        printf "Mismatch at 0x80001f84: got=0x%08x expected=0x0f0d0b09 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f88 & 0xffffffff
      if $soc_actual != 0x17151311
        printf "Mismatch at 0x80001f88: got=0x%08x expected=0x17151311 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f8c & 0xffffffff
      if $soc_actual != 0x1f1d1b19
        printf "Mismatch at 0x80001f8c: got=0x%08x expected=0x1f1d1b19 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f90 & 0xffffffff
      if $soc_actual != 0x27252321
        printf "Mismatch at 0x80001f90: got=0x%08x expected=0x27252321 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f94 & 0xffffffff
      if $soc_actual != 0x2f2d2b29
        printf "Mismatch at 0x80001f94: got=0x%08x expected=0x2f2d2b29 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f98 & 0xffffffff
      if $soc_actual != 0x37353331
        printf "Mismatch at 0x80001f98: got=0x%08x expected=0x37353331 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f9c & 0xffffffff
      if $soc_actual != 0x3f3d3b39
        printf "Mismatch at 0x80001f9c: got=0x%08x expected=0x3f3d3b39 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa0 & 0xffffffff
      if $soc_actual != 0x47454341
        printf "Mismatch at 0x80001fa0: got=0x%08x expected=0x47454341 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa4 & 0xffffffff
      if $soc_actual != 0x4f4d4b49
        printf "Mismatch at 0x80001fa4: got=0x%08x expected=0x4f4d4b49 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa8 & 0xffffffff
      if $soc_actual != 0x57555351
        printf "Mismatch at 0x80001fa8: got=0x%08x expected=0x57555351 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fac & 0xffffffff
      if $soc_actual != 0x5f5d5b59
        printf "Mismatch at 0x80001fac: got=0x%08x expected=0x5f5d5b59 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb0 & 0xffffffff
      if $soc_actual != 0x67656361
        printf "Mismatch at 0x80001fb0: got=0x%08x expected=0x67656361 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb4 & 0xffffffff
      if $soc_actual != 0x6f6d6b69
        printf "Mismatch at 0x80001fb4: got=0x%08x expected=0x6f6d6b69 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb8 & 0xffffffff
      if $soc_actual != 0x77757371
        printf "Mismatch at 0x80001fb8: got=0x%08x expected=0x77757371 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fbc & 0xffffffff
      if $soc_actual != 0x7f7d7b79
        printf "Mismatch at 0x80001fbc: got=0x%08x expected=0x7f7d7b79 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS raw_full_b2_raw checked_words=48 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
