"""Static PyTorch FX capture with calibrated symmetric INT8 tensor boundaries."""
import operator
import numpy as np
import torch
from torch import nn
from torch.fx import Interpreter,symbolic_trace

class CompileError(ValueError): pass

class Capture(Interpreter):
    def __init__(self,graph):super().__init__(graph);self.values={}
    def run_node(self,node):
        value=super().run_node(node)
        if isinstance(value,torch.Tensor):self.values[node.name]=value.detach().cpu().clone()
        return value

def capture(model,example,calibration_inputs=None):
    if model.training:raise CompileError('Call model.eval() before compilation')
    try:graph=symbolic_trace(nn.Sequential(model) if isinstance(model,(nn.Linear,nn.ReLU,nn.Sigmoid,nn.Tanh,nn.Softmax,nn.Identity)) else model)
    except Exception as e:raise CompileError(f'FX capture failed: {e}') from e
    runs=[]
    for sample in list(calibration_inputs or [])+[example]:
        c=Capture(graph)
        with torch.no_grad():c.run(sample)
        runs.append(c.values)
    first=runs[-1];nodes=[];tensors={};output=None;input_name=None
    for node in graph.graph.nodes:
        if node.op=='output':
            if not isinstance(node.args[0],torch.fx.Node):raise CompileError('One tensor output required')
            output=node.args[0].name;continue
        if node.name not in first:raise CompileError(f'{node.name}: non-tensor graph values unsupported')
        value=first[node.name]
        if value.ndim!=2 or not 1<=value.shape[0]<=4 or value.shape[1]<1:
            raise CompileError(f'{node.name}: static [batch,features] tensors with batch 1..4 required')
        if any(tuple(r[node.name].shape)!=tuple(value.shape) for r in runs):raise CompileError('Dynamic shapes unsupported')
        if not all(torch.isfinite(r[node.name]).all() for r in runs):raise CompileError('Nonfinite calibration tensor')
        scale=max(max(float(r[node.name].abs().max()) for r in runs)/127,1e-12)
        tensors[node.name]=dict(shape=list(value.shape),scale=scale)
        if node.op=='placeholder':
            if input_name is not None:raise CompileError('One graph input required')
            input_name=node.name;continue
        args=[a.name for a in node.args if isinstance(a,torch.fx.Node)]
        op=None;extra={}
        if node.op=='call_module':
            m=graph.get_submodule(node.target)
            if isinstance(m,nn.Linear):
                op='linear';extra=dict(weight=m.weight.detach().cpu().numpy(),bias=(m.bias.detach().cpu().numpy() if m.bias is not None else np.zeros(m.out_features)))
            elif isinstance(m,nn.ReLU) and (not m.inplace or len(node.args[0].users)==1):op='relu'
            elif isinstance(m,nn.Sigmoid):op='sigmoid'
            elif isinstance(m,nn.Tanh):op='tanh'
            elif isinstance(m,nn.Softmax) and m.dim in (1,-1):op='softmax'
            elif isinstance(m,nn.Identity):op='identity'
            elif isinstance(m,nn.Flatten) and tuple(first[args[0]].shape)==tuple(value.shape):op='identity'
        elif node.op=='call_function':
            op={operator.add:'add',torch.add:'add',operator.sub:'sub',torch.sub:'sub',operator.mul:'mul',torch.mul:'mul',torch.relu:'relu',torch.sigmoid:'sigmoid',torch.tanh:'tanh'}.get(node.target)
            if node.target==torch.nn.functional.relu:op='relu'
            if node.target in (torch.softmax,torch.nn.functional.softmax) and node.kwargs.get('dim',node.args[1] if len(node.args)>1 else None) in (1,-1):op='softmax'
            if node.kwargs and not (op=='relu' and node.kwargs=={'inplace':False}) and not (op=='softmax' and set(node.kwargs)<= {'dim','dtype','_stacklevel'} and node.kwargs.get('dtype') is None):
                raise CompileError(f'{node.name}: operator keyword arguments unsupported: {node.kwargs}')
        elif node.op=='call_method':
            if node.target in ('relu','sigmoid','tanh'):op=node.target
            elif node.target in ('view','reshape','flatten','contiguous') and tuple(first[args[0]].shape)==tuple(value.shape):op='identity'
        if op is None:raise CompileError(f'{node.name}: no CPU kernel for {node.op} {node.target}')
        expected_args=2 if op in ('add','sub','mul') else 1
        if len(args)!=expected_args:
            constants=[v for v in node.args if isinstance(v,(int,float)) and not isinstance(v,bool)]
            if op in ('add','sub','mul') and len(args)==1 and len(node.args)==2 and len(constants)==1 and np.isfinite(constants[0]):
                extra.update(scalar=float(constants[0]),scalar_left=not isinstance(node.args[0],torch.fx.Node))
            else:raise CompileError(f'{node.name}: unsupported operands')
        if op!='linear' and any(tensors[a]['shape']!=list(value.shape) for a in args):
            raise CompileError(f'{node.name}: broadcasting unsupported')
        nodes.append(dict(name=node.name,op=op,inputs=args,**extra))
    if output is None or input_name is None:raise CompileError('Missing input/output')
    return dict(nodes=nodes,tensors=tensors,input=input_name,output=output,torch_graph=graph)
