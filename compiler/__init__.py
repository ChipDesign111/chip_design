"""PyTorch deployment to the existing INT22 RAW SoC; no task-engine RTL."""


def compile_model(*args, **kwargs):
    from .compiler import compile_model as compile_graph
    return compile_graph(*args, **kwargs)


def compile_layers(*args, **kwargs):
    from .integer import compile_layers as compile_integer
    return compile_integer(*args, **kwargs)
