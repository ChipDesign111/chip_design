# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0x78daf747
    printf "FPGA_CHECK_FAIL: wrong image tag for raw_full_b4_cpu\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001e40 & 0xffffffff
      if $soc_actual != 0x46dcdcd5
        printf "Mismatch at 0x80001e40: got=0x%08x expected=0x46dcdcd5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e44 & 0xffffffff
      if $soc_actual != 0xec5939ed
        printf "Mismatch at 0x80001e44: got=0x%08x expected=0xec5939ed mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e48 & 0xffffffff
      if $soc_actual != 0x03161bc2
        printf "Mismatch at 0x80001e48: got=0x%08x expected=0x03161bc2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e4c & 0xffffffff
      if $soc_actual != 0x13f402f6
        printf "Mismatch at 0x80001e4c: got=0x%08x expected=0x13f402f6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e50 & 0xffffffff
      if $soc_actual != 0x8cfb042f
        printf "Mismatch at 0x80001e50: got=0x%08x expected=0x8cfb042f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e54 & 0xffffffff
      if $soc_actual != 0xd79d1af4
        printf "Mismatch at 0x80001e54: got=0x%08x expected=0xd79d1af4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e58 & 0xffffffff
      if $soc_actual != 0x73fe43ff
        printf "Mismatch at 0x80001e58: got=0x%08x expected=0x73fe43ff mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e5c & 0xffffffff
      if $soc_actual != 0xd0f1fdc3
        printf "Mismatch at 0x80001e5c: got=0x%08x expected=0xd0f1fdc3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e60 & 0xffffffff
      if $soc_actual != 0x0fede8e9
        printf "Mismatch at 0x80001e60: got=0x%08x expected=0x0fede8e9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e64 & 0xffffffff
      if $soc_actual != 0xf1121500
        printf "Mismatch at 0x80001e64: got=0x%08x expected=0xf1121500 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e68 & 0xffffffff
      if $soc_actual != 0x110d08e0
        printf "Mismatch at 0x80001e68: got=0x%08x expected=0x110d08e0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e6c & 0xffffffff
      if $soc_actual != 0x0c0a00f3
        printf "Mismatch at 0x80001e6c: got=0x%08x expected=0x0c0a00f3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e70 & 0xffffffff
      if $soc_actual != 0xdbf60515
        printf "Mismatch at 0x80001e70: got=0x%08x expected=0xdbf60515 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e74 & 0xffffffff
      if $soc_actual != 0xfce104fb
        printf "Mismatch at 0x80001e74: got=0x%08x expected=0xfce104fb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e78 & 0xffffffff
      if $soc_actual != 0x28f71e08
        printf "Mismatch at 0x80001e78: got=0x%08x expected=0x28f71e08 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e7c & 0xffffffff
      if $soc_actual != 0xf2f1ffe7
        printf "Mismatch at 0x80001e7c: got=0x%08x expected=0xf2f1ffe7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e80 & 0xffffffff
      if $soc_actual != 0xd9fff4fd
        printf "Mismatch at 0x80001e80: got=0x%08x expected=0xd9fff4fd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e84 & 0xffffffff
      if $soc_actual != 0xf5ccf212
        printf "Mismatch at 0x80001e84: got=0x%08x expected=0xf5ccf212 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e88 & 0xffffffff
      if $soc_actual != 0x1f04f6fe
        printf "Mismatch at 0x80001e88: got=0x%08x expected=0x1f04f6fe mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e8c & 0xffffffff
      if $soc_actual != 0x0620fff1
        printf "Mismatch at 0x80001e8c: got=0x%08x expected=0x0620fff1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e90 & 0xffffffff
      if $soc_actual != 0x29f206fb
        printf "Mismatch at 0x80001e90: got=0x%08x expected=0x29f206fb mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e94 & 0xffffffff
      if $soc_actual != 0x2124ef02
        printf "Mismatch at 0x80001e94: got=0x%08x expected=0x2124ef02 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e98 & 0xffffffff
      if $soc_actual != 0xdef0f910
        printf "Mismatch at 0x80001e98: got=0x%08x expected=0xdef0f910 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e9c & 0xffffffff
      if $soc_actual != 0x14f0020b
        printf "Mismatch at 0x80001e9c: got=0x%08x expected=0x14f0020b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea0 & 0xffffffff
      if $soc_actual != 0xa210ff12
        printf "Mismatch at 0x80001ea0: got=0x%08x expected=0xa210ff12 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea4 & 0xffffffff
      if $soc_actual != 0xfa84ce25
        printf "Mismatch at 0x80001ea4: got=0x%08x expected=0xfa84ce25 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea8 & 0xffffffff
      if $soc_actual != 0x2dfbe31d
        printf "Mismatch at 0x80001ea8: got=0x%08x expected=0x2dfbe31d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eac & 0xffffffff
      if $soc_actual != 0x0036fdee
        printf "Mismatch at 0x80001eac: got=0x%08x expected=0x0036fdee mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb0 & 0xffffffff
      if $soc_actual != 0x78ed08e1
        printf "Mismatch at 0x80001eb0: got=0x%08x expected=0x78ed08e1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb4 & 0xffffffff
      if $soc_actual != 0x4668da09
        printf "Mismatch at 0x80001eb4: got=0x%08x expected=0x4668da09 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb8 & 0xffffffff
      if $soc_actual != 0x93e9d419
        printf "Mismatch at 0x80001eb8: got=0x%08x expected=0x93e9d419 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ebc & 0xffffffff
      if $soc_actual != 0x36f0052f
        printf "Mismatch at 0x80001ebc: got=0x%08x expected=0x36f0052f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec0 & 0xffffffff
      if $soc_actual != 0x84838281
        printf "Mismatch at 0x80001ec0: got=0x%08x expected=0x84838281 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec4 & 0xffffffff
      if $soc_actual != 0x88878685
        printf "Mismatch at 0x80001ec4: got=0x%08x expected=0x88878685 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec8 & 0xffffffff
      if $soc_actual != 0x8c8b8a89
        printf "Mismatch at 0x80001ec8: got=0x%08x expected=0x8c8b8a89 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ecc & 0xffffffff
      if $soc_actual != 0x908f8e8d
        printf "Mismatch at 0x80001ecc: got=0x%08x expected=0x908f8e8d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed0 & 0xffffffff
      if $soc_actual != 0x94939291
        printf "Mismatch at 0x80001ed0: got=0x%08x expected=0x94939291 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed4 & 0xffffffff
      if $soc_actual != 0x98979695
        printf "Mismatch at 0x80001ed4: got=0x%08x expected=0x98979695 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed8 & 0xffffffff
      if $soc_actual != 0x9c9b9a99
        printf "Mismatch at 0x80001ed8: got=0x%08x expected=0x9c9b9a99 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001edc & 0xffffffff
      if $soc_actual != 0xa09f9e9d
        printf "Mismatch at 0x80001edc: got=0x%08x expected=0xa09f9e9d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee0 & 0xffffffff
      if $soc_actual != 0xa4a3a2a1
        printf "Mismatch at 0x80001ee0: got=0x%08x expected=0xa4a3a2a1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee4 & 0xffffffff
      if $soc_actual != 0xa8a7a6a5
        printf "Mismatch at 0x80001ee4: got=0x%08x expected=0xa8a7a6a5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee8 & 0xffffffff
      if $soc_actual != 0xacabaaa9
        printf "Mismatch at 0x80001ee8: got=0x%08x expected=0xacabaaa9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eec & 0xffffffff
      if $soc_actual != 0xb0afaead
        printf "Mismatch at 0x80001eec: got=0x%08x expected=0xb0afaead mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef0 & 0xffffffff
      if $soc_actual != 0xb4b3b2b1
        printf "Mismatch at 0x80001ef0: got=0x%08x expected=0xb4b3b2b1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef4 & 0xffffffff
      if $soc_actual != 0xb8b7b6b5
        printf "Mismatch at 0x80001ef4: got=0x%08x expected=0xb8b7b6b5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef8 & 0xffffffff
      if $soc_actual != 0xbcbbbab9
        printf "Mismatch at 0x80001ef8: got=0x%08x expected=0xbcbbbab9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001efc & 0xffffffff
      if $soc_actual != 0xc0bfbebd
        printf "Mismatch at 0x80001efc: got=0x%08x expected=0xc0bfbebd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f00 & 0xffffffff
      if $soc_actual != 0xc4c3c2c1
        printf "Mismatch at 0x80001f00: got=0x%08x expected=0xc4c3c2c1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f04 & 0xffffffff
      if $soc_actual != 0xc8c7c6c5
        printf "Mismatch at 0x80001f04: got=0x%08x expected=0xc8c7c6c5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f08 & 0xffffffff
      if $soc_actual != 0xcccbcac9
        printf "Mismatch at 0x80001f08: got=0x%08x expected=0xcccbcac9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f0c & 0xffffffff
      if $soc_actual != 0xd0cfcecd
        printf "Mismatch at 0x80001f0c: got=0x%08x expected=0xd0cfcecd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f10 & 0xffffffff
      if $soc_actual != 0xd4d3d2d1
        printf "Mismatch at 0x80001f10: got=0x%08x expected=0xd4d3d2d1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f14 & 0xffffffff
      if $soc_actual != 0xd8d7d6d5
        printf "Mismatch at 0x80001f14: got=0x%08x expected=0xd8d7d6d5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f18 & 0xffffffff
      if $soc_actual != 0xdcdbdad9
        printf "Mismatch at 0x80001f18: got=0x%08x expected=0xdcdbdad9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f1c & 0xffffffff
      if $soc_actual != 0xe0dfdedd
        printf "Mismatch at 0x80001f1c: got=0x%08x expected=0xe0dfdedd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f20 & 0xffffffff
      if $soc_actual != 0xe4e3e2e1
        printf "Mismatch at 0x80001f20: got=0x%08x expected=0xe4e3e2e1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f24 & 0xffffffff
      if $soc_actual != 0xe8e7e6e5
        printf "Mismatch at 0x80001f24: got=0x%08x expected=0xe8e7e6e5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f28 & 0xffffffff
      if $soc_actual != 0xecebeae9
        printf "Mismatch at 0x80001f28: got=0x%08x expected=0xecebeae9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f2c & 0xffffffff
      if $soc_actual != 0xf0efeeed
        printf "Mismatch at 0x80001f2c: got=0x%08x expected=0xf0efeeed mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f30 & 0xffffffff
      if $soc_actual != 0xf4f3f2f1
        printf "Mismatch at 0x80001f30: got=0x%08x expected=0xf4f3f2f1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f34 & 0xffffffff
      if $soc_actual != 0xf8f7f6f5
        printf "Mismatch at 0x80001f34: got=0x%08x expected=0xf8f7f6f5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f38 & 0xffffffff
      if $soc_actual != 0xfcfbfaf9
        printf "Mismatch at 0x80001f38: got=0x%08x expected=0xfcfbfaf9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f3c & 0xffffffff
      if $soc_actual != 0x00fffefd
        printf "Mismatch at 0x80001f3c: got=0x%08x expected=0x00fffefd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f40 & 0xffffffff
      if $soc_actual != 0x03020100
        printf "Mismatch at 0x80001f40: got=0x%08x expected=0x03020100 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f44 & 0xffffffff
      if $soc_actual != 0x07060504
        printf "Mismatch at 0x80001f44: got=0x%08x expected=0x07060504 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f48 & 0xffffffff
      if $soc_actual != 0x0b0a0908
        printf "Mismatch at 0x80001f48: got=0x%08x expected=0x0b0a0908 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f4c & 0xffffffff
      if $soc_actual != 0x0f0e0d0c
        printf "Mismatch at 0x80001f4c: got=0x%08x expected=0x0f0e0d0c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f50 & 0xffffffff
      if $soc_actual != 0x13121110
        printf "Mismatch at 0x80001f50: got=0x%08x expected=0x13121110 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f54 & 0xffffffff
      if $soc_actual != 0x17161514
        printf "Mismatch at 0x80001f54: got=0x%08x expected=0x17161514 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f58 & 0xffffffff
      if $soc_actual != 0x1b1a1918
        printf "Mismatch at 0x80001f58: got=0x%08x expected=0x1b1a1918 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f5c & 0xffffffff
      if $soc_actual != 0x1f1e1d1c
        printf "Mismatch at 0x80001f5c: got=0x%08x expected=0x1f1e1d1c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f60 & 0xffffffff
      if $soc_actual != 0x23222120
        printf "Mismatch at 0x80001f60: got=0x%08x expected=0x23222120 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f64 & 0xffffffff
      if $soc_actual != 0x27262524
        printf "Mismatch at 0x80001f64: got=0x%08x expected=0x27262524 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f68 & 0xffffffff
      if $soc_actual != 0x2b2a2928
        printf "Mismatch at 0x80001f68: got=0x%08x expected=0x2b2a2928 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f6c & 0xffffffff
      if $soc_actual != 0x2f2e2d2c
        printf "Mismatch at 0x80001f6c: got=0x%08x expected=0x2f2e2d2c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f70 & 0xffffffff
      if $soc_actual != 0x33323130
        printf "Mismatch at 0x80001f70: got=0x%08x expected=0x33323130 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f74 & 0xffffffff
      if $soc_actual != 0x37363534
        printf "Mismatch at 0x80001f74: got=0x%08x expected=0x37363534 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f78 & 0xffffffff
      if $soc_actual != 0x3b3a3938
        printf "Mismatch at 0x80001f78: got=0x%08x expected=0x3b3a3938 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f7c & 0xffffffff
      if $soc_actual != 0x3f3e3d3c
        printf "Mismatch at 0x80001f7c: got=0x%08x expected=0x3f3e3d3c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f80 & 0xffffffff
      if $soc_actual != 0x43424140
        printf "Mismatch at 0x80001f80: got=0x%08x expected=0x43424140 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f84 & 0xffffffff
      if $soc_actual != 0x47464544
        printf "Mismatch at 0x80001f84: got=0x%08x expected=0x47464544 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f88 & 0xffffffff
      if $soc_actual != 0x4b4a4948
        printf "Mismatch at 0x80001f88: got=0x%08x expected=0x4b4a4948 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f8c & 0xffffffff
      if $soc_actual != 0x4f4e4d4c
        printf "Mismatch at 0x80001f8c: got=0x%08x expected=0x4f4e4d4c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f90 & 0xffffffff
      if $soc_actual != 0x53525150
        printf "Mismatch at 0x80001f90: got=0x%08x expected=0x53525150 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f94 & 0xffffffff
      if $soc_actual != 0x57565554
        printf "Mismatch at 0x80001f94: got=0x%08x expected=0x57565554 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f98 & 0xffffffff
      if $soc_actual != 0x5b5a5958
        printf "Mismatch at 0x80001f98: got=0x%08x expected=0x5b5a5958 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f9c & 0xffffffff
      if $soc_actual != 0x5f5e5d5c
        printf "Mismatch at 0x80001f9c: got=0x%08x expected=0x5f5e5d5c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa0 & 0xffffffff
      if $soc_actual != 0x63626160
        printf "Mismatch at 0x80001fa0: got=0x%08x expected=0x63626160 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa4 & 0xffffffff
      if $soc_actual != 0x67666564
        printf "Mismatch at 0x80001fa4: got=0x%08x expected=0x67666564 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fa8 & 0xffffffff
      if $soc_actual != 0x6b6a6968
        printf "Mismatch at 0x80001fa8: got=0x%08x expected=0x6b6a6968 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fac & 0xffffffff
      if $soc_actual != 0x6f6e6d6c
        printf "Mismatch at 0x80001fac: got=0x%08x expected=0x6f6e6d6c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb0 & 0xffffffff
      if $soc_actual != 0x73727170
        printf "Mismatch at 0x80001fb0: got=0x%08x expected=0x73727170 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb4 & 0xffffffff
      if $soc_actual != 0x77767574
        printf "Mismatch at 0x80001fb4: got=0x%08x expected=0x77767574 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fb8 & 0xffffffff
      if $soc_actual != 0x7b7a7978
        printf "Mismatch at 0x80001fb8: got=0x%08x expected=0x7b7a7978 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001fbc & 0xffffffff
      if $soc_actual != 0x7f7e7d7c
        printf "Mismatch at 0x80001fbc: got=0x%08x expected=0x7f7e7d7c mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
    end
  end
  if $soc_check_errors == 0
    printf "FPGA_CHECK_PASS raw_full_b4_cpu checked_words=96 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
