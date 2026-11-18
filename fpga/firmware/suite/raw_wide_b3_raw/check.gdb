# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0x4d1986a4
    printf "FPGA_CHECK_FAIL: wrong image tag for raw_wide_b3_raw\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001de0 & 0xffffffff
      if $soc_actual != 0x99918a82
        printf "Mismatch at 0x80001de0: got=0x%08x expected=0x99918a82 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de4 & 0xffffffff
      if $soc_actual != 0xb7afa8a0
        printf "Mismatch at 0x80001de4: got=0x%08x expected=0xb7afa8a0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de8 & 0xffffffff
      if $soc_actual != 0xd5cec6bf
        printf "Mismatch at 0x80001de8: got=0x%08x expected=0xd5cec6bf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dec & 0xffffffff
      if $soc_actual != 0xf4ece5dd
        printf "Mismatch at 0x80001dec: got=0x%08x expected=0xf4ece5dd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df0 & 0xffffffff
      if $soc_actual != 0x120b03fb
        printf "Mismatch at 0x80001df0: got=0x%08x expected=0x120b03fb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df4 & 0xffffffff
      if $soc_actual != 0x3129211a
        printf "Mismatch at 0x80001df4: got=0x%08x expected=0x3129211a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df8 & 0xffffffff
      if $soc_actual != 0x4f474038
        printf "Mismatch at 0x80001df8: got=0x%08x expected=0x4f474038 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dfc & 0xffffffff
      if $soc_actual != 0x6d665e57
        printf "Mismatch at 0x80001dfc: got=0x%08x expected=0x6d665e57 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e00 & 0xffffffff
      if $soc_actual != 0xa19a928a
        printf "Mismatch at 0x80001e00: got=0x%08x expected=0xa19a928a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e04 & 0xffffffff
      if $soc_actual != 0xbfb8b0a9
        printf "Mismatch at 0x80001e04: got=0x%08x expected=0xbfb8b0a9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e08 & 0xffffffff
      if $soc_actual != 0xded6cfc7
        printf "Mismatch at 0x80001e08: got=0x%08x expected=0xded6cfc7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e0c & 0xffffffff
      if $soc_actual != 0xfcf5ede5
        printf "Mismatch at 0x80001e0c: got=0x%08x expected=0xfcf5ede5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e10 & 0xffffffff
      if $soc_actual != 0x1b130b04
        printf "Mismatch at 0x80001e10: got=0x%08x expected=0x1b130b04 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e14 & 0xffffffff
      if $soc_actual != 0x39312a22
        printf "Mismatch at 0x80001e14: got=0x%08x expected=0x39312a22 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e18 & 0xffffffff
      if $soc_actual != 0x57504841
        printf "Mismatch at 0x80001e18: got=0x%08x expected=0x57504841 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e1c & 0xffffffff
      if $soc_actual != 0x766e665f
        printf "Mismatch at 0x80001e1c: got=0x%08x expected=0x766e665f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e20 & 0xffffffff
      if $soc_actual != 0xa9a29a93
        printf "Mismatch at 0x80001e20: got=0x%08x expected=0xa9a29a93 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e24 & 0xffffffff
      if $soc_actual != 0xc8c0b9b1
        printf "Mismatch at 0x80001e24: got=0x%08x expected=0xc8c0b9b1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e28 & 0xffffffff
      if $soc_actual != 0xe6dfd7cf
        printf "Mismatch at 0x80001e28: got=0x%08x expected=0xe6dfd7cf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e2c & 0xffffffff
      if $soc_actual != 0x05fdf5ee
        printf "Mismatch at 0x80001e2c: got=0x%08x expected=0x05fdf5ee mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e30 & 0xffffffff
      if $soc_actual != 0x231b140c
        printf "Mismatch at 0x80001e30: got=0x%08x expected=0x231b140c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e34 & 0xffffffff
      if $soc_actual != 0x413a322b
        printf "Mismatch at 0x80001e34: got=0x%08x expected=0x413a322b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e38 & 0xffffffff
      if $soc_actual != 0x60585149
        printf "Mismatch at 0x80001e38: got=0x%08x expected=0x60585149 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e3c & 0xffffffff
      if $soc_actual != 0x7e766f67
        printf "Mismatch at 0x80001e3c: got=0x%08x expected=0x7e766f67 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e40 & 0xffffffff
      if $soc_actual != 0x83828281
        printf "Mismatch at 0x80001e40: got=0x%08x expected=0x83828281 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e44 & 0xffffffff
      if $soc_actual != 0x86858484
        printf "Mismatch at 0x80001e44: got=0x%08x expected=0x86858484 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e48 & 0xffffffff
      if $soc_actual != 0x88888786
        printf "Mismatch at 0x80001e48: got=0x%08x expected=0x88888786 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e4c & 0xffffffff
      if $soc_actual != 0x8b8a8a89
        printf "Mismatch at 0x80001e4c: got=0x%08x expected=0x8b8a8a89 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e50 & 0xffffffff
      if $soc_actual != 0x8e8d8c8c
        printf "Mismatch at 0x80001e50: got=0x%08x expected=0x8e8d8c8c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e54 & 0xffffffff
      if $soc_actual != 0x90908f8e
        printf "Mismatch at 0x80001e54: got=0x%08x expected=0x90908f8e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e58 & 0xffffffff
      if $soc_actual != 0x93929291
        printf "Mismatch at 0x80001e58: got=0x%08x expected=0x93929291 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e5c & 0xffffffff
      if $soc_actual != 0x96959494
        printf "Mismatch at 0x80001e5c: got=0x%08x expected=0x96959494 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e60 & 0xffffffff
      if $soc_actual != 0x98989796
        printf "Mismatch at 0x80001e60: got=0x%08x expected=0x98989796 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e64 & 0xffffffff
      if $soc_actual != 0x9b9a9a99
        printf "Mismatch at 0x80001e64: got=0x%08x expected=0x9b9a9a99 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e68 & 0xffffffff
      if $soc_actual != 0x9e9d9c9c
        printf "Mismatch at 0x80001e68: got=0x%08x expected=0x9e9d9c9c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e6c & 0xffffffff
      if $soc_actual != 0xa0a09f9e
        printf "Mismatch at 0x80001e6c: got=0x%08x expected=0xa0a09f9e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e70 & 0xffffffff
      if $soc_actual != 0xa3a2a1a1
        printf "Mismatch at 0x80001e70: got=0x%08x expected=0xa3a2a1a1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e74 & 0xffffffff
      if $soc_actual != 0xa5a5a4a3
        printf "Mismatch at 0x80001e74: got=0x%08x expected=0xa5a5a4a3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e78 & 0xffffffff
      if $soc_actual != 0xa8a7a7a6
        printf "Mismatch at 0x80001e78: got=0x%08x expected=0xa8a7a7a6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e7c & 0xffffffff
      if $soc_actual != 0xabaaa9a9
        printf "Mismatch at 0x80001e7c: got=0x%08x expected=0xabaaa9a9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e80 & 0xffffffff
      if $soc_actual != 0xadadacab
        printf "Mismatch at 0x80001e80: got=0x%08x expected=0xadadacab mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e84 & 0xffffffff
      if $soc_actual != 0xb0afafae
        printf "Mismatch at 0x80001e84: got=0x%08x expected=0xb0afafae mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e88 & 0xffffffff
      if $soc_actual != 0xb3b2b1b1
        printf "Mismatch at 0x80001e88: got=0x%08x expected=0xb3b2b1b1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e8c & 0xffffffff
      if $soc_actual != 0xb5b5b4b3
        printf "Mismatch at 0x80001e8c: got=0x%08x expected=0xb5b5b4b3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e90 & 0xffffffff
      if $soc_actual != 0xb8b7b7b6
        printf "Mismatch at 0x80001e90: got=0x%08x expected=0xb8b7b7b6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e94 & 0xffffffff
      if $soc_actual != 0xbbbab9b9
        printf "Mismatch at 0x80001e94: got=0x%08x expected=0xbbbab9b9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e98 & 0xffffffff
      if $soc_actual != 0xbdbdbcbb
        printf "Mismatch at 0x80001e98: got=0x%08x expected=0xbdbdbcbb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e9c & 0xffffffff
      if $soc_actual != 0xc0bfbfbe
        printf "Mismatch at 0x80001e9c: got=0x%08x expected=0xc0bfbfbe mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea0 & 0xffffffff
      if $soc_actual != 0xc3c2c1c1
        printf "Mismatch at 0x80001ea0: got=0x%08x expected=0xc3c2c1c1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea4 & 0xffffffff
      if $soc_actual != 0xc5c5c4c3
        printf "Mismatch at 0x80001ea4: got=0x%08x expected=0xc5c5c4c3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea8 & 0xffffffff
      if $soc_actual != 0xc8c7c7c6
        printf "Mismatch at 0x80001ea8: got=0x%08x expected=0xc8c7c7c6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eac & 0xffffffff
      if $soc_actual != 0xcbcac9c9
        printf "Mismatch at 0x80001eac: got=0x%08x expected=0xcbcac9c9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb0 & 0xffffffff
      if $soc_actual != 0xcdcdcccb
        printf "Mismatch at 0x80001eb0: got=0x%08x expected=0xcdcdcccb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb4 & 0xffffffff
      if $soc_actual != 0xd0cfcfce
        printf "Mismatch at 0x80001eb4: got=0x%08x expected=0xd0cfcfce mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb8 & 0xffffffff
      if $soc_actual != 0xd3d2d1d1
        printf "Mismatch at 0x80001eb8: got=0x%08x expected=0xd3d2d1d1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ebc & 0xffffffff
      if $soc_actual != 0xd5d5d4d3
        printf "Mismatch at 0x80001ebc: got=0x%08x expected=0xd5d5d4d3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec0 & 0xffffffff
      if $soc_actual != 0xd8d7d7d6
        printf "Mismatch at 0x80001ec0: got=0x%08x expected=0xd8d7d7d6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec4 & 0xffffffff
      if $soc_actual != 0xdbdad9d9
        printf "Mismatch at 0x80001ec4: got=0x%08x expected=0xdbdad9d9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec8 & 0xffffffff
      if $soc_actual != 0xdddddcdb
        printf "Mismatch at 0x80001ec8: got=0x%08x expected=0xdddddcdb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ecc & 0xffffffff
      if $soc_actual != 0xe0dfdfde
        printf "Mismatch at 0x80001ecc: got=0x%08x expected=0xe0dfdfde mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed0 & 0xffffffff
      if $soc_actual != 0xe2e2e1e0
        printf "Mismatch at 0x80001ed0: got=0x%08x expected=0xe2e2e1e0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed4 & 0xffffffff
      if $soc_actual != 0xe5e4e4e3
        printf "Mismatch at 0x80001ed4: got=0x%08x expected=0xe5e4e4e3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed8 & 0xffffffff
      if $soc_actual != 0xe8e7e6e6
        printf "Mismatch at 0x80001ed8: got=0x%08x expected=0xe8e7e6e6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001edc & 0xffffffff
      if $soc_actual != 0xeaeae9e8
        printf "Mismatch at 0x80001edc: got=0x%08x expected=0xeaeae9e8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee0 & 0xffffffff
      if $soc_actual != 0xedececeb
        printf "Mismatch at 0x80001ee0: got=0x%08x expected=0xedececeb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee4 & 0xffffffff
      if $soc_actual != 0xf0efeeee
        printf "Mismatch at 0x80001ee4: got=0x%08x expected=0xf0efeeee mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee8 & 0xffffffff
      if $soc_actual != 0xf2f2f1f0
        printf "Mismatch at 0x80001ee8: got=0x%08x expected=0xf2f2f1f0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eec & 0xffffffff
      if $soc_actual != 0xf5f4f4f3
        printf "Mismatch at 0x80001eec: got=0x%08x expected=0xf5f4f4f3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef0 & 0xffffffff
      if $soc_actual != 0xf8f7f6f6
        printf "Mismatch at 0x80001ef0: got=0x%08x expected=0xf8f7f6f6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef4 & 0xffffffff
      if $soc_actual != 0xfafaf9f8
        printf "Mismatch at 0x80001ef4: got=0x%08x expected=0xfafaf9f8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef8 & 0xffffffff
      if $soc_actual != 0xfdfcfcfb
        printf "Mismatch at 0x80001ef8: got=0x%08x expected=0xfdfcfcfb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001efc & 0xffffffff
      if $soc_actual != 0x00fffefe
        printf "Mismatch at 0x80001efc: got=0x%08x expected=0x00fffefe mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f00 & 0xffffffff
      if $soc_actual != 0x02020100
        printf "Mismatch at 0x80001f00: got=0x%08x expected=0x02020100 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f04 & 0xffffffff
      if $soc_actual != 0x05040403
        printf "Mismatch at 0x80001f04: got=0x%08x expected=0x05040403 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f08 & 0xffffffff
      if $soc_actual != 0x08070606
        printf "Mismatch at 0x80001f08: got=0x%08x expected=0x08070606 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f0c & 0xffffffff
      if $soc_actual != 0x0a0a0908
        printf "Mismatch at 0x80001f0c: got=0x%08x expected=0x0a0a0908 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f10 & 0xffffffff
      if $soc_actual != 0x0d0c0c0b
        printf "Mismatch at 0x80001f10: got=0x%08x expected=0x0d0c0c0b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f14 & 0xffffffff
      if $soc_actual != 0x100f0e0e
        printf "Mismatch at 0x80001f14: got=0x%08x expected=0x100f0e0e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f18 & 0xffffffff
      if $soc_actual != 0x12121110
        printf "Mismatch at 0x80001f18: got=0x%08x expected=0x12121110 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f1c & 0xffffffff
      if $soc_actual != 0x15141413
        printf "Mismatch at 0x80001f1c: got=0x%08x expected=0x15141413 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f20 & 0xffffffff
      if $soc_actual != 0x18171616
        printf "Mismatch at 0x80001f20: got=0x%08x expected=0x18171616 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f24 & 0xffffffff
      if $soc_actual != 0x1a1a1918
        printf "Mismatch at 0x80001f24: got=0x%08x expected=0x1a1a1918 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f28 & 0xffffffff
      if $soc_actual != 0x1d1c1c1b
        printf "Mismatch at 0x80001f28: got=0x%08x expected=0x1d1c1c1b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f2c & 0xffffffff
      if $soc_actual != 0x201f1e1e
        printf "Mismatch at 0x80001f2c: got=0x%08x expected=0x201f1e1e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f30 & 0xffffffff
      if $soc_actual != 0x22212120
        printf "Mismatch at 0x80001f30: got=0x%08x expected=0x22212120 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f34 & 0xffffffff
      if $soc_actual != 0x25242323
        printf "Mismatch at 0x80001f34: got=0x%08x expected=0x25242323 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f38 & 0xffffffff
      if $soc_actual != 0x27272625
        printf "Mismatch at 0x80001f38: got=0x%08x expected=0x27272625 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f3c & 0xffffffff
      if $soc_actual != 0x2a292928
        printf "Mismatch at 0x80001f3c: got=0x%08x expected=0x2a292928 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f40 & 0xffffffff
      if $soc_actual != 0x2d2c2b2b
        printf "Mismatch at 0x80001f40: got=0x%08x expected=0x2d2c2b2b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f44 & 0xffffffff
      if $soc_actual != 0x2f2f2e2d
        printf "Mismatch at 0x80001f44: got=0x%08x expected=0x2f2f2e2d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f48 & 0xffffffff
      if $soc_actual != 0x32313130
        printf "Mismatch at 0x80001f48: got=0x%08x expected=0x32313130 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f4c & 0xffffffff
      if $soc_actual != 0x35343333
        printf "Mismatch at 0x80001f4c: got=0x%08x expected=0x35343333 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f50 & 0xffffffff
      if $soc_actual != 0x37373635
        printf "Mismatch at 0x80001f50: got=0x%08x expected=0x37373635 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f54 & 0xffffffff
      if $soc_actual != 0x3a393938
        printf "Mismatch at 0x80001f54: got=0x%08x expected=0x3a393938 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f58 & 0xffffffff
      if $soc_actual != 0x3d3c3b3b
        printf "Mismatch at 0x80001f58: got=0x%08x expected=0x3d3c3b3b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f5c & 0xffffffff
      if $soc_actual != 0x3f3f3e3d
        printf "Mismatch at 0x80001f5c: got=0x%08x expected=0x3f3f3e3d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f60 & 0xffffffff
      if $soc_actual != 0x42414140
        printf "Mismatch at 0x80001f60: got=0x%08x expected=0x42414140 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f64 & 0xffffffff
      if $soc_actual != 0x45444343
        printf "Mismatch at 0x80001f64: got=0x%08x expected=0x45444343 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f68 & 0xffffffff
      if $soc_actual != 0x47474645
        printf "Mismatch at 0x80001f68: got=0x%08x expected=0x47474645 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f6c & 0xffffffff
      if $soc_actual != 0x4a494948
        printf "Mismatch at 0x80001f6c: got=0x%08x expected=0x4a494948 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f70 & 0xffffffff
      if $soc_actual != 0x4d4c4b4b
        printf "Mismatch at 0x80001f70: got=0x%08x expected=0x4d4c4b4b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f74 & 0xffffffff
      if $soc_actual != 0x4f4f4e4d
        printf "Mismatch at 0x80001f74: got=0x%08x expected=0x4f4f4e4d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f78 & 0xffffffff
      if $soc_actual != 0x52515150
        printf "Mismatch at 0x80001f78: got=0x%08x expected=0x52515150 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f7c & 0xffffffff
      if $soc_actual != 0x55545353
        printf "Mismatch at 0x80001f7c: got=0x%08x expected=0x55545353 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f80 & 0xffffffff
      if $soc_actual != 0x57575655
        printf "Mismatch at 0x80001f80: got=0x%08x expected=0x57575655 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f84 & 0xffffffff
      if $soc_actual != 0x5a595958
        printf "Mismatch at 0x80001f84: got=0x%08x expected=0x5a595958 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f88 & 0xffffffff
      if $soc_actual != 0x5d5c5b5b
        printf "Mismatch at 0x80001f88: got=0x%08x expected=0x5d5c5b5b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f8c & 0xffffffff
      if $soc_actual != 0x5f5f5e5d
        printf "Mismatch at 0x80001f8c: got=0x%08x expected=0x5f5f5e5d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f90 & 0xffffffff
      if $soc_actual != 0x62616060
        printf "Mismatch at 0x80001f90: got=0x%08x expected=0x62616060 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f94 & 0xffffffff
      if $soc_actual != 0x64646362
        printf "Mismatch at 0x80001f94: got=0x%08x expected=0x64646362 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f98 & 0xffffffff
      if $soc_actual != 0x67666665
        printf "Mismatch at 0x80001f98: got=0x%08x expected=0x67666665 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f9c & 0xffffffff
      if $soc_actual != 0x6a696868
        printf "Mismatch at 0x80001f9c: got=0x%08x expected=0x6a696868 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa0 & 0xffffffff
      if $soc_actual != 0x6c6c6b6a
        printf "Mismatch at 0x80001fa0: got=0x%08x expected=0x6c6c6b6a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa4 & 0xffffffff
      if $soc_actual != 0x6f6e6e6d
        printf "Mismatch at 0x80001fa4: got=0x%08x expected=0x6f6e6e6d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa8 & 0xffffffff
      if $soc_actual != 0x72717070
        printf "Mismatch at 0x80001fa8: got=0x%08x expected=0x72717070 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fac & 0xffffffff
      if $soc_actual != 0x74747372
        printf "Mismatch at 0x80001fac: got=0x%08x expected=0x74747372 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb0 & 0xffffffff
      if $soc_actual != 0x77767675
        printf "Mismatch at 0x80001fb0: got=0x%08x expected=0x77767675 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb4 & 0xffffffff
      if $soc_actual != 0x7a797878
        printf "Mismatch at 0x80001fb4: got=0x%08x expected=0x7a797878 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb8 & 0xffffffff
      if $soc_actual != 0x7c7c7b7a
        printf "Mismatch at 0x80001fb8: got=0x%08x expected=0x7c7c7b7a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fbc & 0xffffffff
      if $soc_actual != 0x7f7e7e7d
        printf "Mismatch at 0x80001fbc: got=0x%08x expected=0x7f7e7e7d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS raw_wide_b3_raw checked_words=120 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
