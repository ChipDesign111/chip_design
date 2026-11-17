/* Task ABI v1. The target must advertise capabilities before this API is used.
 * Descriptor/table validation and tensor lifetime allocation are compiler work.
 * Host owns all referenced memory exclusively until DONE or reset. */
#ifndef HAR_TASK_H
#define HAR_TASK_H
#include <stdint.h>
#include <stddef.h>
typedef struct {
    uint32_t header, shape, source, weights, bias, destination, strides;
    int32_t fc_multiplier;
    uint32_t shifts;
    int32_t act_multiplier, negative_multiplier;
    uint32_t lut, clamp_max, context, reserved0, reserved1;
} har_task;
_Static_assert(sizeof(har_task)==64, "task descriptor size");
_Static_assert(offsetof(har_task, fc_multiplier)==28, "task coefficient offset");
_Static_assert(offsetof(har_task, context)==52, "task context offset");
enum { HAR_TASK_VERSION=1, HAR_TASK_FC=1, HAR_TASK_ACTIVATION=2 };
enum { HAR_ACT_NONE, HAR_ACT_RELU, HAR_ACT_RELU6, HAR_ACT_LEAKY_RELU,
       HAR_ACT_SIGMOID, HAR_ACT_TANH };
enum { HAR_TASK_INIT=1u<<16, HAR_TASK_LAST_K=1u<<17,
       HAR_TASK_INPUT_INTERNAL=1u<<18, HAR_TASK_KEEP=1u<<19,
       HAR_TASK_END=1u<<20, HAR_TASK_LUT_CACHE=1u<<21 };
enum { HAR_TASK_DONE=1, HAR_TASK_BUSY=2, HAR_TASK_FAILED=4,
       HAR_TASK_OUTPUT_VALID=8, HAR_TASK_REJECTED=16 };
enum { HAR_TASK_OK, HAR_TASK_EBUSY, HAR_TASK_EALIGN, HAR_TASK_ERANGE,
       HAR_TASK_EDESCRIPTOR, HAR_TASK_ECONTEXT, HAR_TASK_EDMA,
       HAR_TASK_EVALUE, HAR_TASK_EUNSUPPORTED };
static inline volatile uint32_t *har_task_reg(unsigned offset) {
    return (volatile uint32_t *)(uintptr_t)(0x70001600u+offset);
}
static inline void har_task_fence(void) {
#if defined(__riscv)
    __asm__ volatile ("fence iorw,iorw" ::: "memory");
#else
    __asm__ volatile ("" ::: "memory");
#endif
}
/* Negative return: no segment was started. Completion is asynchronous. */
static inline int har_task_start(uint32_t table, unsigned count) {
    if (*har_task_reg(4)&HAR_TASK_BUSY) return -HAR_TASK_EBUSY;
    if (table&63u) return -HAR_TASK_EALIGN;
    if (!count || count>128) return -HAR_TASK_EVALUE;
    if (table<0x80000000u || table>0x80002000u-count*64u) return -HAR_TASK_ERANGE;
    if ((*har_task_reg(0x10)>>24)!=HAR_TASK_VERSION) return -HAR_TASK_EUNSUPPORTED;
    *har_task_reg(0)=2; /* clear previous sticky completion/rejection */
    *har_task_reg(8)=table; *har_task_reg(12)=count;
    har_task_fence(); *har_task_reg(0)=1;
    return 0;
}
/* 0 while busy, 1 for valid completed output, negative for a terminal error.
 * A software timeout cannot cancel AXI. Reset before reusing its memory. */
static inline int har_task_poll(void) {
    uint32_t s=*har_task_reg(4);
    if (s&HAR_TASK_BUSY) return 0;
    if (s&HAR_TASK_FAILED) return -(int)*har_task_reg(0x18);
    if ((s&(HAR_TASK_DONE|HAR_TASK_OUTPUT_VALID))==
        (HAR_TASK_DONE|HAR_TASK_OUTPUT_VALID)) { har_task_fence(); return 1; }
    return 0;
}
#endif
