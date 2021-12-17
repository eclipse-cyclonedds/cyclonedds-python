/*
 * Copyright(c) 2006 to 2018 ADLINK Technology Limited and others
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

#include "dds/ddsi/ddsi_cdrstream.h"
#include "dds/ddsi/ddsi_serdata_default.h"
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

static void tohex(unsigned char * in, size_t insz, char * out, size_t outsz)
{
    const char * hex = "0123456789ABCDEF";
    size_t loop = (2 * insz + 1 > outsz) ? (outsz - 1) / 2 : insz;

    for(size_t i = 0; i < loop; ++i) {
        out[i*2] = hex[(in[i]>>4) & 0xF];
        out[i*2+1] = hex[in[i] & 0xF];
    }
    out[loop*2] = '\0';
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
    unsigned long num_samps = 0;
    unsigned long seqq = 0;
    char* hex_buff = NULL;
    size_t hex_buff_size = 0;

    if(argc < 3) {
        printf("Supply republishing type and sample amount.");
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
        return 0;
    }

    num_samps = strtoul(argv[2], NULL, 10);
    if (num_samps == 0 || num_samps > 200000000) return 1;

    participant = dds_create_participant(0, NULL, NULL);
    if (participant < 0) return 1;

    topic = dds_create_topic(participant, descriptor, argv[1], NULL, NULL);
    if (topic < 0) return 1;

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
            struct ddsi_serdata_default* rserdata = (struct ddsi_serdata_default*) samples[0];
            dds_istream_t sampstream;
            dds_ostreamBE_t keystream;
            dds_ostreamBE_init(&keystream, 0, CDR_ENC_VERSION_2);

            dds_istream_from_serdata_default(&sampstream, rserdata);
            dds_stream_extract_keyBE_from_data(&sampstream, &keystream, (const struct ddsi_sertype_default *) rserdata->c.type);

            if (keystream.x.m_index*2+1 > hex_buff_size) {
                hex_buff = realloc(hex_buff, keystream.x.m_index*2+1);
                hex_buff_size = keystream.x.m_index*2+1;
            }

            tohex(keystream.x.m_buffer, keystream.x.m_index, hex_buff, hex_buff_size);

            printf("%s\n", hex_buff);

            seqq++;
        }
        else
        {
            dds_sleepfor(DDS_MSECS(20));
        }
    }

    dds_sleepfor(DDS_MSECS(200));
    dds_delete(participant);

    return EXIT_SUCCESS;
}
