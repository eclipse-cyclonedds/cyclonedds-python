/*
 * Copyright(c) 2006 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
 */

#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>

#include "dds/ddsrt/heap.h"
#include "dds/ddsrt/string.h"
#include "dds/cdr/dds_cdrstream.h"
#include "dds/ddsi/ddsi_serdata.h"
#include "dds/ddsi/ddsi_domaingv.h"
#include "dds/ddsi/ddsi_typelib.h"
#include "dds/ddsi/ddsi_typebuilder.h"
#include "dds/ddsc/dds_public_qosdefs.h"

#include "xtypes_sub.h"


#if DDSRT_ENDIAN == DDSRT_LITTLE_ENDIAN
#define NATIVE_ENCODING CDR_LE
#define NATIVE_ENCODING_PL PL_CDR_LE
#elif DDSRT_ENDIAN == DDSRT_BIG_ENDIAN
#define NATIVE_ENCODING CDR_BE
#define NATIVE_ENCODING_PL PL_CDR_BE
#else
#error "DDSRT_ENDIAN neither LITTLE nor BIG"
#endif

static void tohex(const unsigned char * in, size_t insz, char * out, size_t outsz)
{
    const char * hex = "0123456789ABCDEF";
    size_t loop = (2 * insz + 1 > outsz) ? (outsz - 1) / 2 : insz;

    for(size_t i = 0; i < loop; ++i) {
        out[i*2] = hex[(in[i]>>4) & 0xF];
        out[i*2+1] = hex[in[i] & 0xF];
    }
    out[loop*2] = '\0';
}

static void xcdr2_deser(const unsigned char * buf, uint32_t sz, void ** obj, const dds_topic_descriptor_t * desc)
{
    unsigned char * data;
    uint32_t srcoff = 0;
    dds_istream_t is = {.m_buffer = buf, .m_index = 0, .m_size = sz, .m_xcdr_version = DDSI_RTPS_CDR_ENC_VERSION_2};
    *obj = ddsrt_calloc(1, desc->m_size);
    dds_stream_read(&is, (void *)*obj, &dds_cdrstream_default_allocator, desc->m_ops);
}

