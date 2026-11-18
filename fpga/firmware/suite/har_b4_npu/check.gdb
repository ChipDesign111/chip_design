# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0xf999fc8f
    printf "FPGA_CHECK_FAIL: wrong image tag for har_b4_npu\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001d00 & 0xffffffff
      if $soc_actual != 0x0a24000f
        printf "Mismatch at 0x80001d00: got=0x%08x expected=0x0a24000f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d04 & 0xffffffff
      if $soc_actual != 0x00261332
        printf "Mismatch at 0x80001d04: got=0x%08x expected=0x00261332 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d08 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001d08: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d0c & 0xffffffff
      if $soc_actual != 0x1e0b2717
        printf "Mismatch at 0x80001d0c: got=0x%08x expected=0x1e0b2717 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d10 & 0xffffffff
      if $soc_actual != 0x00080a00
        printf "Mismatch at 0x80001d10: got=0x%08x expected=0x00080a00 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d14 & 0xffffffff
      if $soc_actual != 0x0a170c1c
        printf "Mismatch at 0x80001d14: got=0x%08x expected=0x0a170c1c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d18 & 0xffffffff
      if $soc_actual != 0x0f002622
        printf "Mismatch at 0x80001d18: got=0x%08x expected=0x0f002622 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d1c & 0xffffffff
      if $soc_actual != 0x27002735
        printf "Mismatch at 0x80001d1c: got=0x%08x expected=0x27002735 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d20 & 0xffffffff
      if $soc_actual != 0x00001bed
        printf "Mismatch at 0x80001d20: got=0x%08x expected=0x00001bed mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d24 & 0xffffffff
      if $soc_actual != 0x00000126
        printf "Mismatch at 0x80001d24: got=0x%08x expected=0x00000126 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d28 & 0xffffffff
      if $soc_actual != 0xfffff901
        printf "Mismatch at 0x80001d28: got=0x%08x expected=0xfffff901 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d2c & 0xffffffff
      if $soc_actual != 0xffffde1d
        printf "Mismatch at 0x80001d2c: got=0x%08x expected=0xffffde1d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d30 & 0xffffffff
      if $soc_actual != 0xffffe6c8
        printf "Mismatch at 0x80001d30: got=0x%08x expected=0xffffe6c8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d34 & 0xffffffff
      if $soc_actual != 0xffffccf4
        printf "Mismatch at 0x80001d34: got=0x%08x expected=0xffffccf4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d38 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001d38: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d40 & 0xffffffff
      if $soc_actual != 0x09280204
        printf "Mismatch at 0x80001d40: got=0x%08x expected=0x09280204 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d44 & 0xffffffff
      if $soc_actual != 0x00220b2a
        printf "Mismatch at 0x80001d44: got=0x%08x expected=0x00220b2a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d48 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001d48: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d4c & 0xffffffff
      if $soc_actual != 0x1d13231d
        printf "Mismatch at 0x80001d4c: got=0x%08x expected=0x1d13231d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d50 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001d50: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d54 & 0xffffffff
      if $soc_actual != 0x08161010
        printf "Mismatch at 0x80001d54: got=0x%08x expected=0x08161010 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d58 & 0xffffffff
      if $soc_actual != 0x0900261a
        printf "Mismatch at 0x80001d58: got=0x%08x expected=0x0900261a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d5c & 0xffffffff
      if $soc_actual != 0x24002439
        printf "Mismatch at 0x80001d5c: got=0x%08x expected=0x24002439 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d60 & 0xffffffff
      if $soc_actual != 0x000022d4
        printf "Mismatch at 0x80001d60: got=0x%08x expected=0x000022d4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d64 & 0xffffffff
      if $soc_actual != 0x00000325
        printf "Mismatch at 0x80001d64: got=0x%08x expected=0x00000325 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d68 & 0xffffffff
      if $soc_actual != 0xfffffb3d
        printf "Mismatch at 0x80001d68: got=0x%08x expected=0xfffffb3d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d6c & 0xffffffff
      if $soc_actual != 0xffffdbb8
        printf "Mismatch at 0x80001d6c: got=0x%08x expected=0xffffdbb8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d70 & 0xffffffff
      if $soc_actual != 0xffffe385
        printf "Mismatch at 0x80001d70: got=0x%08x expected=0xffffe385 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d74 & 0xffffffff
      if $soc_actual != 0xffffd1be
        printf "Mismatch at 0x80001d74: got=0x%08x expected=0xffffd1be mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d78 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001d78: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d80 & 0xffffffff
      if $soc_actual != 0x082d0000
        printf "Mismatch at 0x80001d80: got=0x%08x expected=0x082d0000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d84 & 0xffffffff
      if $soc_actual != 0x001f0a2d
        printf "Mismatch at 0x80001d84: got=0x%08x expected=0x001f0a2d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d88 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001d88: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d8c & 0xffffffff
      if $soc_actual != 0x17162420
        printf "Mismatch at 0x80001d8c: got=0x%08x expected=0x17162420 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d90 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001d90: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d94 & 0xffffffff
      if $soc_actual != 0x031c0711
        printf "Mismatch at 0x80001d94: got=0x%08x expected=0x031c0711 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d98 & 0xffffffff
      if $soc_actual != 0x09002817
        printf "Mismatch at 0x80001d98: got=0x%08x expected=0x09002817 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d9c & 0xffffffff
      if $soc_actual != 0x2700283d
        printf "Mismatch at 0x80001d9c: got=0x%08x expected=0x2700283d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001da0 & 0xffffffff
      if $soc_actual != 0x000026c4
        printf "Mismatch at 0x80001da0: got=0x%08x expected=0x000026c4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001da4 & 0xffffffff
      if $soc_actual != 0x00000d07
        printf "Mismatch at 0x80001da4: got=0x%08x expected=0x00000d07 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001da8 & 0xffffffff
      if $soc_actual != 0xfffff4f1
        printf "Mismatch at 0x80001da8: got=0x%08x expected=0xfffff4f1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dac & 0xffffffff
      if $soc_actual != 0xffffd8e1
        printf "Mismatch at 0x80001dac: got=0x%08x expected=0xffffd8e1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001db0 & 0xffffffff
      if $soc_actual != 0xffffe219
        printf "Mismatch at 0x80001db0: got=0x%08x expected=0xffffe219 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001db4 & 0xffffffff
      if $soc_actual != 0xffffd212
        printf "Mismatch at 0x80001db4: got=0x%08x expected=0xffffd212 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001db8 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001db8: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc0 & 0xffffffff
      if $soc_actual != 0x081e001b
        printf "Mismatch at 0x80001dc0: got=0x%08x expected=0x081e001b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc4 & 0xffffffff
      if $soc_actual != 0x002d1533
        printf "Mismatch at 0x80001dc4: got=0x%08x expected=0x002d1533 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc8 & 0xffffffff
      if $soc_actual != 0x00000004
        printf "Mismatch at 0x80001dc8: got=0x%08x expected=0x00000004 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dcc & 0xffffffff
      if $soc_actual != 0x1e092811
        printf "Mismatch at 0x80001dcc: got=0x%08x expected=0x1e092811 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd0 & 0xffffffff
      if $soc_actual != 0x00131500
        printf "Mismatch at 0x80001dd0: got=0x%08x expected=0x00131500 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd4 & 0xffffffff
      if $soc_actual != 0x080f0e25
        printf "Mismatch at 0x80001dd4: got=0x%08x expected=0x080f0e25 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd8 & 0xffffffff
      if $soc_actual != 0x0e00242b
        printf "Mismatch at 0x80001dd8: got=0x%08x expected=0x0e00242b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ddc & 0xffffffff
      if $soc_actual != 0x24002a30
        printf "Mismatch at 0x80001ddc: got=0x%08x expected=0x24002a30 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de0 & 0xffffffff
      if $soc_actual != 0x000013e9
        printf "Mismatch at 0x80001de0: got=0x%08x expected=0x000013e9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de4 & 0xffffffff
      if $soc_actual != 0xfffff7cf
        printf "Mismatch at 0x80001de4: got=0x%08x expected=0xfffff7cf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de8 & 0xffffffff
      if $soc_actual != 0xfffff7b3
        printf "Mismatch at 0x80001de8: got=0x%08x expected=0xfffff7b3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dec & 0xffffffff
      if $soc_actual != 0xffffe497
        printf "Mismatch at 0x80001dec: got=0x%08x expected=0xffffe497 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df0 & 0xffffffff
      if $soc_actual != 0xffffed57
        printf "Mismatch at 0x80001df0: got=0x%08x expected=0xffffed57 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df4 & 0xffffffff
      if $soc_actual != 0xffffc65f
        printf "Mismatch at 0x80001df4: got=0x%08x expected=0xffffc65f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df8 & 0xffffffff
      if $soc_actual != 0x00000000
        printf "Mismatch at 0x80001df8: got=0x%08x expected=0x00000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS har_b4_npu checked_words=60 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
