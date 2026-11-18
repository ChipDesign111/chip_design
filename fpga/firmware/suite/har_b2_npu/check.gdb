# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0xbee8885d
    printf "FPGA_CHECK_FAIL: wrong image tag for har_b2_npu\n"
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
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS har_b2_npu checked_words=30 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