static bool topic_desc_eq (const dds_topic_descriptor_t * generated_desc, const dds_topic_descriptor_t * desc)
{
    printf("size: %u (%u)\n", generated_desc->m_size, desc->m_size);
    if (desc->m_size != generated_desc->m_size)
        return false;
    printf("align: %u (%u)\n", generated_desc->m_align, desc->m_align);
    if (desc->m_align != generated_desc->m_align)
        return false;
    printf("flagset: %x (%x)\n", generated_desc->m_flagset, desc->m_flagset);
    if (desc->m_flagset != generated_desc->m_flagset)
        return false;
    printf("nkeys: %u (%u)\n", generated_desc->m_nkeys, desc->m_nkeys);
    if (desc->m_nkeys != generated_desc->m_nkeys)
        return false;
    for (uint32_t n = 0; n < desc->m_nkeys; n++)
    {
        printf("key[%u] name: %s (%s)\n", n, generated_desc->m_keys[n].m_name, desc->m_keys[n].m_name);
        if (strcmp(desc->m_keys[n].m_name, generated_desc->m_keys[n].m_name))
            return false;
        printf("  offset: %u (%u)\n", generated_desc->m_keys[n].m_offset, desc->m_keys[n].m_offset);
        if (desc->m_keys[n].m_offset != generated_desc->m_keys[n].m_offset)
            return false;
        printf("  index: %u (%u)\n", generated_desc->m_keys[n].m_idx, desc->m_keys[n].m_idx);
        if (desc->m_keys[n].m_idx != generated_desc->m_keys[n].m_idx)
            return false;
    }
    printf("typename: %s (%s)\n", generated_desc->m_typename, desc->m_typename);
    if (strcmp(desc->m_typename, generated_desc->m_typename))
        return false;
    printf("nops: %u (%u)\n", generated_desc->m_nops, desc->m_nops);
    if (desc->m_nops != generated_desc->m_nops)
        return false;

    uint32_t ops_cnt_gen = dds_stream_countops(generated_desc->m_ops, generated_desc->m_nkeys, generated_desc->m_keys);
    uint32_t ops_cnt = dds_stream_countops(desc->m_ops, desc->m_nkeys, desc->m_keys);
    printf("ops count: %u (%u)\n", ops_cnt_gen, ops_cnt);
    if (ops_cnt_gen != ops_cnt)
        return false;
    for (uint32_t n = 0; n < ops_cnt; n++)
    {
        if (desc->m_ops[n] != generated_desc->m_ops[n])
        {
            printf("incorrect op at index %u: 0x%08x (0x%08x)\n", n, generated_desc->m_ops[n], desc->m_ops[n]);
            return false;
        }
    }

    printf("typeinfo: %u (%u)\n", generated_desc->type_information.sz, desc->type_information.sz);
    ddsi_typeinfo_t *tinfo = ddsi_typeinfo_deser(desc->type_information.data, desc->type_information.sz);
    ddsi_typeinfo_t *gen_tinfo = ddsi_typeinfo_deser(generated_desc->type_information.data, generated_desc->type_information.sz);
    if (!ddsi_typeinfo_equal(tinfo, gen_tinfo, DDSI_TYPE_INCLUDE_DEPS))
    {
        printf("typeinfo different\n");
        return false;
    }
    ddsi_typeinfo_fini(tinfo);
    ddsrt_free(tinfo);
    ddsi_typeinfo_fini(gen_tinfo);
    ddsrt_free(gen_tinfo);

    printf("typemap: %u (%u)\n", generated_desc->type_mapping.sz, desc->type_mapping.sz);
    ddsi_typemap_t *tmap = ddsi_typemap_deser(desc->type_mapping.data, desc->type_mapping.sz);
    ddsi_typemap_t *gen_tmap = ddsi_typemap_deser(generated_desc->type_mapping.data, generated_desc->type_mapping.sz);
    if (!ddsi_typemap_equal(tmap, gen_tmap))
    {
        printf("typemap different\n");
        return false;
    }
    ddsi_typemap_fini(tmap);
    ddsrt_free(tmap);
    ddsi_typemap_fini(gen_tmap);
    ddsrt_free(gen_tmap);
    return true;
}

