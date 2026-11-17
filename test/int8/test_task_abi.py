"""Independent wire vectors, malformed segments and exhaustive INT8 semantics."""
import random
import struct
import sys
import unittest
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from compiler.task_abi import (Task,Op,Activation,Error,TaskError,SRAM_BASE,
    validate_segment,rescale,activate,fc_output)


def reference_scale(v,m,s):
    # Euclidean division independently states nearest, ties toward +infinity.
    q,r=divmod(v*m,2**s)
    if s and r>=2**(s-1):q+=1
    return min(127,max(-128,q))


class TaskABI(unittest.TestCase):
    def bad(self,code,call):
        with self.assertRaises(TaskError) as caught:call()
        self.assertEqual(caught.exception.code,code)

    def test_independent_wire_vector(self):
        t=Task(activation=Activation.LEAKY_RELU,k=7,n=5,batch=2,
            source=0x80000400,weights=0x80000800,bias=0x80000a00,
            destination=0x80000b00,input_stride=8,output_stride=8,
            fc_multiplier=-17,fc_shift=4,act_multiplier=19,act_shift=3,
            negative_multiplier=23,negative_shift=7,clamp_max=93,context=0xfedcba98)
        expected=[0x00133101,0x00020507,0x80000400,0x80000800,0x80000a00,
            0x80000b00,0x00080008,0xffffffef,0x00070304,19,23,0,93,0xfedcba98,0,0]
        raw=struct.pack('<16I',*expected)
        self.assertEqual(t.pack(),raw)
        self.assertEqual(Task.unpack(raw),t)
        self.assertEqual(raw[:4],bytes.fromhex('01311300'))

    def test_encoding_rejections(self):
        w=Task().words()
        for index,mask in [(0,1<<22),(1,1<<24),(8,1<<24),(14,1),(15,1)]:
            a=w.copy();a[index]|=mask
            self.bad(Error.DESCRIPTOR,lambda a=a:Task.unpack(struct.pack('<16I',*a)))
        for value in [0x130100,0x130901,0x139101]:
            a=w.copy();a[0]=value
            self.bad(Error.UNSUPPORTED,lambda a=a:Task.unpack(struct.pack('<16I',*a)))
        self.bad(Error.DESCRIPTOR,lambda:Task.unpack(b'\0'*63))
        for field,value,code in [('source',0x80000001,Error.ALIGNMENT),
            ('weights',0x80001ffc,Error.RANGE),('source',0x80001ffc,Error.RANGE),
            ('destination',0x80001ffc,Error.RANGE),('bias',0x80001ffc,Error.RANGE),
            ('fc_shift',25,Error.VALUE),('batch',5,Error.VALUE),('n',33,Error.VALUE),
            ('k',65,Error.VALUE),('source',2**32,Error.VALUE),('k',True,Error.VALUE),
            ('initialize',1,Error.VALUE),('input_stride',65536,Error.VALUE)]:
            t=replace(Task(k=7,n=5,batch=2,input_stride=8,output_stride=8),**{field:value})
            self.bad(code,lambda t=t:t.pack())
        self.bad(Error.DESCRIPTOR,lambda:replace(Task(),initialize=False).pack())

    def test_end_and_partial_context(self):
        base=0x80001000
        first=Task(k=64,n=5,destination=0,output_stride=0,last_k=False,
            end_segment=False,context=91,input_stride=64)
        last=Task(k=1,n=5,initialize=False,bias=0,context=91,output_stride=8)
        self.assertEqual(len(validate_segment(base,[first,last])),2)
        for task in [replace(last,context=90),replace(last,n=4),
                     replace(last,batch=2),replace(last,initialize=True,bias=SRAM_BASE)]:
            self.bad(Error.CONTEXT,lambda task=task:validate_segment(base,[first,task]))
        self.bad(Error.CONTEXT,lambda:validate_segment(base,[last]))
        self.bad(Error.DESCRIPTOR,lambda:validate_segment(base,[Task(end_segment=False)]))
        self.bad(Error.VALUE,lambda:validate_segment(base,[]))
        self.bad(Error.VALUE,lambda:validate_segment(base,[Task()]*129))
        self.bad(Error.ALIGNMENT,lambda:validate_segment(base+4,[Task()]))
        self.bad(Error.RANGE,lambda:validate_segment(base,[Task(destination=base)]))
        self.bad(Error.RANGE,lambda:validate_segment(0x80001fc0,[first,last]))

    def test_internal_lifetime(self):
        first=Task(n=7,keep_output=True,destination=0,output_stride=0,end_segment=False)
        last=Task(k=7,input_internal=True,source=0,input_stride=0)
        validate_segment(0x80001000,[first,last])
        self.bad(Error.CONTEXT,lambda:validate_segment(0x80001000,[last]))
        self.bad(Error.CONTEXT,lambda:validate_segment(0x80001000,[first,replace(last,k=8)]))
        # A buffer is consumed once, and SRAM output revokes stale forwarding.
        middle=replace(last,end_segment=False)
        self.bad(Error.CONTEXT,lambda:validate_segment(0x80001000,[first,middle,last]))

    def test_activation_descriptor(self):
        t=Task(op=Op.ACTIVATION,k=0,n=17,weights=0,bias=0,initialize=False,
            fc_multiplier=0,fc_shift=0,input_stride=20,output_stride=20,
            activation=Activation.TANH,lut_address=0x80001f00)
        self.assertEqual(Task.unpack(t.pack()),t)
        self.bad(Error.UNSUPPORTED,lambda:replace(t,lut_cache=True).pack())
        self.assertEqual(Task.unpack(replace(t,lut_cache=True).pack(True),True),replace(t,lut_cache=True))
        self.bad(Error.RANGE,lambda:replace(t,lut_address=0x80001f04).pack())
        self.bad(Error.DESCRIPTOR,lambda:replace(t,fc_multiplier=1).pack())

    def test_integer_semantics(self):
        rng=random.Random(1841)
        values=[-(1<<21),-(1<<21)+1,-129,-128,-127,-3,-2,-1,0,1,2,3,126,127,128,(1<<21)-1]
        multipliers=[-(1<<31),-65537,-3,-1,0,1,3,65537,(1<<31)-1]
        for v in values+[rng.randrange(-(1<<21),1<<21) for _ in range(100)]:
            for m in multipliers:
                for s in range(25):self.assertEqual(rescale(v,m,s),reference_scale(v,m,s))
        signed_lut=[(i*73)%256-128 for i in range(256)]
        byte_lut=bytes(v&255 for v in signed_lut)
        for v in range(-128,128):
            for m,s,nm,ns in [(1,0,1,3),(17,4,5,7),(2**31-1,24,2**31-1,24)]:
                for mode in Activation:
                    if mode in [Activation.SIGMOID,Activation.TANH]:expected=signed_lut[v+128]
                    else:
                        x=max(0,v) if mode in [Activation.RELU,Activation.RELU6] else v
                        expected=reference_scale(x,nm,ns) if mode==Activation.LEAKY_RELU and x<0 else reference_scale(x,m,s)
                        if mode==Activation.RELU6:expected=min(expected,67)
                    self.assertEqual(activate(v,mode,m,s,nm,ns,67,byte_lut),expected)
                    self.assertEqual(activate(v,mode,m,s,nm,ns,67,signed_lut),expected)
        t=Task(act_shift=1)
        self.assertEqual(fc_output(400,t),64) # saturation to127, then second rounding
        self.assertNotEqual(fc_output(400,t),rescale(400,1,1))
        self.assertEqual(rescale(-3,1,1),-1) # negative half rounds toward +infinity


if __name__=='__main__':unittest.main(verbosity=2)
