"""Fixed demonstration graph for the current RAW backend, not trained weights."""
import torch
from torch import nn


class Network(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(65, 33)
        self.fc2 = nn.Linear(33, 5)

    def forward(self, x):
        h = torch.relu(self.fc1(x))
        mixed = torch.sigmoid(h)*0.5 + h*0.25
        return torch.softmax(self.fc2(mixed)+0.125, dim=-1)


def build_model():
    torch.manual_seed(181126)
    return Network()