// republisher topic
int main(int argc, char **argv)
{
    dds_entity_t participant;
    dds_entity_t topic;
    dds_qos_t* qos;
    dds_entity_t reader;
    dds_return_t rc;
    dds_sample_info_t infos[1];
    struct ddsi_serdata *samples[1] = {NULL};
    const dds_topic_descriptor_t *descriptor = NULL;
    struct dds_cdrstream_desc cdrs_desc;
    unsigned long num_samps = 0;
    unsigned long seqq = 0;
    char* hex_buff = NULL;
    size_t hex_buff_size = 0;

    if (argc < 3)
    {
        printf("Supply republishing type and sample amount or test mode, e.g.:\n");
        printf("  %s <typename> 10\n", argv[0]);
        printf("  %s <typename> desc\n", argv[0]);
        printf("  %s <typename> typebuilder\n", argv[0]);
        return 1;
    };

    for (int i = 0; i < topic_descriptors_size; ++i) {
        if (strcmp(topic_descriptors[i].name, argv[1]) == 0) {
            descriptor = topic_descriptors[i].descriptor;
        }
    }
    if (!descriptor) return 1;

    if (strcmp(argv[2], "desc") == 0) {
        /// description mode printout
        hex_buff_size = descriptor->type_information.sz * 2 + 1;
        hex_buff = (char*) realloc(hex_buff, hex_buff_size);
        tohex(descriptor->type_information.data, descriptor->type_information.sz, hex_buff, hex_buff_size);
        printf("%s\n", hex_buff);
        hex_buff_size = descriptor->type_mapping.sz * 2 + 1;
        hex_buff = (char*) realloc(hex_buff, hex_buff_size);
        tohex(descriptor->type_mapping.data, descriptor->type_mapping.sz, hex_buff, hex_buff_size);
        printf("%s\n", hex_buff);
        fflush(stdout);
        return 0;
    }
    else if (strcmp(argv[2], "typebuilder") == 0)
    {
        struct ddsi_type *type;
        participant = dds_create_participant(0, NULL, NULL);
        if (participant < 0)
            return 1;

        topic = dds_create_topic(participant, descriptor, argv[1], NULL, NULL);
        if (topic < 0)
            return 1;

        void *type_info_void;
        xcdr2_deser(descriptor->type_information.data, descriptor->type_information.sz, &type_info_void, &DDS_XTypes_TypeInformation_desc);
        dds_typeinfo_t * const type_info = type_info_void;

        dds_topic_descriptor_t *generated_desc;
        if (dds_create_topic_descriptor(DDS_FIND_SCOPE_LOCAL_DOMAIN, participant, type_info, DDS_SECS(0), &generated_desc))
        {
            printf("failed to create topic descriptor");
            fflush(stdout);
            return 1;
        }

        if (!topic_desc_eq(generated_desc, descriptor))
            return 1;

        dds_entity_t topic_gen = dds_create_topic(participant, generated_desc, "topic_gen", NULL, NULL);
        if (topic_gen < 0)
            return 1;

        dds_delete_topic_descriptor (generated_desc);

        printf("success");
        fflush(stdout);
        return 0;
    }

    num_samps = strtoul(argv[2], NULL, 10);
    if (num_samps == 0 || num_samps > 200000000) return 1;

    participant = dds_create_participant(0, NULL, NULL);
    if (participant < 0) return 1;

    topic = dds_create_topic(participant, descriptor, argv[1], NULL, NULL);
    if (topic < 0) return 1;
    dds_cdrstream_desc_from_topic_desc(&cdrs_desc, descriptor);

    /* Create a reliable Reader. */
    qos = dds_create_qos ();
    dds_qset_reliability (qos, DDS_RELIABILITY_RELIABLE, DDS_SECS (2));
    dds_qset_data_representation(qos, 1, (dds_data_representation_id_t[]) { DDS_DATA_REPRESENTATION_XCDR2 });
    dds_qset_history(qos, DDS_HISTORY_KEEP_LAST, num_samps);
    dds_qset_destination_order(qos, DDS_DESTINATIONORDER_BY_SOURCE_TIMESTAMP);

    reader = dds_create_reader(participant, topic, qos, NULL);
    if (reader < 0) return 1;

    while (seqq < num_samps) {
        rc = dds_readcdr(reader, samples, 1, infos, DDS_NOT_READ_SAMPLE_STATE | DDS_ANY_VIEW_STATE | DDS_ALIVE_INSTANCE_STATE);
        if (rc < 0) return 1;

        if (rc > 0)
        {
            struct ddsi_serdata* rserdata = samples[0];
            dds_ostream_t keystream;
            dds_ostream_init(&keystream, &dds_cdrstream_default_allocator, 0, DDSI_RTPS_CDR_ENC_VERSION_2);

            ddsrt_iovec_t ref = { .iov_len = 0, .iov_base = NULL };
            uint32_t data_sz = ddsi_serdata_size (rserdata) - 4;
            struct ddsi_serdata * const rserdata_ref = ddsi_serdata_to_ser_ref (rserdata, 4, data_sz, &ref);
            assert(ref.iov_len == data_sz);
            assert(ref.iov_base);
            dds_istream_t sampstream = { .m_buffer = ref.iov_base, .m_size = data_sz, .m_index = 0, .m_xcdr_version = DDSI_RTPS_CDR_ENC_VERSION_2 };
            dds_stream_extract_key_from_data(&sampstream, &keystream, &dds_cdrstream_default_allocator, &cdrs_desc);
            ddsi_serdata_to_ser_unref (rserdata_ref, &ref);

            if (keystream.m_index * 2 + 1 > hex_buff_size) {
                hex_buff = realloc(hex_buff, keystream.m_index * 2 + 1);
                hex_buff_size = keystream.m_index * 2 + 1;
            }

            tohex(keystream.m_buffer, keystream.m_index, hex_buff, hex_buff_size);

            printf("0x%s\n", hex_buff);
            fflush(stdout);

            seqq++;
        }
        else
        {
            dds_sleepfor(DDS_MSECS(20));
        }
    }

    dds_sleepfor(DDS_MSECS(200));
    dds_delete(participant);

    dds_cdrstream_desc_fini (&cdrs_desc, &dds_cdrstream_default_allocator);

    return EXIT_SUCCESS;
}
