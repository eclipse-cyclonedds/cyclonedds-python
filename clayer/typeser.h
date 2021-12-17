#ifndef TYPESER_H
#define TYPESER_H

#include "dds/dds.h"
#include "dds/ddsi/ddsi_cdrstream.h"

void ddspy_typeid_ser (dds_ostream_t*, dds_typeid_t *);
void ddspy_typeid_deser (dds_istream_t*, dds_typeid_t **);
void ddspy_typeobj_ser (dds_ostream_t*, dds_typeobj_t *);
void ddspy_typeobj_deser (dds_istream_t*, dds_typeobj_t **);

#endif // TYPESER_H