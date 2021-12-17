#ifndef XTYPES_SUB_H
#define XTYPES_SUB_H

#include "dds/dds.h"

struct topic_descriptor_s {
    const char* name;
    const dds_topic_descriptor_t* descriptor;
};
typedef struct topic_descriptor_s topic_descriptor_t;

extern const topic_descriptor_t topic_descriptors[];
extern const unsigned long long topic_descriptors_size;

#endif // XTYPES_SUB_H