# Generated; source from the fpga directory after running and halting this image.
define soc-check-result
  set $soc_check_errors = 0
  if *(unsigned int *)0x80001fe4 != 0xb81dce62
    printf "FPGA_CHECK_FAIL: wrong image tag for raw_multi_b2_raw\n"
    set $soc_check_errors = $soc_check_errors + 1
  else
    if *(unsigned int *)0x80001fe0 != 0xc0dec0de
      printf "FPGA_CHECK_FAIL: firmware status is not PASS\n"
      set $soc_check_errors = $soc_check_errors + 1
    else
      set $soc_actual = *(unsigned int *)0x80001dc0 & 0xffffffff
      if $soc_actual != 0xdf020b39
        printf "Mismatch at 0x80001dc0: got=0x%08x expected=0xdf020b39 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc4 & 0xffffffff
      if $soc_actual != 0x08e620c5
        printf "Mismatch at 0x80001dc4: got=0x%08x expected=0x08e620c5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dc8 & 0xffffffff
      if $soc_actual != 0x1f43d63d
        printf "Mismatch at 0x80001dc8: got=0x%08x expected=0x1f43d63d mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dcc & 0xffffffff
      if $soc_actual != 0x13fefa13
        printf "Mismatch at 0x80001dcc: got=0x%08x expected=0x13fefa13 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd0 & 0xffffffff
      if $soc_actual != 0x093b3927
        printf "Mismatch at 0x80001dd0: got=0x%08x expected=0x093b3927 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd4 & 0xffffffff
      if $soc_actual != 0x1e27dea2
        printf "Mismatch at 0x80001dd4: got=0x%08x expected=0x1e27dea2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dd8 & 0xffffffff
      if $soc_actual != 0x0118fe24
        printf "Mismatch at 0x80001dd8: got=0x%08x expected=0x0118fe24 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ddc & 0xffffffff
      if $soc_actual != 0x15f7cfd4
        printf "Mismatch at 0x80001ddc: got=0x%08x expected=0x15f7cfd4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de0 & 0xffffffff
      if $soc_actual != 0x470d3be3
        printf "Mismatch at 0x80001de0: got=0x%08x expected=0x470d3be3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de4 & 0xffffffff
      if $soc_actual != 0x44aadd44
        printf "Mismatch at 0x80001de4: got=0x%08x expected=0x44aadd44 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001de8 & 0xffffffff
      if $soc_actual != 0xd612faf6
        printf "Mismatch at 0x80001de8: got=0x%08x expected=0xd612faf6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dec & 0xffffffff
      if $soc_actual != 0xeeb311d5
        printf "Mismatch at 0x80001dec: got=0x%08x expected=0xeeb311d5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df0 & 0xffffffff
      if $soc_actual != 0x073e13de
        printf "Mismatch at 0x80001df0: got=0x%08x expected=0x073e13de mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df4 & 0xffffffff
      if $soc_actual != 0x2b09005f
        printf "Mismatch at 0x80001df4: got=0x%08x expected=0x2b09005f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001df8 & 0xffffffff
      if $soc_actual != 0xf703e3ba
        printf "Mismatch at 0x80001df8: got=0x%08x expected=0xf703e3ba mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001dfc & 0xffffffff
      if $soc_actual != 0x5deaf5d0
        printf "Mismatch at 0x80001dfc: got=0x%08x expected=0x5deaf5d0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e00 & 0xffffffff
      if $soc_actual != 0xce180efd
        printf "Mismatch at 0x80001e00: got=0x%08x expected=0xce180efd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e04 & 0xffffffff
      if $soc_actual != 0x0f042ebd
        printf "Mismatch at 0x80001e04: got=0x%08x expected=0x0f042ebd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e08 & 0xffffffff
      if $soc_actual != 0x19d513f4
        printf "Mismatch at 0x80001e08: got=0x%08x expected=0x19d513f4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e0c & 0xffffffff
      if $soc_actual != 0x1ac3fa33
        printf "Mismatch at 0x80001e0c: got=0x%08x expected=0x1ac3fa33 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e10 & 0xffffffff
      if $soc_actual != 0x23fa39ed
        printf "Mismatch at 0x80001e10: got=0x%08x expected=0x23fa39ed mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e14 & 0xffffffff
      if $soc_actual != 0x32be2e03
        printf "Mismatch at 0x80001e14: got=0x%08x expected=0x32be2e03 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e18 & 0xffffffff
      if $soc_actual != 0xede3df0f
        printf "Mismatch at 0x80001e18: got=0x%08x expected=0xede3df0f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e1c & 0xffffffff
      if $soc_actual != 0xee2581fd
        printf "Mismatch at 0x80001e1c: got=0x%08x expected=0xee2581fd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e20 & 0xffffffff
      if $soc_actual != 0x3a62efe0
        printf "Mismatch at 0x80001e20: got=0x%08x expected=0x3a62efe0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e24 & 0xffffffff
      if $soc_actual != 0x55dacf11
        printf "Mismatch at 0x80001e24: got=0x%08x expected=0x55dacf11 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e28 & 0xffffffff
      if $soc_actual != 0x3b4a33dd
        printf "Mismatch at 0x80001e28: got=0x%08x expected=0x3b4a33dd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e2c & 0xffffffff
      if $soc_actual != 0xfce713db
        printf "Mismatch at 0x80001e2c: got=0x%08x expected=0xfce713db mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e30 & 0xffffffff
      if $soc_actual != 0xadf3f4e6
        printf "Mismatch at 0x80001e30: got=0x%08x expected=0xadf3f4e6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e34 & 0xffffffff
      if $soc_actual != 0xeaceeedd
        printf "Mismatch at 0x80001e34: got=0x%08x expected=0xeaceeedd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e38 & 0xffffffff
      if $soc_actual != 0xd93012f8
        printf "Mismatch at 0x80001e38: got=0x%08x expected=0xd93012f8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e3c & 0xffffffff
      if $soc_actual != 0x12081413
        printf "Mismatch at 0x80001e3c: got=0x%08x expected=0x12081413 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e40 & 0xffffffff
      if $soc_actual != 0xe2020a34
        printf "Mismatch at 0x80001e40: got=0x%08x expected=0xe2020a34 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e44 & 0xffffffff
      if $soc_actual != 0x07e81dca
        printf "Mismatch at 0x80001e44: got=0x%08x expected=0x07e81dca mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e48 & 0xffffffff
      if $soc_actual != 0x1c3eda38
        printf "Mismatch at 0x80001e48: got=0x%08x expected=0x1c3eda38 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e4c & 0xffffffff
      if $soc_actual != 0x11fefb11
        printf "Mismatch at 0x80001e4c: got=0x%08x expected=0x11fefb11 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e50 & 0xffffffff
      if $soc_actual != 0x08363424
        printf "Mismatch at 0x80001e50: got=0x%08x expected=0x08363424 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e54 & 0xffffffff
      if $soc_actual != 0x1b24e1a7
        printf "Mismatch at 0x80001e54: got=0x%08x expected=0x1b24e1a7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e58 & 0xffffffff
      if $soc_actual != 0x0116fe21
        printf "Mismatch at 0x80001e58: got=0x%08x expected=0x0116fe21 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e5c & 0xffffffff
      if $soc_actual != 0x13f8d3d8
        printf "Mismatch at 0x80001e5c: got=0x%08x expected=0x13f8d3d8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e60 & 0xffffffff
      if $soc_actual != 0x420c36e6
        printf "Mismatch at 0x80001e60: got=0x%08x expected=0x420c36e6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e64 & 0xffffffff
      if $soc_actual != 0x3fafe03f
        printf "Mismatch at 0x80001e64: got=0x%08x expected=0x3fafe03f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e68 & 0xffffffff
      if $soc_actual != 0xda10fbf7
        printf "Mismatch at 0x80001e68: got=0x%08x expected=0xda10fbf7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e6c & 0xffffffff
      if $soc_actual != 0xf0b80fd9
        printf "Mismatch at 0x80001e6c: got=0x%08x expected=0xf0b80fd9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e70 & 0xffffffff
      if $soc_actual != 0x063911e1
        printf "Mismatch at 0x80001e70: got=0x%08x expected=0x063911e1 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e74 & 0xffffffff
      if $soc_actual != 0x2708005b
        printf "Mismatch at 0x80001e74: got=0x%08x expected=0x2708005b mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e78 & 0xffffffff
      if $soc_actual != 0xf803e6bf
        printf "Mismatch at 0x80001e78: got=0x%08x expected=0xf803e6bf mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e7c & 0xffffffff
      if $soc_actual != 0x58ecf6d4
        printf "Mismatch at 0x80001e7c: got=0x%08x expected=0x58ecf6d4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e80 & 0xffffffff
      if $soc_actual != 0xd2160dfd
        printf "Mismatch at 0x80001e80: got=0x%08x expected=0xd2160dfd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e84 & 0xffffffff
      if $soc_actual != 0x0e042ac2
        printf "Mismatch at 0x80001e84: got=0x%08x expected=0x0e042ac2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e88 & 0xffffffff
      if $soc_actual != 0x17d911f5
        printf "Mismatch at 0x80001e88: got=0x%08x expected=0x17d911f5 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e8c & 0xffffffff
      if $soc_actual != 0x18c8fb2f
        printf "Mismatch at 0x80001e8c: got=0x%08x expected=0x18c8fb2f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e90 & 0xffffffff
      if $soc_actual != 0x20fb34ef
        printf "Mismatch at 0x80001e90: got=0x%08x expected=0x20fb34ef mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e94 & 0xffffffff
      if $soc_actual != 0x2ec32a03
        printf "Mismatch at 0x80001e94: got=0x%08x expected=0x2ec32a03 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e98 & 0xffffffff
      if $soc_actual != 0xefe6e20e
        printf "Mismatch at 0x80001e98: got=0x%08x expected=0xefe6e20e mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001e9c & 0xffffffff
      if $soc_actual != 0xf02281fd
        printf "Mismatch at 0x80001e9c: got=0x%08x expected=0xf02281fd mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea0 & 0xffffffff
      if $soc_actual != 0x355ef1e3
        printf "Mismatch at 0x80001ea0: got=0x%08x expected=0x355ef1e3 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea4 & 0xffffffff
      if $soc_actual != 0x50ddd30f
        printf "Mismatch at 0x80001ea4: got=0x%08x expected=0x50ddd30f mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ea8 & 0xffffffff
      if $soc_actual != 0x36452fe0
        printf "Mismatch at 0x80001ea8: got=0x%08x expected=0x36452fe0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eac & 0xffffffff
      if $soc_actual != 0xfce911de
        printf "Mismatch at 0x80001eac: got=0x%08x expected=0xfce911de mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb0 & 0xffffffff
      if $soc_actual != 0xb2f4f5e8
        printf "Mismatch at 0x80001eb0: got=0x%08x expected=0xb2f4f5e8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb4 & 0xffffffff
      if $soc_actual != 0xecd2f0e0
        printf "Mismatch at 0x80001eb4: got=0x%08x expected=0xecd2f0e0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eb8 & 0xffffffff
      if $soc_actual != 0xdc2c10f9
        printf "Mismatch at 0x80001eb8: got=0x%08x expected=0xdc2c10f9 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ebc & 0xffffffff
      if $soc_actual != 0x10071211
        printf "Mismatch at 0x80001ebc: got=0x%08x expected=0x10071211 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec0 & 0xffffffff
      if $soc_actual != 0x0b2e0000
        printf "Mismatch at 0x80001ec0: got=0x%08x expected=0x0b2e0000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec4 & 0xffffffff
      if $soc_actual != 0x3e3d1d03
        printf "Mismatch at 0x80001ec4: got=0x%08x expected=0x3e3d1d03 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ec8 & 0xffffffff
      if $soc_actual != 0x00016626
        printf "Mismatch at 0x80001ec8: got=0x%08x expected=0x00016626 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ecc & 0xffffffff
      if $soc_actual != 0x000e0000
        printf "Mismatch at 0x80001ecc: got=0x%08x expected=0x000e0000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed0 & 0xffffffff
      if $soc_actual != 0x002e004a
        printf "Mismatch at 0x80001ed0: got=0x%08x expected=0x002e004a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed4 & 0xffffffff
      if $soc_actual != 0x00000300
        printf "Mismatch at 0x80001ed4: got=0x%08x expected=0x00000300 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ed8 & 0xffffffff
      if $soc_actual != 0x00180000
        printf "Mismatch at 0x80001ed8: got=0x%08x expected=0x00180000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001edc & 0xffffffff
      if $soc_actual != 0x394f0000
        printf "Mismatch at 0x80001edc: got=0x%08x expected=0x394f0000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee0 & 0xffffffff
      if $soc_actual != 0x0000112a
        printf "Mismatch at 0x80001ee0: got=0x%08x expected=0x0000112a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee4 & 0xffffffff
      if $soc_actual != 0x00070016
        printf "Mismatch at 0x80001ee4: got=0x%08x expected=0x00070016 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ee8 & 0xffffffff
      if $soc_actual != 0x16000000
        printf "Mismatch at 0x80001ee8: got=0x%08x expected=0x16000000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001eec & 0xffffffff
      if $soc_actual != 0x441a3920
        printf "Mismatch at 0x80001eec: got=0x%08x expected=0x441a3920 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef0 & 0xffffffff
      if $soc_actual != 0x3c314700
        printf "Mismatch at 0x80001ef0: got=0x%08x expected=0x3c314700 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef4 & 0xffffffff
      if $soc_actual != 0x132c0000
        printf "Mismatch at 0x80001ef4: got=0x%08x expected=0x132c0000 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001ef8 & 0xffffffff
      if $soc_actual != 0x00002100
        printf "Mismatch at 0x80001ef8: got=0x%08x expected=0x00002100 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001efc & 0xffffffff
      if $soc_actual != 0x35002972
        printf "Mismatch at 0x80001efc: got=0x%08x expected=0x35002972 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f00 & 0xffffffff
      if $soc_actual != 0x0b2ee400
        printf "Mismatch at 0x80001f00: got=0x%08x expected=0x0b2ee400 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f04 & 0xffffffff
      if $soc_actual != 0x3e3d1d03
        printf "Mismatch at 0x80001f04: got=0x%08x expected=0x3e3d1d03 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f08 & 0xffffffff
      if $soc_actual != 0xd7016626
        printf "Mismatch at 0x80001f08: got=0x%08x expected=0xd7016626 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f0c & 0xffffffff
      if $soc_actual != 0xdc0ed3f7
        printf "Mismatch at 0x80001f0c: got=0x%08x expected=0xdc0ed3f7 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f10 & 0xffffffff
      if $soc_actual != 0xd52eff4a
        printf "Mismatch at 0x80001f10: got=0x%08x expected=0xd52eff4a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f14 & 0xffffffff
      if $soc_actual != 0xf2d703e6
        printf "Mismatch at 0x80001f14: got=0x%08x expected=0xf2d703e6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f18 & 0xffffffff
      if $soc_actual != 0xe218ace4
        printf "Mismatch at 0x80001f18: got=0x%08x expected=0xe218ace4 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f1c & 0xffffffff
      if $soc_actual != 0x394ff7d6
        printf "Mismatch at 0x80001f1c: got=0x%08x expected=0x394ff7d6 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f20 & 0xffffffff
      if $soc_actual != 0xeca3112a
        printf "Mismatch at 0x80001f20: got=0x%08x expected=0xeca3112a mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f24 & 0xffffffff
      if $soc_actual != 0xa407da16
        printf "Mismatch at 0x80001f24: got=0x%08x expected=0xa407da16 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f28 & 0xffffffff
      if $soc_actual != 0x16fc93fc
        printf "Mismatch at 0x80001f28: got=0x%08x expected=0x16fc93fc mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f2c & 0xffffffff
      if $soc_actual != 0x441a3920
        printf "Mismatch at 0x80001f2c: got=0x%08x expected=0x441a3920 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f30 & 0xffffffff
      if $soc_actual != 0x3c3147f2
        printf "Mismatch at 0x80001f30: got=0x%08x expected=0x3c3147f2 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f34 & 0xffffffff
      if $soc_actual != 0x132cc2f8
        printf "Mismatch at 0x80001f34: got=0x%08x expected=0x132cc2f8 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f38 & 0xffffffff
      if $soc_actual != 0xdaf421f0
        printf "Mismatch at 0x80001f38: got=0x%08x expected=0xdaf421f0 mask=0xffffffff\n", $soc_actual
        set $soc_check_errors = $soc_check_errors + 1
      end
      set $soc_actual = *(unsigned int *)0x80001f3c & 0xffffffff
      if $soc_actual != 0x35c12972
        printf "Mismatch at 0x80001f3c: got=0x%08x expected=0x35c12972 mask=0xffffffff\n", $soc_actual
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
    printf "FPGA_CHECK_PASS raw_multi_b2_raw checked_words=128 full_soc_cycles=%u\n", *(unsigned int *)0x00010038
  else
    printf "FPGA_CHECK_FAIL errors=%d\n", $soc_check_errors
  end
end

document soc-check-result
Check the image tag, PASS status and all input/intermediate/output tensor words.
Read $soc_check_errors for a machine-readable failure count. CPU must be halted.
end
