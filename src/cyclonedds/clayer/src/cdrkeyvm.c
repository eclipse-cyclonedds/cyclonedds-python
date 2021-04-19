/*
 * Copyright(c) 2021 ADLINK Technology Limited and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
 */

#include "cdrkeyvm.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <inttypes.h>

#define ALIGN(X, VAL) X = ((X + VAL - 1) & ~(VAL - 1))


bool endianness_is_little() {
    volatile uint32_t i=0x01234567;
    // return 0 for big endian, 1 for little endian.
    return (*((uint8_t*)(&i))) == 0x67;
}

cdr_key_vm_runner* cdr_key_vm_create_runner(cdr_key_vm* vm)
{
    if (vm == NULL) return NULL;
    cdr_key_vm_runner* runner = (cdr_key_vm_runner*) malloc(sizeof(struct cdr_key_vm_runner_s));
    if (runner == NULL) return NULL;
    size_t alloc_size = vm->initial_alloc_size < 16 ? 16 : vm->initial_alloc_size;
    runner->workspace = malloc(alloc_size);
    memset(runner->workspace, 0, alloc_size);
    if (runner->workspace == NULL) {
        free(runner);
        return NULL;
    }
    runner->workspace_size = alloc_size;
    runner->my_vm = vm;
    return runner;
}

void make_space_for(cdr_key_vm_runner* runner, size_t size) {
    // If you misconfigure things the following will wreak havoc
    if (runner->my_vm->final_size_is_static) return;

    if (runner->workspace_size < size) {
        uint8_t* new_workspace = (uint8_t*) malloc(size);
        memset(new_workspace, 0, size);
        memcpy(new_workspace, runner->workspace, runner->workspace_size);
        free(runner->workspace);
        runner->workspace = new_workspace;
        runner->workspace_size = size;
    }
}

