"""Repeatable PyTorch graphs for current RAW deployment, not task-engine RTL."""
import torch
from torch import nn
from torch.nn import functional as F

from model.raw_mixed.model import build_model


class Arithmetic(nn.Module):
    def forward(self, x):
        a = F.relu6(x*3.0+0.25)
        b = F.leaky_relu(x, negative_slope=0.125)
        return torch.softmax(torch.tanh(a-b)+torch.sigmoid(x), dim=-1)


def fixtures():
    torch.manual_seed(181126)
    full = nn.Linear(64, 32).eval()
    tail = nn.Linear(65, 33).eval()
    batch = nn.Linear(64, 32).eval()
    wide = nn.Linear(64, 32).eval()
    with torch.no_grad():
        wide.weight.fill_(0.25)
        wide.bias.fill_(300)
    small = nn.Sequential(nn.Linear(17, 9), nn.ReLU(), nn.Linear(9, 5), nn.ReLU(), nn.Linear(5, 3)).eval()
    cases = [
        ('full', full, torch.linspace(-1, 1, 64).reshape(1, 64)),
        ('tail', tail, torch.linspace(-1, 1, 65).reshape(1, 65)),
        ('mixed', build_model().eval(), torch.linspace(-1, 1, 65).reshape(1, 65)),
        ('batch2', batch, torch.linspace(-1, 1, 128).reshape(2, 64)),
        ('beyond_int22', wide, torch.linspace(-1, 1, 64).reshape(1, 64)),
        ('small', small, torch.linspace(-1, 1, 17).reshape(1, 17)),
        ('arithmetic', Arithmetic().eval(), torch.linspace(-2, 2, 14).reshape(2, 7)),
        ('inplace_relu', nn.ReLU(inplace=True).eval(), torch.tensor([[-1.0, 2.0]])),
    ]
    return [(name, model, x, [-x, x*0.5]) for name, model, x in cases]
