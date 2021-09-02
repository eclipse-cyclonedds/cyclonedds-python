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

#include "dds/dds.h"
#include "dds/ddsi/ddsi_cdrstream.h"
#include "dds/ddsi/ddsi_serdata_default.h"
#include "py_c_compat.h"
#include "fuzzy_type_support.h"
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>


#if DDSRT_ENDIAN == DDSRT_LITTLE_ENDIAN
#define NATIVE_ENCODING CDR_LE
#define NATIVE_ENCODING_PL PL_CDR_LE
#elif DDSRT_ENDIAN == DDSRT_BIG_ENDIAN
#define NATIVE_ENCODING CDR_BE
#define NATIVE_ENCODING_PL PL_CDR_BE
#else
#error "DDSRT_ENDIAN neither LITTLE nor BIG"
#endif


// republisher topic
int main(int argc, char **argv)
{
    dds_entity_t participant;
    dds_entity_t topic;
    dds_entity_t reader;
    dds_return_t rc;
    dds_entity_t repltopic;
    dds_entity_t writer;
    py_c_compat_replybytes msg;
    dds_sample_info_t infos[1];
    struct ddsi_serdata *samples[1] = {NULL};
    const dds_topic_descriptor_t *descriptor = NULL;
    dds_qos_t* qos;
    unsigned long num_samps = 0;
    unsigned long seqq = 0;

    if(argc < 3) {
        printf("Supply republishing type and sample amount.");
        return 1;
    };

    for (int i = 0; i < fuzzy_descriptors_size; ++i) {
        if (strcmp(fuzzy_descriptors[i].name, argv[1]) == 0) {
            descriptor = fuzzy_descriptors[i].descriptor;
        }
    }
    if (!descriptor) return 1;

    qos = dds_create_qos();
    dds_qset_reliability(qos, DDS_RELIABILITY_RELIABLE, DDS_SECS(10));
    dds_qset_durability(qos, DDS_DURABILITY_TRANSIENT_LOCAL);
    dds_qset_history(qos, DDS_HISTORY_KEEP_ALL, -1);
    dds_qset_destination_order(qos, DDS_DESTINATIONORDER_BY_SOURCE_TIMESTAMP);

    num_samps = strtoul(argv[2], NULL, 10);
    if (num_samps == 0 || num_samps > 200000000) return 1;

    participant = dds_create_participant(0, NULL, NULL);
    if (participant < 0) return 1;

    topic = dds_create_topic(participant, descriptor, argv[1], NULL, NULL);
    if (topic < 0) return 1;

    reader = dds_create_reader(participant, topic, qos, NULL);
    if (reader < 0) return 1;

    repltopic = dds_create_topic(participant, &py_c_compat_replybytes_desc, "replybytes", NULL, NULL);
    if (repltopic < 0) return 1;

    writer = dds_create_writer(participant, repltopic, qos, NULL);
    if (writer < 0) return 1;

    printf("ready\n");

    while (seqq < num_samps) {
        rc = dds_readcdr(reader, samples, 1, infos, DDS_NOT_READ_SAMPLE_STATE | DDS_ANY_VIEW_STATE | DDS_ALIVE_INSTANCE_STATE);
        if (rc < 0) return 1;

        if (rc > 0)
        {
            struct ddsi_serdata_default* rserdata = (struct ddsi_serdata_default*) samples[0];
            dds_istream_t sampstream;
            dds_ostreamBE_t keystream;
            ddsi_keyhash_t keyhash;
            dds_ostreamBE_init(&keystream, 0);

            dds_istream_from_serdata_default(&sampstream, rserdata);
            dds_stream_extract_keyBE_from_data(&sampstream, &keystream, (const struct ddsi_sertype_default *) rserdata->c.type);
            ddsi_serdata_get_keyhash(rserdata, &keyhash, false);

            msg.reply_to = dds_string_dup(argv[1]);
            msg.seq = seqq++;
            memcpy(msg.keyhash, keyhash.value, 16);

            const size_t outs = keystream.x.m_index;
            msg.data._buffer = (uint8_t*) malloc(outs);
            memcpy(msg.data._buffer, keystream.x.m_buffer, outs);
            msg.data._maximum = outs;
            msg.data._length = outs;
            msg.data._release = true;

            if (dds_write(writer, &msg) != DDS_RETCODE_OK)
                return 1;

            dds_ostreamBE_fini(&keystream);
            ddsi_serdata_unref(samples[0]);
            free(msg.data._buffer);
            free(msg.reply_to);
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
