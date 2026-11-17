"""Versioned little-endian task interface shared by compiler and NPU.

This is the frozen host contract, not a claim that the RTL engine exists yet.
Descriptors describe whole K/N blocks; 64-byte weight tiles are internal.
"""
from dataclasses import dataclass
from enum import IntEnum
import struct

VERSION=1
WORDS=16
BYTES=64
SRAM_BASE=0x80000000
SRAM_END=0x80002000
MMIO_BASE=0x70001600
INGRESS=0x70001640
PACKED_OUTPUT=0x70001680
LUT_WORD=0x70001700
CONTROL=0x00
STATUS=0x04
BASE=0x08
COUNT=0x0c
CAPABILITIES=0x10
INDEX=0x14
ERROR=0x18
CYCLES=0x1c
COMPLETED=0x20
REJECT_CODE=0x24
DONE=1
BUSY=2
FAILED=4
OUTPUT_VALID=8
REJECTED=16


class Op(IntEnum):
    FC=1
    ACTIVATION=2


class Activation(IntEnum):
    NONE=0
    RELU=1
    RELU6=2
    LEAKY_RELU=3
    SIGMOID=4
    TANH=5


class Error(IntEnum):
    NONE=0
    BUSY=1
    ALIGNMENT=2
    RANGE=3
    DESCRIPTOR=4
    CONTEXT=5
    DMA=6
    VALUE=7
    UNSUPPORTED=8


class TaskError(ValueError):
    def __init__(self,code,message):
        super().__init__(message);self.code=Error(code)


def checked(condition,code,message):
    if not condition:raise TaskError(code,message)


def align4(n):return (n+3)&~3


def region(address,size,alignment=4):
    checked(isinstance(address,int) and isinstance(size,int),Error.VALUE,'Noninteger region')
    checked(address%alignment==0,Error.ALIGNMENT,'Unaligned region')
    checked(size>0 and SRAM_BASE<=address<SRAM_END and address+size<=SRAM_END,
            Error.RANGE,'Region outside physical 8KiB SRAM')


def tensor_region(address,rows,stride,width):
    checked(stride>=align4(width) and stride%4==0,Error.VALUE,'Invalid row stride')
    # Include the full final bus word, although output WSTRB protects padding.
    region(address,(rows-1)*stride+align4(width))


