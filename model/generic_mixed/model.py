"""Executable deployment example: NPU FC + CPU activations/residual + NPU FC."""
import torch
from torch import nn

class Network(nn.Module):
    def __init__(self):
        super().__init__();self.fc1=nn.Linear(17,12);self.relu=nn.ReLU();self.sigmoid=nn.Sigmoid();self.fc2=nn.Linear(12,5)
    def forward(self,x):
        y=self.relu(self.fc1(x));z=self.sigmoid(y)
        return torch.softmax(self.fc2(z*y+y)*0.9+0.1,dim=1)

def build_model():
    with torch.random.fork_rng():
        torch.manual_seed(42)
        return Network().eval()
