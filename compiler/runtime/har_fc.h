/* ABI 1: ordinary volatile MMIO; no custom CPU instructions required.
 * Weights must already be in SRAM in plan_fc() order. A job is at most
 * K=64,N=32,B=4; consecutive accumulate jobs retain INT22 partial sums.
 */
#ifndef HAR_FC_H
#define HAR_FC_H
#include <stdint.h>
#include <stddef.h>
static inline volatile uint32_t *har_fc_reg(uint32_t offset) {
    return (volatile uint32_t *)(uintptr_t)(0x70000000u + offset);
}
static inline int har_fc_job(const int8_t *x, size_t input_stride,
                             const int32_t *bias, uint32_t weight_address,
                             unsigned k, unsigned n, unsigned batch,
                             int accumulate, int32_t *out, size_t output_stride) {
    if (!x || !bias || !out || !k || k>64 || !n || n>32 || !batch || batch>4 ||
        input_stride<k || output_stride<n || (*har_fc_reg(4)&2)) return -1;
    *har_fc_reg(0)=2;
    *har_fc_reg(0x3c)=accumulate ? 3:1;
    *har_fc_reg(0x80)=k; *har_fc_reg(0x84)=n;
    *har_fc_reg(0x18)=batch; *har_fc_reg(0x20)=weight_address;
    for (unsigned b=0;b<batch;++b) {
        unsigned base=b==0 ? 0x40 : b==1 ? 0xc00 : 0x1000+(b-2)*64;
        for (unsigned i=0;i<k;i+=4) {
            uint32_t word=0;
            for (unsigned lane=0;lane<4 && i+lane<k;++lane)
                word|=(uint32_t)(uint8_t)x[b*input_stride+i+lane]<<(lane*8);
            *har_fc_reg(base+i)=word;
        }
    }
    for (unsigned i=0;i<n;++i) *har_fc_reg(0x9c0+i*4)=(uint32_t)bias[i];
    *har_fc_reg(0)=1;
    unsigned timeout=1000000;
    uint32_t status;
    do { status=*har_fc_reg(4); } while ((status&2) && --timeout);
    if (!timeout || status!=1) return -2;
    for (unsigned b=0;b<batch;++b)
        for (unsigned i=0;i<n;++i)
            out[b*output_stride+i]=(int32_t)*har_fc_reg(0x1400+b*128+i*4);
    return 0;
}
#endif
