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

#include "cdrkeyvm.h"
#include "dds/ddsc/dds_public_alloc.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <inttypes.h>

#define _MIN(x, y) (((x) < (y)) ? (x) : (y))

static inline size_t ALIGN(size_t x, size_t val)
{
    return ((x + (val - 1)) & ~(val - 1));
}

static inline uint32_t decode_4byte_at(const uint8_t* stream, bool stream_little_endian)
{
    return stream_little_endian ?
        ((uint32_t) *(stream)) | ((uint32_t) *(stream + 1) << 8) |
        ((uint32_t) *(stream + 2) << 16) | ((uint32_t) *(stream + 3) << 24)
        :
        ((uint32_t) *(stream + 3)) | ((uint32_t) *(stream + 2) << 8) |
        ((uint32_t) *(stream + 1) << 16) | ((uint32_t) *(stream) << 24);
}

static inline size_t size_from_member_header(const uint8_t* stream, uint32_t member_header, bool stream_little_endian) {
    uint8_t LC = (uint8_t) ((member_header >> 28) & 0x7);
    switch(LC) {
        case 0:
            return 1;
        case 1:
            return 2;
        case 2:
            return 4;
        case 3:
            return 8;
        case 4:
        case 5:
            return 4 + decode_4byte_at(stream + 4, stream_little_endian);
        case 6:
            return 4 + decode_4byte_at(stream + 4, stream_little_endian) * 4;
        case 7:
            return 4 + decode_4byte_at(stream + 4, stream_little_endian) * 8;
        default:
            break;
    }
    // By decode of LC with (& 0x7) it is impossible to get here
    abort();
}

cdr_key_vm_runner* cdr_key_vm_create_runner(cdr_key_vm* vm)
{
    if (vm == NULL) return NULL;
    cdr_key_vm_runner* runner = (cdr_key_vm_runner*) dds_alloc(sizeof(struct cdr_key_vm_runner_s));
    if (runner == NULL) return NULL;
    size_t alloc_size = vm->initial_alloc_size < 20 ? 20 : (vm->initial_alloc_size + 4);
    runner->header = dds_alloc(alloc_size);
    memset(runner->header, 0, alloc_size);
    if (runner->header == NULL) {
        dds_free(runner);
        return NULL;
    }
    runner->workspace = runner->header + 4;
    runner->workspace_size = alloc_size - 4;
    runner->my_vm = vm;
    return runner;
}

