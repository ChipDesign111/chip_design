# NPU regression

[tb_har_core.sv](tb_har_core.sv) compares hidden activations, signed scores and class IDs against independent gold. Each parameter case runs single and paired modes, including pipeline overlap, reset, busy START/ACK and sticky completion.

`python project.py test --suite unit` runs 1000 cases / 3000 inferences. `--count 12` is a debug subset. Vector generation has a fixed seed and rejects invalid integer ranges.