@dataclass(frozen=True)
class Task:
    op:Op=Op.FC
    activation:Activation=Activation.NONE
    k:int=1
    n:int=1
    batch:int=1
    source:int=SRAM_BASE
    weights:int=SRAM_BASE
    bias:int=SRAM_BASE
    destination:int=SRAM_BASE
    input_stride:int=4
    output_stride:int=4
    initialize:bool=True
    last_k:bool=True
    input_internal:bool=False
    keep_output:bool=False
    end_segment:bool=True
    lut_cache:bool=False
    fc_multiplier:int=1
    fc_shift:int=0
    act_multiplier:int=1
    act_shift:int=0
    negative_multiplier:int=1
    negative_shift:int=0
    lut_address:int=0
    clamp_max:int=127
    context:int=0

    def validate(self,allow_cache=False):
        numeric=[self.k,self.n,self.batch,self.source,self.weights,self.bias,self.destination,
            self.input_stride,self.output_stride,self.fc_multiplier,self.fc_shift,self.act_multiplier,
            self.act_shift,self.negative_multiplier,self.negative_shift,self.lut_address,self.clamp_max,self.context]
        checked(all(type(v) is int for v in numeric),Error.VALUE,'Descriptor fields must be integers')
        checked(all(type(v) is bool for v in [self.initialize,self.last_k,self.input_internal,
            self.keep_output,self.end_segment,self.lut_cache]),Error.VALUE,'Flags must be bool')
        checked(all(0<=v<(1<<32) for v in [self.source,self.weights,self.bias,self.destination,self.lut_address]),
                Error.VALUE,'Address is not uint32')
        checked(self.op in tuple(Op) and self.activation in tuple(Activation),Error.UNSUPPORTED,'Unknown operator/activation')
        checked(0<=self.input_stride<=65535 and 0<=self.output_stride<=65535,Error.VALUE,'Stride exceeds16-bit field')
        checked(1<=self.n<=32 and 1<=self.batch<=4,Error.VALUE,'N/batch outside capability')
        if self.op==Op.FC:
            checked(1<=self.k<=64,Error.VALUE,'K outside capability')
            region(self.weights,((self.k+1)//2)*((self.n+7)//8)*16)
            if self.initialize:region(self.bias,self.n*4)
            else:checked(self.bias==0,Error.DESCRIPTOR,'Continuation has no bias load')
            if not self.last_k:
                checked(not self.keep_output and not self.end_segment and self.activation==Activation.NONE,
                        Error.CONTEXT,'Unfinished K accumulation cannot publish/end/activate')
                checked(self.destination==0 and self.output_stride==0,Error.DESCRIPTOR,'Partial sums have no output address')
        else:
            checked(self.k==0 and self.weights==0 and self.bias==0 and not self.initialize and self.last_k,
                    Error.DESCRIPTOR,'Activation task has FC-only fields')
            checked(self.fc_multiplier==0 and self.fc_shift==0,Error.DESCRIPTOR,'Activation has FC scaling')
        width=self.k if self.op==Op.FC else self.n
        if self.input_internal:
            checked(width<=32 and self.source==0 and self.input_stride==0,
                    Error.VALUE,'Internal tensor has at most32 elements per sample')
        else:tensor_region(self.source,self.batch,self.input_stride,width)
        if self.last_k:
            if self.keep_output:
                checked(self.destination==0 and self.output_stride==0,Error.DESCRIPTOR,'Internal output has SRAM address')
            else:tensor_region(self.destination,self.batch,self.output_stride,self.n)
        for value in [self.fc_multiplier,self.act_multiplier,self.negative_multiplier]:
            checked(-(1<<31)<=value<(1<<31),Error.VALUE,'Multiplier is not signed32')
        checked(all(0<=s<=24 for s in [self.fc_shift,self.act_shift,self.negative_shift]),Error.VALUE,'Shift outside0..24')
        checked(0<=self.clamp_max<=127 and 0<=self.context<(1<<32),Error.VALUE,'Clamp/context outside encoding')
        if self.activation in (Activation.SIGMOID,Activation.TANH):region(self.lut_address,256)
        else:checked(self.lut_address==0 and not self.lut_cache,Error.DESCRIPTOR,'Non-LUT activation has LUT fields')
        checked(not self.lut_cache or allow_cache,Error.UNSUPPORTED,'LUT cache not enabled for this target')
        return self

    def words(self):
        flags=sum(int(v)<<bit for bit,v in enumerate([self.initialize,self.last_k,self.input_internal,
            self.keep_output,self.end_segment,self.lut_cache],16))
        return [VERSION|(int(self.op)<<8)|(int(self.activation)<<12)|flags,
            self.k|(self.n<<8)|(self.batch<<16),self.source,self.weights,self.bias,self.destination,
            self.input_stride|(self.output_stride<<16),self.fc_multiplier&0xffffffff,
            self.fc_shift|(self.act_shift<<8)|(self.negative_shift<<16),
            self.act_multiplier&0xffffffff,self.negative_multiplier&0xffffffff,self.lut_address,
            self.clamp_max,self.context,0,0]

    def pack(self,allow_cache=False):
        self.validate(allow_cache)
        return struct.pack('<16I',*self.words())

    @classmethod
    def unpack(cls,data,allow_cache=False):
        checked(len(data)==BYTES,Error.DESCRIPTOR,'Descriptor must be64 bytes')
        w=struct.unpack('<16I',data)
        checked(w[0]&255==VERSION,Error.UNSUPPORTED,'Unknown descriptor version')
        checked(w[0]&0xffc00000==0 and w[1]&0xff000000==0 and w[8]&0xff000000==0 and
                w[12]<=127 and w[14]==w[15]==0,Error.DESCRIPTOR,'Reserved bits are nonzero')
        try:op=Op((w[0]>>8)&15);activation=Activation((w[0]>>12)&15)
        except ValueError:raise TaskError(Error.UNSUPPORTED,'Unknown operator/activation') from None
        signed=lambda v:v-(1<<32) if v>>31 else v
        task=cls(op=op,activation=activation,k=w[1]&255,n=(w[1]>>8)&255,batch=(w[1]>>16)&255,
            source=w[2],weights=w[3],bias=w[4],destination=w[5],input_stride=w[6]&65535,output_stride=w[6]>>16,
            initialize=bool(w[0]&(1<<16)),last_k=bool(w[0]&(1<<17)),input_internal=bool(w[0]&(1<<18)),
            keep_output=bool(w[0]&(1<<19)),end_segment=bool(w[0]&(1<<20)),lut_cache=bool(w[0]&(1<<21)),
            fc_multiplier=signed(w[7]),fc_shift=w[8]&255,act_shift=(w[8]>>8)&255,negative_shift=(w[8]>>16)&255,
            act_multiplier=signed(w[9]),negative_multiplier=signed(w[10]),lut_address=w[11],clamp_max=w[12],context=w[13])
        return task.validate(allow_cache)


def validate_segment(base,tasks,allow_cache=False):
    tasks=list(tasks)
    checked(1<=len(tasks)<=128,Error.VALUE,'COUNT must be1..128')
    region(base,len(tasks)*BYTES,alignment=64)
    partial=None;forward=None
    for index,task in enumerate(tasks):
        task.validate(allow_cache)
        checked(task.end_segment==(index==len(tasks)-1),Error.DESCRIPTOR,'END must match COUNT exactly')
        if partial is not None:
            checked(task.op==Op.FC and not task.initialize and
                    partial==(task.context,task.n,task.batch),Error.CONTEXT,'Partial sums are not a contiguous matching chain')
        elif task.op==Op.FC:checked(task.initialize,Error.CONTEXT,'Continuation without initialized sums')
        if task.input_internal:
            width=task.k if task.op==Op.FC else task.n
            checked(forward==(width,task.batch),Error.CONTEXT,'No matching forward tensor')
            forward=None
        if task.last_k:
            partial=None
            if task.keep_output:forward=(task.n,task.batch)
            else:
                forward=None
                end=task.destination+(task.batch-1)*task.output_stride+align4(task.n)
                checked(end<=base or task.destination>=base+len(tasks)*BYTES,Error.RANGE,'Output overwrites task table')
        else:partial=(task.context,task.n,task.batch)
    return tasks


def rescale(value,multiplier,shift):
    checked(0<=shift<=24,Error.VALUE,'Shift outside0..24')
    product=int(value)*int(multiplier)
    if shift:product=(product+(1<<(shift-1)))>>shift
    return max(-128,min(127,product))


def activate(value,mode,multiplier=1,shift=0,negative_multiplier=1,negative_shift=0,clamp_max=127,lut=None):
    """Input already quantized INT8; preserve this boundary after FC."""
    checked(-128<=value<=127,Error.VALUE,'Activation input must beINT8')
    checked(mode in tuple(Activation),Error.UNSUPPORTED,'Unknown activation')
    checked(0<=clamp_max<=127,Error.VALUE,'Invalid activation clamp')
    if mode in (Activation.SIGMOID,Activation.TANH):
        checked(lut is not None and len(lut)==256,Error.VALUE,'Expected256-entry signed INT8 LUT')
        result=int(lut[value+128]);checked(-128<=result<=255,Error.VALUE,'Invalid LUT value')
        return result-256 if result>=128 else result
    if mode in (Activation.RELU,Activation.RELU6):value=max(0,value)
    if mode==Activation.LEAKY_RELU and value<0:
        return rescale(value,negative_multiplier,negative_shift)
    result=rescale(value,multiplier,shift)
    return min(result,clamp_max) if mode==Activation.RELU6 else result


def fc_output(accumulator,task,lut=None):
    checked(task.last_k,Error.CONTEXT,'Intermediate K block has no quantized output')
    checked(-(1<<21)<=accumulator<(1<<21),Error.VALUE,'FC input must be signedINT22')
    q=rescale(accumulator,task.fc_multiplier,task.fc_shift)
    return activate(q,task.activation,task.act_multiplier,task.act_shift,
        task.negative_multiplier,task.negative_shift,task.clamp_max,lut)