static void make_space_for(cdr_key_vm_runner* runner, size_t size) {
    // If you misconfigure things the following will wreak havoc
    if (runner->my_vm->final_size_is_static) return;

    if (runner->workspace_size < size) {
        size = ALIGN(size, 4);
        runner->header = (uint8_t*) dds_realloc(runner->header, size + 4);
        runner->workspace = runner->header + 4;
        memset(runner->workspace + runner->workspace_size, 0, size - runner->workspace_size);
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
    size_t repeat_stack[40];  /// max recursion depth 20 == 20 nested structs
    size_t member_seek_stack[40];
    size_t repeat_index = 0;
    size_t member_seek_index = 0;
    bool stream_little_endian = (*(cdr_sample_in + 1) & 1) > 0;

    // Look at everything _but_ the Little Endian/Big endian switch
    uint32_t stream_max_alignment = (*(cdr_sample_in + 1) & 0x0FE) > 0 ? 4u : 8u;

    // Work relative from cdr-header
    const uint8_t* cdr_sample = cdr_sample_in + 4;
    const size_t cdr_sample_size = cdr_sample_size_in - 4;

    memset(runner->workspace, 0, runner->workspace_size);
    memcpy(runner->header, cdr_sample_in, 4);

    while (instruction->type != CdrKeyVMOpDone) {
        //printf("op: %d %d %" PRIu32 " %d %" PRIu64 "\n", instruction->type, instruction->skip, instruction->size, instruction->align, instruction->value);
        //printf("size: %zu, wpos: %zu, spos: %zu\n", size, workspace_pos, sample_pos);

        switch(instruction->type) {
            case CdrKeyVMOpDone:  // Impossible to get here
                assert(0);
            break;

            case CdrKeyVMOpStreamStatic:
                sample_pos = ALIGN(sample_pos, _MIN(stream_max_alignment, instruction->align));

                if (instruction->skip) {
                    copy = false;
                    size = instruction->size;
                    sample_pos += size;
                }
                else {
                    copy = true;
                    workspace_pos = ALIGN(workspace_pos, _MIN(stream_max_alignment, instruction->align));
                    size = instruction->size;
                    make_space_for(runner, workspace_pos + size);
                }
                instruction++;
            break;

            case CdrKeyVMOpStream2ByteSize:
                sample_pos = ALIGN(sample_pos, 2);

                if (sample_pos + 2 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                if (instruction->skip) {
                    copy = false;

                    size = stream_little_endian ?
                        ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) :
                        ((size_t)*(cdr_sample + sample_pos) << 8) | ((size_t)*(cdr_sample + sample_pos + 1));
                    sample_pos += 2;
                    if (size > 0) {
                        sample_pos = ALIGN(sample_pos, _MIN(stream_max_alignment, instruction->align));
                        size *= instruction->size;
                        sample_pos += size;
                    } else {
                        copy = false;
                    }
                }
                else {
                    copy = true;
                    workspace_pos = ALIGN(workspace_pos, 2);

                    size = stream_little_endian ?
                        ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) :
                        ((size_t)*(cdr_sample + sample_pos) << 8) | ((size_t)*(cdr_sample + sample_pos + 1));

                    make_space_for(runner, workspace_pos + 2);
                    *(runner->workspace + workspace_pos++) = (uint8_t) ((size >> 8) & 0xFF);
                    *(runner->workspace + workspace_pos++) = (uint8_t) (size & 0xFF);
                    sample_pos += 2;
                    size *= instruction->size;

                    if (size > 0) {
                        sample_pos = ALIGN(sample_pos, _MIN(stream_max_alignment, instruction->align));
                        workspace_pos = ALIGN(workspace_pos, _MIN(stream_max_alignment, instruction->align));
                        make_space_for(runner, workspace_pos + size);
                    } else {
                        copy = false;
                    }
                }
                instruction++;
            break;

            case CdrKeyVMOpStream4ByteSize:
                sample_pos = ALIGN(sample_pos, 4);

                if (sample_pos + 4 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                if (instruction->skip) {
                    copy = false;
                    size = stream_little_endian ?
                        ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) |
                        ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) :
                        ((size_t)*(cdr_sample + sample_pos + 3)) | ((size_t)*(cdr_sample + sample_pos + 2) << 8) |
                        ((size_t)*(cdr_sample + sample_pos + 1) << 16) | ((size_t)*(cdr_sample + sample_pos) << 24);
                    sample_pos += 4;

                    if (size > 0) {
                        sample_pos = ALIGN(sample_pos, _MIN(stream_max_alignment, instruction->align));
                        size *= instruction->size;
                        sample_pos += size;
                    }
                }
                else {
                    copy = true;
                    sample_pos = ALIGN(sample_pos, 4);
                    workspace_pos = ALIGN(workspace_pos, 4);
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
                        sample_pos = ALIGN(sample_pos, _MIN(stream_max_alignment, instruction->align));
                        workspace_pos = ALIGN(workspace_pos, _MIN(stream_max_alignment, instruction->align));
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
                            for (size_t i = size; i > 0; i -= 2) {
                                uint8_t tmp = *(runner->workspace + workspace_pos - i);
                                *(runner->workspace + workspace_pos - i) = *(runner->workspace + workspace_pos - i + 1);
                                *(runner->workspace + workspace_pos - i + 1) = tmp;
                            }
                        break;
                        case 4:
                            for (size_t i = size; i > 0; i -= 4) {
                                uint8_t tmp = *(runner->workspace + workspace_pos - i);
                                *(runner->workspace + workspace_pos - i) = *(runner->workspace + workspace_pos - i + 3);
                                *(runner->workspace + workspace_pos - i + 3) = tmp;
                                tmp = *(runner->workspace + workspace_pos - i + 1);
                                *(runner->workspace + workspace_pos - i + 1) = *(runner->workspace + workspace_pos - i + 2);
                                *(runner->workspace + workspace_pos - i + 2) = tmp;
                            }
                        break;
                        case 8:
                            for (size_t i = size; i > 0; i -= 8) {
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
                    return 0;
                }

                repeat_stack[repeat_index++] = instruction->size;
                instruction++;
            break;

            case CdrKeyVMOpRepeat2ByteSize:
                copy = false;

                if (repeat_index == 20) {
                    // Stack overflow!
                    return 0;
                }

                if (sample_pos + 2 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                sample_pos = ALIGN(sample_pos, 2);
                size = stream_little_endian ?
                    ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) :
                    ((size_t)*(cdr_sample + sample_pos) << 8) | ((size_t)*(cdr_sample + sample_pos + 1));

                sample_pos += 2;

                if (!instruction->skip) {
                    workspace_pos = ALIGN(workspace_pos, 2);
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
                    return 0;
                }

                if (sample_pos + 4 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                sample_pos = ALIGN(sample_pos, 4);
                size = stream_little_endian ?
                    ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) |
                    ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) :
                    ((size_t)*(cdr_sample + sample_pos + 3)) | ((size_t)*(cdr_sample + sample_pos + 2) << 8) |
                    ((size_t)*(cdr_sample + sample_pos + 1) << 16) | ((size_t)*(cdr_sample + sample_pos) << 24);

                sample_pos += 4;

                if (!instruction->skip) {
                    workspace_pos = ALIGN(workspace_pos, 4);
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

                if (sample_pos + 1 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

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
                sample_pos = ALIGN(sample_pos, 2);

                if (sample_pos + 2 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                value = stream_little_endian ?
                    ((uint64_t)*(cdr_sample + sample_pos)) | ((uint64_t)*(cdr_sample + sample_pos + 1) << 8) :
                    ((uint64_t)*(cdr_sample + sample_pos) << 8) | ((uint64_t)*(cdr_sample + sample_pos + 1));

                if (instruction->value == value) {
                    if (!instruction->skip) {
                        workspace_pos = ALIGN(workspace_pos, 2);
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
                sample_pos = ALIGN(sample_pos, 4);

                if (sample_pos + 4 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                value = stream_little_endian ?
                    ((size_t)*(cdr_sample + sample_pos)) | ((size_t)*(cdr_sample + sample_pos + 1) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 2) << 16) | ((size_t)*(cdr_sample + sample_pos + 3) << 24) :
                    ((size_t)*(cdr_sample + sample_pos + 3)) | ((size_t)*(cdr_sample + sample_pos + 2) << 8) | 
                    ((size_t)*(cdr_sample + sample_pos + 1) << 16) | ((size_t)*(cdr_sample + sample_pos) << 24);

                if (instruction->value == value) {
                    if (!instruction->skip) {
                        workspace_pos = ALIGN(workspace_pos, 4);
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
                sample_pos = ALIGN(sample_pos, _MIN(8, stream_max_alignment));

                if (sample_pos + 8 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

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
                        workspace_pos = ALIGN(workspace_pos, _MIN(8, stream_max_alignment));
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

            case CdrKeyVMOpOptional:
                copy = false;

                if (sample_pos + 1 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                if ((bool) *(cdr_sample + sample_pos++)) {
                    instruction++;
                } else {
                    instruction += instruction->size;
                }
            break;

            case CdrKeyVMOpMemberSelect: {
                copy = false;
                sample_pos = ALIGN(sample_pos, 4);

                if (sample_pos + 4 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                // We will seek through a encoded struct
                // sample_pos should be on the struct header
                if (member_seek_index == 40) {
                    return 0;
                }
                member_seek_stack[member_seek_index++] = sample_pos;

                uint32_t member_id_to_find = (uint32_t) (instruction->value & 0x0fffffff);
                uint32_t struct_size = decode_4byte_at(cdr_sample + sample_pos, stream_little_endian);
                sample_pos += 4;
                size_t end_of_struct = sample_pos + struct_size;
                uint32_t member_header = 0;
                bool found = false;

                while (sample_pos < end_of_struct) {
                    sample_pos = ALIGN(sample_pos, 4);

                    if (sample_pos + 4 > cdr_sample_size) {
                        // out-of-bounds
                        return 0;
                    }

                    member_header = decode_4byte_at(cdr_sample + sample_pos, stream_little_endian);
                    if ((member_header & 0x0fffffff) == member_id_to_find) {
                        found = true;
                        break;
                    }
                    sample_pos += 4 + size_from_member_header(cdr_sample + sample_pos, member_header, stream_little_endian);
                }

                if (!found) {
                    // key data was not included in struct, error&quit
                    return 0;
                }

                uint8_t LC = (uint8_t) ((member_header >> 28) & 0x7);
                if (LC == 4) {
                    sample_pos += 8;
                } else {
                    sample_pos += 4;
                }
                instruction++;
            }
            break;

            case CdrKeyVmOpMemberSelectEnd:
                copy = false;
                member_seek_index--;
                sample_pos = member_seek_stack[member_seek_index];
                instruction++;
            break;

            case CdrKeyVMOpStructHeader:
                copy = false;
                sample_pos = ALIGN(sample_pos, 4);

                if (sample_pos + 4 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }

                sample_pos += 4 + decode_4byte_at(cdr_sample + sample_pos, stream_little_endian);
                instruction++;
            break;

            case CdrKeyVMOpAppendableHeader:
                if (member_seek_index == 40) return 0;
                copy = false;
                sample_pos = ALIGN(sample_pos, 4);

                if (sample_pos + 4 > cdr_sample_size) {
                    // out-of-bounds
                    return 0;
                }
                member_seek_stack[member_seek_index++] = sample_pos + 4 + decode_4byte_at(cdr_sample + sample_pos, stream_little_endian);
                instruction++;
                sample_pos += 4;
            break;

            case CdrKeyVMOpAppendableJumpToEnd:
                if (member_seek_index == 0) return 0;
                copy = false;
                sample_pos = member_seek_stack[--member_seek_index];
                instruction++;
            break;

        }

        if (copy) {
            if (sample_pos + size > cdr_sample_size) {
                // out-of-bounds
                return 0;
            }

            memcpy(runner->workspace + workspace_pos, cdr_sample + sample_pos, size);
            workspace_pos += size;
            sample_pos += size;
        }
    }

    return workspace_pos + 4;
}
