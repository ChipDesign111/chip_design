"""Compiler ownership, tiling and specialization safety contracts."""
import sys,unittest
from pathlib import Path
import torch
from torch import nn
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from compiler.compiler import compile_model
from compiler.tasks import select_special_segments
from compiler.task_abi import Task,validate_segment
from run_task_compiler import special_network


class Planner(unittest.TestCase):
    def special(self,mutate=None):
        x=torch.linspace(0.5,1,256).reshape(4,64)
        p=compile_model(special_network(),x,[-x,x*0.5],task_engine=False)
        if mutate:mutate(p)
        before=bytes(p.memory.image)
        result=select_special_segments(p.nodes,p.graph['tensors'],p.memory,p.graph['output'])
        return p,result,before

    def test_special_layout_and_scale(self):
        p,segments,before=self.special();self.assertEqual(len(segments),1)
        s=segments[0];at=s['weight2']-0x80000000
        self.assertEqual(bytes(p.memory.image[at:at+192]),p.nodes[2]['qweight'].T.copy().tobytes())
        self.assertEqual(bytes(p.memory.image[at+192:at+256]),bytes(64))
        self.assertEqual(bytes(p.memory.image[:at]),before[:at])
        self.assertEqual(bytes(p.memory.image[at+256:]),before[at+256:])
        self.assertEqual(s['multiplier']*2**p.nodes[0]['shift'],p.nodes[0]['mult'][0]*2**s['shift'])

    def test_shape_is_insufficient(self):
        for mutate in [lambda p:p.nodes[1].update(mult=[3],shift=2),
            lambda p:p.nodes[0].update(mult=[65537],shift=0),
            lambda p:p.nodes[1].update(op='identity'),
            lambda p:p.nodes[2].update(backend='CPU'),
            lambda p:p.nodes.append(dict(name='branch',op='identity',inputs=[p.nodes[0]['name']]))]:
            p,segments,before=self.special(mutate)
            self.assertFalse(segments)
            self.assertEqual(bytes(p.memory.image),before)

    def test_single_sample_cost_choice(self):
        x=torch.linspace(0.5,1,64).reshape(1,64)
        p=compile_model(special_network(),x,[-x],task_engine=True)
        self.assertFalse(p.metadata['special_segments'])
        self.assertIn('single-sample',p.nodes[0]['specialization_note'])

    def test_tiny_cpu_choice(self):
        x=torch.ones(1,1);m=nn.Linear(1,1).eval()
        with torch.no_grad():m.weight.fill_(1);m.bias.zero_()
        old=compile_model(m,x,[-x],task_engine=False);new=compile_model(m,x,[-x],task_engine=True)
        self.assertEqual(old.nodes[0]['backend'],'NPU');self.assertEqual(new.nodes[0]['backend'],'CPU')

    def test_multi_output_consumer_spills(self):
        torch.manual_seed(74)
        m=nn.Sequential(nn.Linear(7,9),nn.ReLU(),nn.Linear(9,41)).eval();x=torch.linspace(-1,1,7).reshape(1,7)
        p=compile_model(m,x,[-x],task_engine=True)
        relu=p.graph['tensors'][p.nodes[1]['name']]
        self.assertNotEqual(relu.get('storage'),'internal')
        self.assertEqual(p.metadata['task_segments'][0]['count'],3)

    def test_wire_tables_and_partial_chain(self):
        torch.manual_seed(47);x=torch.linspace(-1,1,65).reshape(1,65)
        p=compile_model(nn.Sequential(nn.Linear(65,41),nn.ReLU(),nn.Linear(41,9)).eval(),x,[-x],task_engine=True)
        for segment in p.metadata['task_segments']:
            at=segment['address']-0x80000000
            tasks=[Task.unpack(p.memory.image[at+i*64:at+(i+1)*64]) for i in range(segment['count'])]
            validate_segment(segment['address'],tasks)
            self.assertEqual(len(tasks),5)
            self.assertFalse(tasks[0].last_k);self.assertFalse(tasks[1].initialize)
            self.assertFalse(tasks[2].last_k);self.assertFalse(tasks[3].initialize)
            self.assertFalse(tasks[4].input_internal) # input41 exceeds internal32


if __name__=='__main__':unittest.main(verbosity=2)
