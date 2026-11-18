"""Distinct sample rows and matrix boundaries for RAW weight reuse."""
import torch
from torch import nn


def fixtures():
    torch.manual_seed(181130)
    full = nn.Linear(64, 32).eval()
    cases = []
    for batch in range(1, 5):
        x = torch.linspace(-1, 1, batch*64).reshape(batch, 64)
        cases.append(('full_b%d' % batch, full, x))
    for name, batch, k, n in (('k_split_b4', 4, 128, 32),
                              ('n_split_b3', 3, 64, 64),
                              ('tail_b4', 4, 65, 33),
                              ('right_b3', 3, 65, 32),
                              ('bottom_b2', 2, 64, 33),
                              ('capacity_b4', 4, 176, 32)):
        model = nn.Linear(k, n).eval()
        cases.append((name, model, torch.linspace(-1, 1, batch*k).reshape(batch, k)))
    multi = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 64), nn.Tanh()).eval()
    cases.append(('multi_b2', multi, torch.linspace(-1, 1, 128).reshape(2, 64)))
    small = nn.Sequential(nn.Linear(17, 9), nn.ReLU(), nn.Linear(9, 5)).eval()
    cases.append(('cpu_only_b4', small, torch.linspace(-1, 1, 68).reshape(4, 17)))
    wide = nn.Linear(128, 32).eval()
    with torch.no_grad():
        wide.weight.fill_(0.25)
        wide.bias.copy_(torch.linspace(-300, 300, 32))
    cases.append(('wide_b3', wide, torch.linspace(-1, 1, 384).reshape(3, 128)))
    shift0 = nn.Linear(64, 32).eval()
    with torch.no_grad():
        shift0.weight[:, :32].fill_(0.25)
        shift0.weight[:, 32:].fill_(-0.25)
        shift0.bias.fill_(1e-6)
    cases.append(('shift0_b2', shift0, torch.stack((torch.ones(64), -torch.ones(64)))))
    return [(name, model, x, [-x, x*0.5]) for name, model, x in cases]