size_t cdr_key_vm_run(cdr_key_vm_runner* runner, const uint8_t* cdr_sample_in, const size_t cdr_sample_size_in)
{
    cdr_key_vm_op* instruction = runner->my_vm->instructions;
    bool copy = false;
    size_t size = 0;
    uint64_t value = 0;
    size_t sample_pos = 0;
    size_t workspace_pos = 0;
    size_t repeat_stack[20];  /// max recursion depth 20 == 20 nested structs
    size_t repeat_index = 0;
    bool stream_little_endian = (*(cdr_sample_in + 1) & 1) > 0;

    // Work relative from post-dds-header
    const uint8_t* cdr_sample = cdr_sample_in + 4;
    const size_t cdr_sample_size = cdr_sample_size_in - 4;

    memset(runner->workspace, 0, runner->workspace_size);

    while (instruction->type != CdrKeyVMOpDone) {
        //printf("op: %d %d %" PRIu32 " %d %" PRIu64 "\n", instruction->type, instruction->skip, instruction->size, instruction->align, instruction->value);
        //printf("size: %zu, wpos: %zu, spos: %zu\n", size, workspace_pos, sample_pos);

        switch(instruction->type) {
            case CdrKeyVMOpDone:  // Impossible to get here
                assert(0);
            break;

            case CdrKeyVMOpStreamStatic:
                ALIGN(sample_pos, instruction->align);

                if (instruction->skip) {
                    copy = false;
                    sample_pos = ALIGN(sample_pos, instruction->align);
                    size = instruction->size;
                    sample_pos += size;
                }
                else {
                    copy = true;
                    ALIGN(workspace_pos, instruction->align);
                    size = instruction->size;
                    make_space_for(runner, workspace_pos + size);
                }
                instruction++;
            break;

            case CdrKeyVMOpStream2ByteSize:
                ALIGN(sample_pos, 2);

                if (instruction->skip) {
                    copy = false;
                    size = stream_little_endian ? 
                        ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) :
                        ((size_t)*(cdr_sample + sample_pos) << 8) | ((size_t)*(cdr_sample + sample_pos + 1));
                    sample_pos += 2;
                    if (size > 0) {
                        ALIGN(sample_pos, instruction->align);
                        size *= instruction->size;
                        sample_pos += size;
                    } else {
                        copy = false;
                    }
                }
                else {
                    copy = true;
                    ALIGN(workspace_pos, 2);
                    size = stream_little_endian ? 
                        ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) :
                        ((size_t)*(cdr_sample + sample_pos) << 8) | ((size_t)*(cdr_sample + sample_pos + 1));
                    
                    make_space_for(runner, workspace_pos + 2);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 8) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) (size & 0xFF);
                    sample_pos += 2;
                    size *= instruction->size;
                    if (size > 0) {
                        ALIGN(sample_pos, instruction->align);
                        ALIGN(workspace_pos, instruction->align);
                        make_space_for(runner, workspace_pos + size);
                    } else {
                        copy = false;
                    }
                }
                instruction++;
            break;

            case CdrKeyVMOpStream4ByteSize:
                ALIGN(sample_pos, 4);

                if (instruction->skip) {
                    copy = false;
                    size = stream_little_endian ? 
                        ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) | 
                        ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) :
                        ((size_t)*(cdr_sample + sample_pos + 3)) | ((size_t)*(cdr_sample + sample_pos + 2) << 8) | 
                        ((size_t)*(cdr_sample + sample_pos + 1) << 16) | ((size_t)*(cdr_sample + sample_pos) << 24);
                    sample_pos += 4;
                    ALIGN(sample_pos, instruction->align);
                    size *= instruction->size;
                    sample_pos += size;
                }
                else {
                    copy = true;
                    ALIGN(sample_pos, 4);
                    ALIGN(workspace_pos, 4);
                    size = stream_little_endian ? 
                        ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) | 
                        ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) :
                        ((size_t)*(cdr_sample + sample_pos + 3)) | ((size_t)*(cdr_sample + sample_pos + 2) << 8) | 
                        ((size_t)*(cdr_sample + sample_pos + 1) << 16) | ((size_t)*(cdr_sample + sample_pos) << 24);

                    make_space_for(runner, workspace_pos + 4);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 24) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 16) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 8) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) (size & 0xFF);
                    sample_pos += 4;
                    size *= instruction->size;
                    
                    if (size > 0) {
                        ALIGN(sample_pos, instruction->align);
                        ALIGN(workspace_pos, instruction->align);
                        make_space_for(runner, workspace_pos + size);
                    } else {
                        copy = false;
                    }
                }
                instruction++;
            break;

            case CdrKeyVMOpByteSwap:
                copy = false;
                if (stream_little_endian) {
                    switch(instruction->align) {
                        default: assert(0); break;
                        case 2:
                            for (int i = size; i > 0; i -= 2) {
                                uint8_t tmp = *(runner->workspace + workspace_pos - i);
                                *(runner->workspace + workspace_pos - i) = *(runner->workspace + workspace_pos - i + 1);
                                *(runner->workspace + workspace_pos - i + 1) = tmp;
                            }
                        break;
                        case 4:
                            for (int i = size; i > 0; i -= 4) {
                                uint8_t tmp = *(runner->workspace + workspace_pos - i);
                                *(runner->workspace + workspace_pos - i) = *(runner->workspace + workspace_pos - i + 3);
                                *(runner->workspace + workspace_pos - i + 3) = tmp;
                                tmp = *(runner->workspace + workspace_pos - i + 1);
                                *(runner->workspace + workspace_pos - i + 1) = *(runner->workspace + workspace_pos - i + 2);
                                *(runner->workspace + workspace_pos - i + 2) = tmp;
                            }
                        break;
                        case 8:
                            for (int i = size; i > 0; i -= 8) {
                                uint8_t tmp = *(runner->workspace + workspace_pos - i);
                                *(runner->workspace + workspace_pos - i) = *(runner->workspace + workspace_pos - i + 7);
                                *(runner->workspace + workspace_pos - i + 7) = tmp;
                                tmp = *(runner->workspace + workspace_pos - i + 1);
                                *(runner->workspace + workspace_pos - i + 1) = *(runner->workspace + workspace_pos - i + 6);
                                *(runner->workspace + workspace_pos - i + 6) = tmp;
                                tmp = *(runner->workspace + workspace_pos - i + 2);
                                *(runner->workspace + workspace_pos - i + 2) = *(runner->workspace + workspace_pos - i + 5);
                                *(runner->workspace + workspace_pos - i + 5) = tmp;
                                tmp = *(runner->workspace + workspace_pos - i + 3);
                                *(runner->workspace + workspace_pos - i + 3) = *(runner->workspace + workspace_pos - i + 4);
                                *(runner->workspace + workspace_pos - i + 4) = tmp;
                            }
                        break;
                    }
                }
                instruction++;
            break;

            case CdrKeyVMOpRepeatStatic:
                copy = false;
                if (repeat_index == 20 || instruction->size == 0) {
                    // Stack overflow or invalid
                    assert(0);
                }
                repeat_stack[repeat_index++] = instruction->size;
                instruction++;
            break;

            case CdrKeyVMOpRepeat2ByteSize:
                copy = false;
                if (repeat_index == 20) {
                    // Stack overflow!
                    assert(0);
                }
                ALIGN(sample_pos, 2);
                size = stream_little_endian ? 
                    ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) :
                    ((size_t)*(cdr_sample + sample_pos) << 8) | ((size_t)*(cdr_sample + sample_pos + 1));
                
                sample_pos += 2;
                
                if (!instruction->skip) {
                    ALIGN(workspace_pos, 2);
                    make_space_for(runner, workspace_pos + 2);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 8) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) (size & 0xFF);
                }
                
                if (size != 0) {
                    repeat_stack[repeat_index++] = size;
                    instruction++;
                }
                else {
                    instruction += instruction->value;
                }
            break;

            case CdrKeyVMOpRepeat4ByteSize:
                copy = false;
                if (repeat_index == 20) {
                    // Stack overflow!
                    assert(0);
                }
                ALIGN(sample_pos, 4);
                size = stream_little_endian ? 
                    ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) :
                    ((size_t)*(cdr_sample + sample_pos + 3)) | ((size_t)*(cdr_sample + sample_pos + 2) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 1) << 16) | ((size_t)*(cdr_sample + sample_pos) << 24);
                
                sample_pos += 4;

                if (!instruction->skip) {
                    ALIGN(workspace_pos, 4);
                    make_space_for(runner, workspace_pos + 4);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 24) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 16) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 8) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) (size & 0xFF);
                }

                if (size != 0) {
                    repeat_stack[repeat_index++] = size;
                    instruction++;
                }
                else {
                    instruction += instruction->value;
                }
            break;

            case CdrKeyVMOpEndRepeat:
                copy = false;
                repeat_stack[repeat_index-1]--;
                if (repeat_stack[repeat_index-1] != 0) {
                    instruction -= instruction->size;
                } else {
                    repeat_index--;
                    instruction++;
                }
            break;

            case CdrKeyVMOpUnion1Byte:
                copy = false;
                value = ((uint64_t)*(cdr_sample + sample_pos) & 0xFF);

                //printf("%" PRIu64 " %" PRIu64 "\n", value, instruction->value);
                if (value == instruction->value)  {
                    if (!instruction->skip) {
                        make_space_for(runner, workspace_pos + 1);
                        *(runner->workspace + workspace_pos++) = (uint8_t) value;
                    }
                    sample_pos++;
                    instruction++;
                } else {
                    instruction += instruction->size;
                }
            break;

            case CdrKeyVMOpUnion2Byte:
                copy = false;
                ALIGN(sample_pos, 2);
                value = stream_little_endian ? 
                    ((uint64_t)*(cdr_sample + sample_pos)) | ((uint64_t)*(cdr_sample + sample_pos + 1) << 8) :
                    ((uint64_t)*(cdr_sample + sample_pos) << 8) | ((uint64_t)*(cdr_sample + sample_pos + 1));

                if (instruction->value == value) {
                    if (!instruction->skip) {
                        ALIGN(workspace_pos, 2);
                        make_space_for(runner, workspace_pos + 2);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 8) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) (value & 0xFF);
                    }
                    sample_pos += 2;
                    instruction++;
                }
                else {
                    instruction += instruction->size;
                }
            break;

            case CdrKeyVMOpUnion4Byte:
                copy = false;
                ALIGN(sample_pos, 4);
                value = stream_little_endian ? 
                    ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) :
                    ((size_t)*(cdr_sample + sample_pos + 3)) | ((size_t)*(cdr_sample + sample_pos + 2) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 1) << 16) | ((size_t)*(cdr_sample + sample_pos) << 24);
                
                if (instruction->value == value) {
                    if (!instruction->skip) {
                        ALIGN(workspace_pos, 4);
                        make_space_for(runner, workspace_pos + 4);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 24) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 16) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 8) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) (value & 0xFF);
                    }
                    sample_pos += 4;
                    instruction++;
                }
                else {
                    instruction += instruction->size;
                }
            break;

            case CdrKeyVMOpUnion8Byte:
                copy = false;
                ALIGN(sample_pos, 8);
                value = stream_little_endian ? 
                    ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) |
                    ((size_t)*(cdr_sample + sample_pos + 4) << 32) | ((size_t)*(cdr_sample + sample_pos + 5) << 40) |
                    ((size_t)*(cdr_sample + sample_pos + 6) << 48) | ((size_t)*(cdr_sample + sample_pos + 7) << 56) :
                    ((size_t)*(cdr_sample + sample_pos + 7)) | ((size_t)*(cdr_sample + sample_pos + 6) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 5) << 16) | ((size_t)*(cdr_sample + sample_pos + 4) << 24) |
                    ((size_t)*(cdr_sample + sample_pos + 3) << 32) | ((size_t)*(cdr_sample + sample_pos + 2) << 40) |
                    ((size_t)*(cdr_sample + sample_pos + 1) << 48) | ((size_t)*(cdr_sample + sample_pos) << 56);
                
                if (instruction->value == value) {
                    if (!instruction->skip) {
                        ALIGN(workspace_pos, 8);
                        make_space_for(runner, workspace_pos + 8);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 56) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 48) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 40) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 32) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 24) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 16) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) ((value >> 8) & 0xFF);
                        *(runner->workspace + workspace_pos++) = (uint8_t) (value & 0xFF);
                    }
                    sample_pos += 8;
                    instruction++;
                }
                else {
                    instruction += instruction->size;
                }
            break;

            case CdrKeyVMOpJump:
                copy = false;
                instruction += instruction->size;
            break;
        }

        if (copy) {
            memcpy(runner->workspace + workspace_pos, cdr_sample + sample_pos, size);
            workspace_pos += size;
            sample_pos += size;
        }
    }

    workspace_pos = workspace_pos > 16 ? workspace_pos : 16;
    return workspace_pos;
}
