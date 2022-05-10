/*
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
 */

#ifndef CDR_KEY_VM_H
#define CDR_KEY_VM_H

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

typedef enum
{
    CdrKeyVMOpDone,
    CdrKeyVMOpStreamStatic,
    CdrKeyVMOpStream2ByteSize,
    CdrKeyVMOpStream4ByteSize,
    CdrKeyVMOpByteSwap,
    CdrKeyVMOpRepeatStatic,
    CdrKeyVMOpRepeat2ByteSize,
    CdrKeyVMOpRepeat4ByteSize,
    CdrKeyVMOpEndRepeat,
    CdrKeyVMOpUnion1Byte,
    CdrKeyVMOpUnion2Byte,
    CdrKeyVMOpUnion4Byte,
    CdrKeyVMOpUnion8Byte,
    CdrKeyVMOpJump,
    CdrKeyVMOpOptional,
    CdrKeyVMOpMemberSelect,
    CdrKeyVmOpMemberSelectEnd,
    CdrKeyVMOpStructHeader,
    CdrKeyVMOpAppendableHeader,
    CdrKeyVMOpAppendableJumpToEnd
}
cdr_key_vm_op_type;

typedef struct cdr_key_vm_op_s
{
    cdr_key_vm_op_type type;
    bool skip;
    uint8_t align;
    uint32_t size;
    uint64_t value;
}
cdr_key_vm_op;


typedef struct cdr_key_vm_s
{
    size_t initial_alloc_size;
    bool final_size_is_static;
    cdr_key_vm_op* instructions;
}
cdr_key_vm;

typedef struct cdr_key_vm_runner_s
{
    cdr_key_vm* my_vm;
    uint8_t* header;
    uint8_t* workspace;
    size_t workspace_size;
}
cdr_key_vm_runner;

cdr_key_vm_runner* cdr_key_vm_create_runner(cdr_key_vm* vm);
size_t cdr_key_vm_run(cdr_key_vm_runner* runner, const uint8_t* cdr_sample, const size_t cdr_sample_size);

#endif // CDR_KEY_VM_H
