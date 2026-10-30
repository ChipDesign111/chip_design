define soc-boot-status
  set $soc_boot = *(unsigned int *)0x0001003c
  set $soc_words = $soc_boot & 0xfff
  set $soc_ready = ($soc_boot >> 13) & 1
  printf "boot_status=0x%08x loaded_words=%d ready=%d\n", $soc_boot, $soc_words, $soc_ready
end

document soc-boot-status
Print the boot controller's loaded-word count and ready bit.
end

define soc-load-bin
  if $argc != 1
    printf "usage: soc-load-bin <image.bin>\n"
    error "soc-load-bin requires one binary image path"
  end

  set $soc_before = *(unsigned int *)0x0001003c
  if (($soc_before & 0x2000) != 0) || (($soc_before & 0xfff) != 0)
    printf "boot controller is not idle: status=0x%08x\n", $soc_before
    error "reset the SoC before loading a new image"
  end

  restore $arg0 binary 0x80000000

  set $soc_after = *(unsigned int *)0x0001003c
  set $soc_words = $soc_after & 0xfff
  set $soc_ready = ($soc_after >> 13) & 1
  if ($soc_words != 2048) || ($soc_ready != 0)
    printf "image was not accepted in order: status=0x%08x loaded_words=%d ready=%d\n", $soc_after, $soc_words, $soc_ready
    error "check image size, alignment and address order"
  end

  printf "image ready: status=0x%08x loaded_words=%d ready=0\n", $soc_after, $soc_words
  printf "use soc-commit-image to write the boot key\n"
end

document soc-load-bin
Load an 8 KiB little-endian binary at 0x80000000 and verify that all 2048 words were accepted in order.
end

define soc-commit-image
  set $soc_before = *(unsigned int *)0x0001003c
  set $soc_words = $soc_before & 0xfff
  set $soc_ready = ($soc_before >> 13) & 1
  if ($soc_words != 2048) || ($soc_ready != 0)
    printf "image is not ready to commit: status=0x%08x loaded_words=%d ready=%d\n", $soc_before, $soc_words, $soc_ready
    error "load a complete image before committing"
  end

  set {unsigned int}0x0001003c = 0xb007c0de
  set $soc_tries = 0
  while $soc_tries < 100 && ((*(unsigned int *)0x0001003c & 0x2000) == 0)
    set $soc_tries = $soc_tries + 1
  end

  set $soc_after = *(unsigned int *)0x0001003c
  set $soc_ready = ($soc_after >> 13) & 1
  if $soc_ready == 0
    printf "boot_ready did not assert: status=0x%08x\n", $soc_after
    error "boot key was not accepted"
  end

  printf "image committed: status=0x%08x loaded_words=%d ready=1\n", $soc_after, ($soc_after & 0xfff)
end

document soc-commit-image
Commit a fully loaded image with 0xb007c0de and wait for boot_ready.
end

define soc-check-final
  monitor halt
  maintenance flush register-cache
  info registers pc
  monitor reg pc
  x/3i $pc
  x/1wx 0x80001fe0
end

document soc-check-final
Halt the CPU, refresh GDB's register cache, and inspect the final PC and PASS flag.
end

define soc-resume-and-check-final
  monitor resume
  shell sleep 1
  soc-check-final
end

document soc-resume-and-check-final
Resume a committed image, wait one second, halt, and inspect the final CPU state.
end
