# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0x24584176
    printf "FPGA_CHECK_FAIL: wrong image tag for raw_k_split_b4_cpu\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001d40 & 0xffffffff
      if $soc_actual != 0x1a0f11db
        printf "Mismatch at 0x80001d40: got=0x%08x expected=0x1a0f11db mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d44 & 0xffffffff
      if $soc_actual != 0x07cb2511
        printf "Mismatch at 0x80001d44: got=0x%08x expected=0x07cb2511 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d48 & 0xffffffff
      if $soc_actual != 0x021831be
        printf "Mismatch at 0x80001d48: got=0x%08x expected=0x021831be mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d4c & 0xffffffff
      if $soc_actual != 0xb606c9ff
        printf "Mismatch at 0x80001d4c: got=0x%08x expected=0xb606c9ff mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d50 & 0xffffffff
      if $soc_actual != 0x9ed50803
        printf "Mismatch at 0x80001d50: got=0x%08x expected=0x9ed50803 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d54 & 0xffffffff
      if $soc_actual != 0xae33afba
        printf "Mismatch at 0x80001d54: got=0x%08x expected=0xae33afba mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d58 & 0xffffffff
      if $soc_actual != 0xe91afcdf
        printf "Mismatch at 0x80001d58: got=0x%08x expected=0xe91afcdf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d5c & 0xffffffff
      if $soc_actual != 0x503800f1
        printf "Mismatch at 0x80001d5c: got=0x%08x expected=0x503800f1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d60 & 0xffffffff
      if $soc_actual != 0x0000fcf8
        printf "Mismatch at 0x80001d60: got=0x%08x expected=0x0000fcf8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d64 & 0xffffffff
      if $soc_actual != 0x14f50efa
        printf "Mismatch at 0x80001d64: got=0x%08x expected=0x14f50efa mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d68 & 0xffffffff
      if $soc_actual != 0x020407fe
        printf "Mismatch at 0x80001d68: got=0x%08x expected=0x020407fe mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d6c & 0xffffffff
      if $soc_actual != 0xd60ff301
        printf "Mismatch at 0x80001d6c: got=0x%08x expected=0xd60ff301 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d70 & 0xffffffff
      if $soc_actual != 0xd2f7fc0b
        printf "Mismatch at 0x80001d70: got=0x%08x expected=0xd2f7fc0b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d74 & 0xffffffff
      if $soc_actual != 0xd723dde8
        printf "Mismatch at 0x80001d74: got=0x%08x expected=0xd723dde8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d78 & 0xffffffff
      if $soc_actual != 0xf00bfeef
        printf "Mismatch at 0x80001d78: got=0x%08x expected=0xf00bfeef mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d7c & 0xffffffff
      if $soc_actual != 0x1b170407
        printf "Mismatch at 0x80001d7c: got=0x%08x expected=0x1b170407 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d80 & 0xffffffff
      if $soc_actual != 0xe5f1e715
        printf "Mismatch at 0x80001d80: got=0x%08x expected=0xe5f1e715 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d84 & 0xffffffff
      if $soc_actual != 0x221df7e2
        printf "Mismatch at 0x80001d84: got=0x%08x expected=0x221df7e2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d88 & 0xffffffff
      if $soc_actual != 0x03f1dc3e
        printf "Mismatch at 0x80001d88: got=0x%08x expected=0x03f1dc3e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d8c & 0xffffffff
      if $soc_actual != 0xf6181d04
        printf "Mismatch at 0x80001d8c: got=0x%08x expected=0xf6181d04 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d90 & 0xffffffff
      if $soc_actual != 0x0619f013
        printf "Mismatch at 0x80001d90: got=0x%08x expected=0x0619f013 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d94 & 0xffffffff
      if $soc_actual != 0x01130d15
        printf "Mismatch at 0x80001d94: got=0x%08x expected=0x01130d15 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d98 & 0xffffffff
      if $soc_actual != 0xf7fcfeff
        printf "Mismatch at 0x80001d98: got=0x%08x expected=0xf7fcfeff mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001d9c & 0xffffffff
      if $soc_actual != 0xe7f6091d
        printf "Mismatch at 0x80001d9c: got=0x%08x expected=0xe7f6091d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001da0 & 0xffffffff
      if $soc_actual != 0xcae3d132
        printf "Mismatch at 0x80001da0: got=0x%08x expected=0xcae3d132 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001da4 & 0xffffffff
      if $soc_actual != 0x3046e0cb
        printf "Mismatch at 0x80001da4: got=0x%08x expected=0x3046e0cb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001da8 & 0xffffffff
      if $soc_actual != 0x04deb27f
        printf "Mismatch at 0x80001da8: got=0x%08x expected=0x04deb27f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dac & 0xffffffff
      if $soc_actual != 0x15224707
        printf "Mismatch at 0x80001dac: got=0x%08x expected=0x15224707 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001db0 & 0xffffffff
      if $soc_actual != 0x393ce31d
        printf "Mismatch at 0x80001db0: got=0x%08x expected=0x393ce31d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001db4 & 0xffffffff
      if $soc_actual != 0x2a033b43
        printf "Mismatch at 0x80001db4: got=0x%08x expected=0x2a033b43 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001db8 & 0xffffffff
      if $soc_actual != 0xffedff0f
        printf "Mismatch at 0x80001db8: got=0x%08x expected=0xffedff0f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dbc & 0xffffffff
      if $soc_actual != 0xb3d50d33
        printf "Mismatch at 0x80001dbc: got=0x%08x expected=0xb3d50d33 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc0 & 0xffffffff
      if $soc_actual != 0x82828181
        printf "Mismatch at 0x80001dc0: got=0x%08x expected=0x82828181 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc4 & 0xffffffff
      if $soc_actual != 0x84848383
        printf "Mismatch at 0x80001dc4: got=0x%08x expected=0x84848383 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc8 & 0xffffffff
      if $soc_actual != 0x86868585
        printf "Mismatch at 0x80001dc8: got=0x%08x expected=0x86868585 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dcc & 0xffffffff
      if $soc_actual != 0x88888787
        printf "Mismatch at 0x80001dcc: got=0x%08x expected=0x88888787 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd0 & 0xffffffff
      if $soc_actual != 0x8a8a8989
        printf "Mismatch at 0x80001dd0: got=0x%08x expected=0x8a8a8989 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd4 & 0xffffffff
      if $soc_actual != 0x8c8c8b8b
        printf "Mismatch at 0x80001dd4: got=0x%08x expected=0x8c8c8b8b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd8 & 0xffffffff
      if $soc_actual != 0x8e8e8d8d
        printf "Mismatch at 0x80001dd8: got=0x%08x expected=0x8e8e8d8d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ddc & 0xffffffff
      if $soc_actual != 0x90908f8f
        printf "Mismatch at 0x80001ddc: got=0x%08x expected=0x90908f8f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de0 & 0xffffffff
      if $soc_actual != 0x92929191
        printf "Mismatch at 0x80001de0: got=0x%08x expected=0x92929191 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de4 & 0xffffffff
      if $soc_actual != 0x94949393
        printf "Mismatch at 0x80001de4: got=0x%08x expected=0x94949393 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de8 & 0xffffffff
      if $soc_actual != 0x96969595
        printf "Mismatch at 0x80001de8: got=0x%08x expected=0x96969595 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dec & 0xffffffff
      if $soc_actual != 0x98989797
        printf "Mismatch at 0x80001dec: got=0x%08x expected=0x98989797 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df0 & 0xffffffff
      if $soc_actual != 0x9a9a9999
        printf "Mismatch at 0x80001df0: got=0x%08x expected=0x9a9a9999 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df4 & 0xffffffff
      if $soc_actual != 0x9c9c9b9b
        printf "Mismatch at 0x80001df4: got=0x%08x expected=0x9c9c9b9b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df8 & 0xffffffff
      if $soc_actual != 0x9e9e9d9d
        printf "Mismatch at 0x80001df8: got=0x%08x expected=0x9e9e9d9d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dfc & 0xffffffff
      if $soc_actual != 0xa0a09f9f
        printf "Mismatch at 0x80001dfc: got=0x%08x expected=0xa0a09f9f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e00 & 0xffffffff
      if $soc_actual != 0xa2a2a1a1
        printf "Mismatch at 0x80001e00: got=0x%08x expected=0xa2a2a1a1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e04 & 0xffffffff
      if $soc_actual != 0xa4a4a3a3
        printf "Mismatch at 0x80001e04: got=0x%08x expected=0xa4a4a3a3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e08 & 0xffffffff
      if $soc_actual != 0xa6a6a5a5
        printf "Mismatch at 0x80001e08: got=0x%08x expected=0xa6a6a5a5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e0c & 0xffffffff
      if $soc_actual != 0xa8a8a7a7
        printf "Mismatch at 0x80001e0c: got=0x%08x expected=0xa8a8a7a7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e10 & 0xffffffff
      if $soc_actual != 0xaaaaa9a9
        printf "Mismatch at 0x80001e10: got=0x%08x expected=0xaaaaa9a9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e14 & 0xffffffff
      if $soc_actual != 0xacacabab
        printf "Mismatch at 0x80001e14: got=0x%08x expected=0xacacabab mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e18 & 0xffffffff
      if $soc_actual != 0xaeaeadad
        printf "Mismatch at 0x80001e18: got=0x%08x expected=0xaeaeadad mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e1c & 0xffffffff
      if $soc_actual != 0xb0b0afaf
        printf "Mismatch at 0x80001e1c: got=0x%08x expected=0xb0b0afaf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e20 & 0xffffffff
      if $soc_actual != 0xb2b2b1b1
        printf "Mismatch at 0x80001e20: got=0x%08x expected=0xb2b2b1b1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e24 & 0xffffffff
      if $soc_actual != 0xb4b4b3b3
        printf "Mismatch at 0x80001e24: got=0x%08x expected=0xb4b4b3b3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e28 & 0xffffffff
      if $soc_actual != 0xb6b6b5b5
        printf "Mismatch at 0x80001e28: got=0x%08x expected=0xb6b6b5b5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e2c & 0xffffffff
      if $soc_actual != 0xb8b8b7b7
        printf "Mismatch at 0x80001e2c: got=0x%08x expected=0xb8b8b7b7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e30 & 0xffffffff
      if $soc_actual != 0xbabab9b9
        printf "Mismatch at 0x80001e30: got=0x%08x expected=0xbabab9b9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e34 & 0xffffffff
      if $soc_actual != 0xbcbcbbbb
        printf "Mismatch at 0x80001e34: got=0x%08x expected=0xbcbcbbbb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e38 & 0xffffffff
      if $soc_actual != 0xbebebdbd
        printf "Mismatch at 0x80001e38: got=0x%08x expected=0xbebebdbd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e3c & 0xffffffff
      if $soc_actual != 0xc0c0bfbf
        printf "Mismatch at 0x80001e3c: got=0x%08x expected=0xc0c0bfbf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e40 & 0xffffffff
      if $soc_actual != 0xc2c2c1c1
        printf "Mismatch at 0x80001e40: got=0x%08x expected=0xc2c2c1c1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e44 & 0xffffffff
      if $soc_actual != 0xc4c4c3c3
        printf "Mismatch at 0x80001e44: got=0x%08x expected=0xc4c4c3c3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e48 & 0xffffffff
      if $soc_actual != 0xc6c6c5c5
        printf "Mismatch at 0x80001e48: got=0x%08x expected=0xc6c6c5c5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e4c & 0xffffffff
      if $soc_actual != 0xc8c8c7c7
        printf "Mismatch at 0x80001e4c: got=0x%08x expected=0xc8c8c7c7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e50 & 0xffffffff
      if $soc_actual != 0xcacac9c9
        printf "Mismatch at 0x80001e50: got=0x%08x expected=0xcacac9c9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e54 & 0xffffffff
      if $soc_actual != 0xcccccbcb
        printf "Mismatch at 0x80001e54: got=0x%08x expected=0xcccccbcb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e58 & 0xffffffff
      if $soc_actual != 0xcececdcd
        printf "Mismatch at 0x80001e58: got=0x%08x expected=0xcececdcd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e5c & 0xffffffff
      if $soc_actual != 0xd0d0cfcf
        printf "Mismatch at 0x80001e5c: got=0x%08x expected=0xd0d0cfcf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e60 & 0xffffffff
      if $soc_actual != 0xd2d2d1d1
        printf "Mismatch at 0x80001e60: got=0x%08x expected=0xd2d2d1d1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e64 & 0xffffffff
      if $soc_actual != 0xd4d4d3d3
        printf "Mismatch at 0x80001e64: got=0x%08x expected=0xd4d4d3d3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e68 & 0xffffffff
      if $soc_actual != 0xd6d6d5d5
        printf "Mismatch at 0x80001e68: got=0x%08x expected=0xd6d6d5d5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e6c & 0xffffffff
      if $soc_actual != 0xd8d7d7d6
        printf "Mismatch at 0x80001e6c: got=0x%08x expected=0xd8d7d7d6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e70 & 0xffffffff
      if $soc_actual != 0xdad9d9d8
        printf "Mismatch at 0x80001e70: got=0x%08x expected=0xdad9d9d8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e74 & 0xffffffff
      if $soc_actual != 0xdcdbdbda
        printf "Mismatch at 0x80001e74: got=0x%08x expected=0xdcdbdbda mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e78 & 0xffffffff
      if $soc_actual != 0xdedddddc
        printf "Mismatch at 0x80001e78: got=0x%08x expected=0xdedddddc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e7c & 0xffffffff
      if $soc_actual != 0xe0dfdfde
        printf "Mismatch at 0x80001e7c: got=0x%08x expected=0xe0dfdfde mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e80 & 0xffffffff
      if $soc_actual != 0xe2e1e1e0
        printf "Mismatch at 0x80001e80: got=0x%08x expected=0xe2e1e1e0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e84 & 0xffffffff
      if $soc_actual != 0xe4e3e3e2
        printf "Mismatch at 0x80001e84: got=0x%08x expected=0xe4e3e3e2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e88 & 0xffffffff
      if $soc_actual != 0xe6e5e5e4
        printf "Mismatch at 0x80001e88: got=0x%08x expected=0xe6e5e5e4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e8c & 0xffffffff
      if $soc_actual != 0xe8e7e7e6
        printf "Mismatch at 0x80001e8c: got=0x%08x expected=0xe8e7e7e6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e90 & 0xffffffff
      if $soc_actual != 0xeae9e9e8
        printf "Mismatch at 0x80001e90: got=0x%08x expected=0xeae9e9e8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e94 & 0xffffffff
      if $soc_actual != 0xecebebea
        printf "Mismatch at 0x80001e94: got=0x%08x expected=0xecebebea mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e98 & 0xffffffff
      if $soc_actual != 0xeeededec
        printf "Mismatch at 0x80001e98: got=0x%08x expected=0xeeededec mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e9c & 0xffffffff
      if $soc_actual != 0xf0efefee
        printf "Mismatch at 0x80001e9c: got=0x%08x expected=0xf0efefee mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea0 & 0xffffffff
      if $soc_actual != 0xf2f1f1f0
        printf "Mismatch at 0x80001ea0: got=0x%08x expected=0xf2f1f1f0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea4 & 0xffffffff
      if $soc_actual != 0xf4f3f3f2
        printf "Mismatch at 0x80001ea4: got=0x%08x expected=0xf4f3f3f2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea8 & 0xffffffff
      if $soc_actual != 0xf6f5f5f4
        printf "Mismatch at 0x80001ea8: got=0x%08x expected=0xf6f5f5f4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eac & 0xffffffff
      if $soc_actual != 0xf8f7f7f6
        printf "Mismatch at 0x80001eac: got=0x%08x expected=0xf8f7f7f6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb0 & 0xffffffff
      if $soc_actual != 0xfaf9f9f8
        printf "Mismatch at 0x80001eb0: got=0x%08x expected=0xfaf9f9f8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb4 & 0xffffffff
      if $soc_actual != 0xfcfbfbfa
        printf "Mismatch at 0x80001eb4: got=0x%08x expected=0xfcfbfbfa mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb8 & 0xffffffff
      if $soc_actual != 0xfefdfdfc
        printf "Mismatch at 0x80001eb8: got=0x%08x expected=0xfefdfdfc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ebc & 0xffffffff
      if $soc_actual != 0x00fffffe
        printf "Mismatch at 0x80001ebc: got=0x%08x expected=0x00fffffe mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec0 & 0xffffffff
      if $soc_actual != 0x02010100
        printf "Mismatch at 0x80001ec0: got=0x%08x expected=0x02010100 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec4 & 0xffffffff
      if $soc_actual != 0x04030302
        printf "Mismatch at 0x80001ec4: got=0x%08x expected=0x04030302 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec8 & 0xffffffff
      if $soc_actual != 0x06050504
        printf "Mismatch at 0x80001ec8: got=0x%08x expected=0x06050504 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ecc & 0xffffffff
      if $soc_actual != 0x08070706
        printf "Mismatch at 0x80001ecc: got=0x%08x expected=0x08070706 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed0 & 0xffffffff
      if $soc_actual != 0x0a090908
        printf "Mismatch at 0x80001ed0: got=0x%08x expected=0x0a090908 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed4 & 0xffffffff
      if $soc_actual != 0x0c0b0b0a
        printf "Mismatch at 0x80001ed4: got=0x%08x expected=0x0c0b0b0a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed8 & 0xffffffff
      if $soc_actual != 0x0e0d0d0c
        printf "Mismatch at 0x80001ed8: got=0x%08x expected=0x0e0d0d0c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001edc & 0xffffffff
      if $soc_actual != 0x100f0f0e
        printf "Mismatch at 0x80001edc: got=0x%08x expected=0x100f0f0e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee0 & 0xffffffff
      if $soc_actual != 0x12111110
        printf "Mismatch at 0x80001ee0: got=0x%08x expected=0x12111110 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee4 & 0xffffffff
      if $soc_actual != 0x14131312
        printf "Mismatch at 0x80001ee4: got=0x%08x expected=0x14131312 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee8 & 0xffffffff
      if $soc_actual != 0x16151514
        printf "Mismatch at 0x80001ee8: got=0x%08x expected=0x16151514 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eec & 0xffffffff
      if $soc_actual != 0x18171716
        printf "Mismatch at 0x80001eec: got=0x%08x expected=0x18171716 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef0 & 0xffffffff
      if $soc_actual != 0x1a191918
        printf "Mismatch at 0x80001ef0: got=0x%08x expected=0x1a191918 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef4 & 0xffffffff
      if $soc_actual != 0x1c1b1b1a
        printf "Mismatch at 0x80001ef4: got=0x%08x expected=0x1c1b1b1a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef8 & 0xffffffff
      if $soc_actual != 0x1e1d1d1c
        printf "Mismatch at 0x80001ef8: got=0x%08x expected=0x1e1d1d1c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001efc & 0xffffffff
      if $soc_actual != 0x201f1f1e
        printf "Mismatch at 0x80001efc: got=0x%08x expected=0x201f1f1e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f00 & 0xffffffff
      if $soc_actual != 0x22212120
        printf "Mismatch at 0x80001f00: got=0x%08x expected=0x22212120 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f04 & 0xffffffff
      if $soc_actual != 0x24232322
        printf "Mismatch at 0x80001f04: got=0x%08x expected=0x24232322 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f08 & 0xffffffff
      if $soc_actual != 0x26252524
        printf "Mismatch at 0x80001f08: got=0x%08x expected=0x26252524 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f0c & 0xffffffff
      if $soc_actual != 0x28272726
        printf "Mismatch at 0x80001f0c: got=0x%08x expected=0x28272726 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f10 & 0xffffffff
      if $soc_actual != 0x2a292928
        printf "Mismatch at 0x80001f10: got=0x%08x expected=0x2a292928 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f14 & 0xffffffff
      if $soc_actual != 0x2b2b2a2a
        printf "Mismatch at 0x80001f14: got=0x%08x expected=0x2b2b2a2a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f18 & 0xffffffff
      if $soc_actual != 0x2d2d2c2c
        printf "Mismatch at 0x80001f18: got=0x%08x expected=0x2d2d2c2c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f1c & 0xffffffff
      if $soc_actual != 0x2f2f2e2e
        printf "Mismatch at 0x80001f1c: got=0x%08x expected=0x2f2f2e2e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f20 & 0xffffffff
      if $soc_actual != 0x31313030
        printf "Mismatch at 0x80001f20: got=0x%08x expected=0x31313030 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f24 & 0xffffffff
      if $soc_actual != 0x33333232
        printf "Mismatch at 0x80001f24: got=0x%08x expected=0x33333232 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f28 & 0xffffffff
      if $soc_actual != 0x35353434
        printf "Mismatch at 0x80001f28: got=0x%08x expected=0x35353434 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f2c & 0xffffffff
      if $soc_actual != 0x37373636
        printf "Mismatch at 0x80001f2c: got=0x%08x expected=0x37373636 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f30 & 0xffffffff
      if $soc_actual != 0x39393838
        printf "Mismatch at 0x80001f30: got=0x%08x expected=0x39393838 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f34 & 0xffffffff
      if $soc_actual != 0x3b3b3a3a
        printf "Mismatch at 0x80001f34: got=0x%08x expected=0x3b3b3a3a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f38 & 0xffffffff
      if $soc_actual != 0x3d3d3c3c
        printf "Mismatch at 0x80001f38: got=0x%08x expected=0x3d3d3c3c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f3c & 0xffffffff
      if $soc_actual != 0x3f3f3e3e
        printf "Mismatch at 0x80001f3c: got=0x%08x expected=0x3f3f3e3e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f40 & 0xffffffff
      if $soc_actual != 0x41414040
        printf "Mismatch at 0x80001f40: got=0x%08x expected=0x41414040 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f44 & 0xffffffff
      if $soc_actual != 0x43434242
        printf "Mismatch at 0x80001f44: got=0x%08x expected=0x43434242 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f48 & 0xffffffff
      if $soc_actual != 0x45454444
        printf "Mismatch at 0x80001f48: got=0x%08x expected=0x45454444 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f4c & 0xffffffff
      if $soc_actual != 0x47474646
        printf "Mismatch at 0x80001f4c: got=0x%08x expected=0x47474646 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f50 & 0xffffffff
      if $soc_actual != 0x49494848
        printf "Mismatch at 0x80001f50: got=0x%08x expected=0x49494848 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f54 & 0xffffffff
      if $soc_actual != 0x4b4b4a4a
        printf "Mismatch at 0x80001f54: got=0x%08x expected=0x4b4b4a4a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f58 & 0xffffffff
      if $soc_actual != 0x4d4d4c4c
        printf "Mismatch at 0x80001f58: got=0x%08x expected=0x4d4d4c4c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f5c & 0xffffffff
      if $soc_actual != 0x4f4f4e4e
        printf "Mismatch at 0x80001f5c: got=0x%08x expected=0x4f4f4e4e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f60 & 0xffffffff
      if $soc_actual != 0x51515050
        printf "Mismatch at 0x80001f60: got=0x%08x expected=0x51515050 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f64 & 0xffffffff
      if $soc_actual != 0x53535252
        printf "Mismatch at 0x80001f64: got=0x%08x expected=0x53535252 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f68 & 0xffffffff
      if $soc_actual != 0x55555454
        printf "Mismatch at 0x80001f68: got=0x%08x expected=0x55555454 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f6c & 0xffffffff
      if $soc_actual != 0x57575656
        printf "Mismatch at 0x80001f6c: got=0x%08x expected=0x57575656 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f70 & 0xffffffff
      if $soc_actual != 0x59595858
        printf "Mismatch at 0x80001f70: got=0x%08x expected=0x59595858 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f74 & 0xffffffff
      if $soc_actual != 0x5b5b5a5a
        printf "Mismatch at 0x80001f74: got=0x%08x expected=0x5b5b5a5a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f78 & 0xffffffff
      if $soc_actual != 0x5d5d5c5c
        printf "Mismatch at 0x80001f78: got=0x%08x expected=0x5d5d5c5c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f7c & 0xffffffff
      if $soc_actual != 0x5f5f5e5e
        printf "Mismatch at 0x80001f7c: got=0x%08x expected=0x5f5f5e5e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f80 & 0xffffffff
      if $soc_actual != 0x61616060
        printf "Mismatch at 0x80001f80: got=0x%08x expected=0x61616060 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f84 & 0xffffffff
      if $soc_actual != 0x63636262
        printf "Mismatch at 0x80001f84: got=0x%08x expected=0x63636262 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f88 & 0xffffffff
      if $soc_actual != 0x65656464
        printf "Mismatch at 0x80001f88: got=0x%08x expected=0x65656464 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f8c & 0xffffffff
      if $soc_actual != 0x67676666
        printf "Mismatch at 0x80001f8c: got=0x%08x expected=0x67676666 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f90 & 0xffffffff
      if $soc_actual != 0x69696868
        printf "Mismatch at 0x80001f90: got=0x%08x expected=0x69696868 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f94 & 0xffffffff
      if $soc_actual != 0x6b6b6a6a
        printf "Mismatch at 0x80001f94: got=0x%08x expected=0x6b6b6a6a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f98 & 0xffffffff
      if $soc_actual != 0x6d6d6c6c
        printf "Mismatch at 0x80001f98: got=0x%08x expected=0x6d6d6c6c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f9c & 0xffffffff
      if $soc_actual != 0x6f6f6e6e
        printf "Mismatch at 0x80001f9c: got=0x%08x expected=0x6f6f6e6e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa0 & 0xffffffff
      if $soc_actual != 0x71717070
        printf "Mismatch at 0x80001fa0: got=0x%08x expected=0x71717070 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa4 & 0xffffffff
      if $soc_actual != 0x73737272
        printf "Mismatch at 0x80001fa4: got=0x%08x expected=0x73737272 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa8 & 0xffffffff
      if $soc_actual != 0x75757474
        printf "Mismatch at 0x80001fa8: got=0x%08x expected=0x75757474 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fac & 0xffffffff
      if $soc_actual != 0x77777676
        printf "Mismatch at 0x80001fac: got=0x%08x expected=0x77777676 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb0 & 0xffffffff
      if $soc_actual != 0x79797878
        printf "Mismatch at 0x80001fb0: got=0x%08x expected=0x79797878 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb4 & 0xffffffff
      if $soc_actual != 0x7b7b7a7a
        printf "Mismatch at 0x80001fb4: got=0x%08x expected=0x7b7b7a7a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb8 & 0xffffffff
      if $soc_actual != 0x7d7d7c7c
        printf "Mismatch at 0x80001fb8: got=0x%08x expected=0x7d7d7c7c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fbc & 0xffffffff
      if $soc_actual != 0x7f7f7e7e
        printf "Mismatch at 0x80001fbc: got=0x%08x expected=0x7f7f7e7e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS raw_k_split_b4_cpu checked_words=160 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
