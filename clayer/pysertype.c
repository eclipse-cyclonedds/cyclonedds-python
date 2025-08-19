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
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include "dds/dds.h"
#include "dds/ddsrt/endian.h"
#include "dds/ddsrt/heap.h"
#include "dds/ddsrt/string.h"
#include "dds/ddsrt/mh3.h"
#include "dds/ddsrt/md5.h"
#include "dds/ddsi/ddsi_radmin.h"
#include "dds/ddsi/ddsi_serdata.h"
#include "dds/ddsi/ddsi_sertype.h"
#include "dds/ddsi/ddsi_typelib.h"
#include "dds/ddsi/ddsi_typebuilder.h"
#include "dds/cdr/dds_cdrstream.h"
#include "pysertype.h"

#define HEXDUMP 0

const struct dds_cdrstream_allocator cdrstream_allocator = { dds_alloc, dds_realloc, dds_free };

typedef struct ddsi_serdata ddsi_serdata_t;
typedef struct ddsi_sertype ddsi_sertype_t;

// Python refcount: one ref for each PyObject*.
typedef struct ddspy_sertype {
  ddsi_sertype_t my_c_type;
  PyObject *my_py_type;
  bool keyless;

  bool v1_key_maxsize_bigger_16;
  bool v2_key_maxsize_bigger_16;

  // xtypes
  unsigned char *typeinfo_ser_data;
  uint32_t typeinfo_ser_sz;
  unsigned char *typemap_ser_data;
  uint32_t typemap_ser_sz;
  struct dds_cdrstream_desc cdrstream_desc;
} ddspy_sertype_t;

// Python refcount: one ref for sample.
typedef struct ddspy_serdata {
  ddsi_serdata_t c_data;
  void *data;
  size_t data_size;     // size of the data, including 4 bytes for CDR encapsulation header
  void *key;            // key in native endianness XCDR2, no encapsulation header
  size_t key_size;      // size of the key
  bool is_v2;
} ddspy_serdata_t;

// Python refcount: one ref for sample.
typedef struct ddspy_sample_container {
  void *usample;
  size_t usample_size;
} ddspy_sample_container_t;

typedef struct {
  ddspy_sample_container_t *containers;
  dds_sample_info_t *sample_infos;
  size_t count;
  size_t capacity;
} collector_state_t;

#if 0
static inline ddspy_sertype_t *sertype (ddspy_serdata_t *this)
{
  return (ddspy_sertype_t *) (this->c_data.type);
}
#endif

static inline const ddspy_sertype_t *csertype (const ddspy_serdata_t *this)
{
  return (const ddspy_sertype_t *) (this->c_data.type);
}

static inline ddspy_serdata_t *serdata (ddsi_serdata_t *this)
{
  return (ddspy_serdata_t *) (this);
}

static inline const ddspy_serdata_t *cserdata (const ddsi_serdata_t *this)
{
  return (const ddspy_serdata_t *) (this);
}

static void typeid_ser (dds_ostream_t *os, const dds_typeid_t *type_id)
{
  if (!dds_stream_write (os, &cdrstream_allocator, (char *)type_id, DDS_XTypes_TypeIdentifier_desc.m_ops))
    abort (); // internally generated data, so should never fail
}

#ifdef DDS_HAS_TYPE_DISCOVERY

static void typeid_deser (dds_istream_t *is, dds_typeid_t **type_id)
{
  *type_id = dds_alloc (sizeof (DDS_XTypes_TypeIdentifier));
  dds_stream_read (is, (void *) *type_id, &cdrstream_allocator, DDS_XTypes_TypeIdentifier_desc.m_ops);
}

static void typeobj_ser (dds_ostream_t *os, const dds_typeobj_t *type_obj)
{
  if (!dds_stream_write (os, &cdrstream_allocator, (char *)type_obj, DDS_XTypes_TypeObject_desc.m_ops))
    abort (); // internally generated data, so should never fail
}

#endif /* DDS_HAS_TYPE_DISCOVERY */

static void hexdump(const char *what, const unsigned char *msg, const size_t len)
{
#if HEXDUMP
  printf ("%s:\n", what);
  for (size_t off16 = 0; off16 < len; off16 += 16)
  {
    printf ("%04" PRIxSIZE " ", off16);
    char sep = ' ';
    size_t off1;
    for (off1 = 0; off1 < 16 && off16 + off1 < len; off1++) {
      printf ("%s%c%02x", (off1 == 8) ? " " : "", sep, msg[off16 + off1]);
    }
    for (; off1 < 16; off1++) {
      printf ("%s%c  ", (off1 == 8) ? " " : "", (sep == '[') ? ']' : sep);
      sep = ' ';
    }
    printf ("  |");
    for (off1 = 0; off1 < 16 && off16 + off1 < len; off1++) {
      unsigned char c = msg[off16 + off1];
      printf ("%c", (c >= 32 && c < 127) ? c : '.');
    }
    printf ("|\n");
  }
  fflush (stdout);
#endif
}

static ddspy_serdata_t *ddspy_serdata_new (const struct ddsi_sertype *type, enum ddsi_serdata_kind kind, size_t data_size)
{
  ddspy_serdata_t *new = dds_alloc (sizeof (struct ddspy_serdata));
  ddsi_serdata_init ((ddsi_serdata_t *)new, type, kind);
  new->data = dds_alloc (data_size);
  new->data_size = data_size;
  new->key = NULL;
  new->key_size = 0;
  new->is_v2 = false;
  return new;
}

static bool ddspy_serdata_populate_key (ddspy_serdata_t *this)
{
  const uint32_t xcdr_version = this->is_v2 ? DDSI_RTPS_CDR_ENC_VERSION_2 : DDSI_RTPS_CDR_ENC_VERSION_1;

  // Encoding is a 16-bit number in big-endian format in the first 2 bytes,
  // odd numbers correspond to little-endian
  unsigned char * const endianness_encoding_byte = (unsigned char *) this->data + 1;
  const bool input_is_le = *endianness_encoding_byte & 1;
#if DDSRT_ENDIAN == DDSRT_LITTLE_ENDIAN
  const bool needs_bswap = !input_is_le;
#elif DDSRT_ENDIAN == DDSRT_BIG_ENDIAN
  const bool needs_bswap = input_is_le;
#endif

  hexdump("populate_key input", this->data, this->data_size);

  // The python serializer doesn't detect that in:
  // enum E { A, B, C }
  // union T switch (E) { ... }
  // union U switch (boolean) { case true: T value }
  // struct S { U m }
  //
  // write (S(m=T(discriminant=B, value=...)))
  //
  // there's an entire layer of unions missing and because it can't find "B" in the
  // list of labels in U (i.e., "B" is not in "[True]") it serializes "B" and skips
  // "value".  It so happens that "B"'s serialization matches that of "True" (on a
  // little endian machine, but there are variants where endianness doesn't matter),
  // and so dds_stream_extract_key will take the "true" case and try to deserialize
  // T.
  //
  // That's effectively malformed input and dds_stream_extract_key only handles
  // well-formed inputs.  So we'd better check.
  void * const cdr_data = (char *)this->data + 4;
  uint32_t act_size;
  if (!dds_stream_normalize (cdr_data, (uint32_t)this->data_size - 4, needs_bswap, xcdr_version, &csertype(this)->cdrstream_desc, (this->c_data.kind == SDK_KEY), &act_size))
    return false;
  // Fixup encoding header if we byte-swapped the contents
  if (needs_bswap)
    *endianness_encoding_byte ^= 1;

  dds_ostream_t os;
  dds_ostream_init (&os, &cdrstream_allocator, 0, DDSI_RTPS_CDR_ENC_VERSION_2);
  dds_istream_t is;
  dds_istream_init (&is, (uint32_t)this->data_size - 4, cdr_data, xcdr_version);

  bool extract_result;
  if (this->c_data.kind == SDK_KEY)
  {
    hexdump("extract_key_from_key input", is.m_buffer, is.m_size);
    dds_stream_extract_key_from_key (&is, &os, DDS_CDR_KEY_SERIALIZATION_SAMPLE, &cdrstream_allocator, &csertype(this)->cdrstream_desc);
    extract_result = true;
  }
  else
  {
    hexdump("extract_key_from_data input", is.m_buffer, is.m_size);
    extract_result = dds_stream_extract_key_from_data (&is, &os, &cdrstream_allocator, &csertype(this)->cdrstream_desc);
  }
  if (extract_result)
  {
    hexdump("extracted key", os.m_buffer, os.m_index);
    this->key_size = os.m_index;
    this->key = dds_alloc (this->key_size);
    memcpy ((char *)this->key, os.m_buffer, os.m_index);
  }
  dds_ostream_fini (&os, &cdrstream_allocator);
  return extract_result;
}

static uint32_t hash_value (void *data, const size_t sz)
{
  if (sz == 0)
    return 0;

  unsigned char buf[16];
  ddsrt_md5_state_t md5st;
  ddsrt_md5_init (&md5st);
  ddsrt_md5_append (&md5st, (ddsrt_md5_byte_t *)data, (uint32_t)sz);
  ddsrt_md5_finish (&md5st, (ddsrt_md5_byte_t *)buf);
  return *(uint32_t *)buf;
}

static void ddspy_serdata_populate_hash (ddspy_serdata_t *this)
{
  ddsi_serdata_t *sd = (ddsi_serdata_t *)this;

  // set initial hash to that of type
  sd->hash = sd->type->serdata_basehash;

  // xor type hash with hash of key
  const uint32_t key_hash = hash_value (this->key, this->key_size);
  sd->hash ^= key_hash;
}

static bool serdata_eqkey (const struct ddsi_serdata *a, const struct ddsi_serdata *b)
{
  const ddspy_serdata_t *apy = cserdata(a), *bpy = cserdata(b);
  if (csertype(apy)->keyless ^ csertype(bpy)->keyless)
    return false;
  if (csertype(apy)->keyless && csertype(bpy)->keyless)
    return true;
  assert (cserdata(a)->key != NULL);
  assert (cserdata(b)->key != NULL);
  if (cserdata(a)->key_size != cserdata(b)->key_size) return false;
  return 0 == memcmp (cserdata(a)->key, cserdata(b)->key, cserdata(a)->key_size);
}

static uint32_t serdata_size (const struct ddsi_serdata *dcmn)
{
  assert (cserdata(dcmn)->key != NULL);
  assert (cserdata(dcmn)->data != NULL);
  return (uint32_t)cserdata(dcmn)->data_size;
}

static ddsi_serdata_t *serdata_from_common (ddspy_serdata_t *d, enum ddsi_serdata_kind kind)
{
  d->is_v2 = ((char *)d->data)[1] > 3;
  if (!ddspy_serdata_populate_key (d))
  {
    ddsi_serdata_unref ((ddsi_serdata_t *)d);
    return NULL;
  }
  ddspy_serdata_populate_hash (d);
  return (ddsi_serdata_t *)d;
}

static ddsi_serdata_t *serdata_from_ser (const struct ddsi_sertype *type, enum ddsi_serdata_kind kind, const struct ddsi_rdata *fragchain, size_t size)
{
  ddspy_serdata_t *d = ddspy_serdata_new (type, kind, size);

  uint32_t off = 0;
  assert (fragchain->min == 0);
  assert (fragchain->maxp1 >= off);    //CDR header must be in first fragment

  unsigned char *cursor = d->data;
  while (fragchain)
  {
    if (fragchain->maxp1 > off)
    {
      //only copy if this fragment adds data
      const unsigned char *payload =
        DDSI_RMSG_PAYLOADOFF (fragchain->rmsg, DDSI_RDATA_PAYLOAD_OFF (fragchain));
      const unsigned char *src = payload + off - fragchain->min;
      size_t n_bytes = fragchain->maxp1 - off;
      memcpy (cursor, src, n_bytes);
      cursor += n_bytes;
      off = fragchain->maxp1;
      assert (off <= size);
    }
    fragchain = fragchain->nextfrag;
  }
  return serdata_from_common (d, kind);
}

static ddsi_serdata_t *serdata_from_ser_iov (const struct ddsi_sertype *type, enum ddsi_serdata_kind kind, ddsrt_msg_iovlen_t niov, const ddsrt_iovec_t *iov, size_t size)
{
  ddspy_serdata_t *d = ddspy_serdata_new (type, kind, size);

  size_t off = 0;
  unsigned char *cursor = d->data;
  for (ddsrt_msg_iovlen_t i = 0; i < niov && off < size; i++)
  {
    size_t n_bytes = iov[i].iov_len;
    if (n_bytes + off > size) n_bytes = size - off;
    memcpy (cursor, iov[i].iov_base, n_bytes);
    cursor += n_bytes;
    off += n_bytes;
  }
  return serdata_from_common (d, kind);
}

static ddsi_serdata_t *serdata_from_keyhash (const struct ddsi_sertype *topic, const struct ddsi_keyhash *keyhash)
{
  (void)keyhash;
  (void)topic;
  //replace with (if key_size_max <= 16) then populate the data class with the key hash (key_read)
  // TODO
  assert (0);
  return NULL;
}

static ddsi_serdata_t *serdata_from_sample (const ddsi_sertype_t *type, enum ddsi_serdata_kind kind, const void *sample)
{
  ddspy_sample_container_t *container = (ddspy_sample_container_t *)sample;
  ddspy_serdata_t *d = ddspy_serdata_new (type, kind, container->usample_size);
  memcpy ((char *)d->data, container->usample, container->usample_size);
  return serdata_from_common (d, kind);
}

static void serdata_to_ser (const ddsi_serdata_t *dcmn, size_t off, size_t sz, void *buf)
{
  memcpy (buf, (char *)cserdata(dcmn)->data + off, sz);
}

static ddsi_serdata_t *serdata_to_ser_ref (const struct ddsi_serdata *dcmn, size_t off, size_t sz, ddsrt_iovec_t *ref)
{
  ref->iov_base = (char *)cserdata(dcmn)->data + off;
  ref->iov_len = (ddsrt_iov_len_t)sz;
  return ddsi_serdata_ref (dcmn);
}

static void serdata_to_ser_unref (struct ddsi_serdata *dcmn, const ddsrt_iovec_t *ref)
{
  (void)ref;    // unused
  ddsi_serdata_unref (dcmn);
}

static bool serdata_to_sample (const ddsi_serdata_t *dcmn, void *sample, void **bufptr, void *buflim)
{
  (void)bufptr;
  (void)buflim;
  ddspy_sample_container_t *container = (ddspy_sample_container_t *)sample;
  assert (container->usample == NULL);
  container->usample = dds_alloc (cserdata(dcmn)->data_size);
  memcpy (container->usample, cserdata(dcmn)->data, cserdata(dcmn)->data_size);
  container->usample_size = cserdata(dcmn)->data_size;
  return true;
}

static ddsi_serdata_t *serdata_to_typeless (const ddsi_serdata_t *dcmn)
{
  const ddspy_serdata_t *d = cserdata(dcmn);
  ddspy_serdata_t *d_tl = dds_alloc (sizeof (struct ddspy_serdata));
  assert (d_tl);
  ddsi_serdata_init ((ddsi_serdata_t *)d_tl, dcmn->type, SDK_KEY);
  d_tl->data = NULL;
  d_tl->data_size = 0;
  d_tl->key = ddsrt_memdup (d->key, d->key_size);
  d_tl->key_size = d->key_size;
  d_tl->is_v2 = d->is_v2;
  d_tl->c_data.hash = d->c_data.hash;
  return (struct ddsi_serdata *)d_tl;
}

static bool serdata_typeless_to_sample (const struct ddsi_sertype *type, const struct ddsi_serdata *dcmn, void *sample, void **buf, void *buflim)
{
  ddspy_sample_container_t *container = (ddspy_sample_container_t *)sample;
  ddspy_sertype_t const * const pyst = (const ddspy_sertype_t *) type;
  ddspy_serdata_t const * const pysd = cserdata (dcmn);
  (void)buf;
  (void)buflim;

  assert (container->usample == NULL);

  struct { uint16_t enc; uint16_t options; } header;
  header.options = 0;
#if DDSRT_ENDIAN == DDSRT_BIG_ENDIAN
  if (pysd->is_v2) {
    switch (pyst->cdrstream_desc.ops.ops[0]) {
      case DDS_OP_DLC: header.enc = DDSI_RTPS_D_CDR2_BE; break;
      case DDS_OP_PLC: header.enc = DDSI_RTPS_PL_CDR2_BE; break;
      default: header.enc = DDSI_RTPS_CDR2_BE; break;
    }
  } else {
    switch (pyst->cdrstream_desc.ops.ops[0]) {
      case DDS_OP_PLC: header.enc = DDSI_RTPS_PL_CDR_BE; break;
      default: header.enc = DDSI_RTPS_CDR_BE; break;
    }    
  }
#elif DDSRT_ENDIAN == DDSRT_LITTLE_ENDIAN
  if (pysd->is_v2) {
    switch (pyst->cdrstream_desc.ops.ops[0]) {
      case DDS_OP_DLC: header.enc = DDSI_RTPS_D_CDR2_LE; break;
      case DDS_OP_PLC: header.enc = DDSI_RTPS_PL_CDR2_LE; break;
      default: header.enc = DDSI_RTPS_CDR2_LE; break;
    }
  } else {
    switch (pyst->cdrstream_desc.ops.ops[0]) {
      case DDS_OP_PLC: header.enc = DDSI_RTPS_PL_CDR_LE; break;
      default: header.enc = DDSI_RTPS_CDR_LE; break;
    }    
  }
#else
#error "endianness not set properly"
#endif

  if (pysd->is_v2)
  {
    container->usample = dds_alloc (pysd->key_size + 4);
    container->usample_size = pysd->key_size + 4;
    memcpy (container->usample, &header, 4);
    memcpy ((char *) container->usample + 4, pysd->key, pysd->key_size);
  }
  else
  {
    dds_istream_t is;
    dds_istream_init (&is, pysd->key_size, pysd->key, DDSI_RTPS_CDR_ENC_VERSION_2);
    dds_ostream_t os;
    dds_ostream_init (&os, &dds_cdrstream_default_allocator, 0, pysd->is_v2 ? DDSI_RTPS_CDR_ENC_VERSION_2 : DDSI_RTPS_CDR_ENC_VERSION_1);
    dds_stream_extract_key_from_key (&is, &os, DDS_CDR_KEY_SERIALIZATION_SAMPLE, &dds_cdrstream_default_allocator, &pyst->cdrstream_desc);

    container->usample = dds_alloc (os.m_index + 4);
    container->usample_size = os.m_index + 4;
    memcpy (container->usample, &header, 4);
    memcpy ((char *) container->usample + 4, os.m_buffer, os.m_index);
    dds_ostream_fini (&os, &dds_cdrstream_default_allocator);
  }
  hexdump ("invalid sample", container->usample, container->usample_size);
  return true;
}

static void serdata_free (struct ddsi_serdata *dcmn)
{
  dds_free (serdata (dcmn)->data);
  dds_free (serdata (dcmn)->key);
  dds_free (dcmn);
}

static size_t serdata_print (const struct ddsi_sertype *tpcmn, const struct ddsi_serdata *dcmn, char *buf, size_t bufsize)
{
  (void)tpcmn;
  (void)dcmn;
  (void)buf;
  (void)bufsize;
  return 0;
}

static void serdata_get_keyhash (const ddsi_serdata_t *d, struct ddsi_keyhash *buf, bool force_md5)
{
  assert (cserdata(d)->data != NULL);
  assert (cserdata(d)->data_size != 0);
  assert (d->type != NULL);

  if (csertype (cserdata(d))->keyless)
  {
    memset (buf->value, 0, 16);
    return;
  }

  bool is_v2 = cserdata(d)->is_v2;
  bool v1_key_maxsize_bigger_16 = csertype (cserdata(d))->v1_key_maxsize_bigger_16;
  bool v2_key_maxsize_bigger_16 = csertype (cserdata(d))->v2_key_maxsize_bigger_16;

  assert (le_key != NULL);
  assert (le_keysz > 0);

  dds_istream_t is;
  dds_istream_init (&is, cserdata(d)->key_size, cserdata(d)->key, DDSI_RTPS_CDR_ENC_VERSION_2);
  dds_ostreamBE_t os;
  dds_ostreamBE_init (&os, &cdrstream_allocator, 16, is_v2 ? DDSI_RTPS_CDR_ENC_VERSION_2 : DDSI_RTPS_CDR_ENC_VERSION_1);
  hexdump ("keyhash input", is.m_buffer, is.m_size);
  dds_stream_extract_keyBE_from_key (&is, &os, DDS_CDR_KEY_SERIALIZATION_KEYHASH, &cdrstream_allocator, &csertype (cserdata(d))->cdrstream_desc);
  assert (is.m_index == cserdata(d)->key_size);
  hexdump ("serialized key for keyhash", os.x.m_buffer, os.x.m_index);

  void *be_key = os.x.m_buffer;
  size_t be_keysz = os.x.m_index;

  if (be_keysz < 16)
    memset ((char *)be_key + be_keysz, 0, 16 - be_keysz);
  if (force_md5 || (is_v2 && v2_key_maxsize_bigger_16) || (!is_v2 && v1_key_maxsize_bigger_16))
  {
    ddsrt_md5_state_t md5st;
    ddsrt_md5_init (&md5st);
    ddsrt_md5_append (&md5st, be_key, be_keysz > 16 ? (uint32_t)be_keysz : 16);
    ddsrt_md5_finish (&md5st, buf->value);
  }
  else
  {
    assert (be_keysz <= 16);
    memset (buf->value, 0, 16);
    memcpy (buf->value, be_key, be_keysz);
  }
  dds_ostreamBE_fini (&os, &cdrstream_allocator);

  hexdump ("keyhash", buf->value, 16);
}

const struct ddsi_serdata_ops ddspy_serdata_ops = {
  &serdata_eqkey,
  &serdata_size,
  &serdata_from_ser,
  &serdata_from_ser_iov,
  &serdata_from_keyhash,
  &serdata_from_sample,
  &serdata_to_ser,
  &serdata_to_ser_ref,
  &serdata_to_ser_unref,
  &serdata_to_sample,
  &serdata_to_typeless,
  &serdata_typeless_to_sample,
  &serdata_free,
  &serdata_print,
  &serdata_get_keyhash
};

static void sertype_free (struct ddsi_sertype *tpcmn)
{
  struct ddspy_sertype *this = (struct ddspy_sertype *)tpcmn;
  if (this->typeinfo_ser_sz)
    dds_free (this->typeinfo_ser_data);
  if (this->typemap_ser_sz)
    dds_free (this->typemap_ser_data);
  dds_cdrstream_desc_fini (&this->cdrstream_desc, &cdrstream_allocator);

  // dds_free the python type if python isn't already shutting down (deadlock).#
#if PY_MINOR_VERSION >= 13
  if (!Py_IsFinalizing ())
  {
    PyGILState_STATE state = PyGILState_Ensure ();
    Py_DECREF (this->my_py_type);
    PyGILState_Release (state);
  }
#elif PY_MINOR_VERSION > 6
  if (!_Py_IsFinalizing ())
  {
    PyGILState_STATE state = PyGILState_Ensure ();
    Py_DECREF (this->my_py_type);
    PyGILState_Release (state);
  }
#else
  if (PyGILState_GetThisThreadState () != _Py_Finalizing)
  {
    PyGILState_STATE state = PyGILState_Ensure ();
    Py_DECREF (this->my_py_type);
    PyGILState_Release (state);
  }
#endif
  ddsi_sertype_fini (tpcmn);
  dds_free (this);
}

static void sertype_zero_samples (const struct ddsi_sertype *sertype_common, void *samples, size_t count)
{
  (void)sertype_common;
  memset (samples, 0, sizeof (ddspy_sample_container_t) *count);
}

static void sertype_realloc_samples (void **ptrs, const struct ddsi_sertype *sertype_common, void *old, size_t oldcount, size_t count)
{
  (void)sertype_common;
  char *new = (oldcount == count) ? old : dds_realloc (old, sizeof (ddspy_sample_container_t) *count);
  if (new && count > oldcount)
    memset (new + sizeof (ddspy_sample_container_t) *oldcount, 0, sizeof (ddspy_sample_container_t) * (count - oldcount));

  for (size_t i = 0; i < count; i++)
  {
    void *ptr = (char *)new + i *sizeof (ddspy_sample_container_t);
    ptrs[i] = ptr;
  }
}

static void sertype_free_samples (const struct ddsi_sertype *sertype_common, void **ptrs, size_t count, dds_free_op_t op)
{
  (void)sertype_common;
  if (count > 0)
  {
    if (op & DDS_FREE_CONTENTS_BIT)
    {
      if (((ddspy_sample_container_t *)ptrs[0])->usample != NULL)
        dds_free (((ddspy_sample_container_t *)ptrs[0])->usample);
    }

    if (op & DDS_FREE_ALL_BIT)
    {
      dds_free (ptrs[0]);
    }
  }
}

static bool sertype_equal (const ddsi_sertype_t *acmn, const ddsi_sertype_t *bcmn)
{
  // Sertypes are equal if:
  //    1: they point to the same point in memory (trivial)
  //    1: they point to the same python object
  //    2: the python objects they point to contain the same type info

  const ddspy_sertype_t *A = (const ddspy_sertype_t *)acmn;
  const ddspy_sertype_t *B = (const ddspy_sertype_t *)bcmn;

  if (A == B)
    return true;

  if (A->my_py_type == NULL || B->my_py_type == NULL) // should never be true
    return false;

  if (A->my_py_type == B->my_py_type)
    return true;

  // Expensive stuff coming up here
  PyGILState_STATE state = PyGILState_Ensure ();
  int result = PyObject_RichCompareBool (A->my_py_type, B->my_py_type, Py_EQ);
  PyGILState_Release (state);
  return result == 1;
}

static uint32_t sertype_hash (const struct ddsi_sertype *tpcmn)
{
  (void)tpcmn;
  return 0x0u;
}

static ddsi_typeid_t *sertype_typeid (const struct ddsi_sertype *tpcmn, ddsi_typeid_kind_t kind)
{
  assert (tpcmn);
  assert (kind == DDSI_TYPEID_KIND_MINIMAL || kind == DDSI_TYPEID_KIND_COMPLETE);

  const struct ddspy_sertype *type = (struct ddspy_sertype *)tpcmn;
  ddsi_typeinfo_t *type_info = ddsi_typeinfo_deser (type->typeinfo_ser_data, type->typeinfo_ser_sz);
  if (type_info == NULL)
    return NULL;
  ddsi_typeid_t *type_id = ddsi_typeinfo_typeid (type_info, kind);
  ddsi_typeinfo_fini (type_info);
  ddsrt_free (type_info);
  return type_id;
}

static ddsi_typemap_t *sertype_typemap (const struct ddsi_sertype *tpcmn)
{
  assert (tpcmn);
  const struct ddspy_sertype *type = (struct ddspy_sertype *)tpcmn;
  return ddsi_typemap_deser (type->typemap_ser_data, type->typemap_ser_sz);
}

static ddsi_typeinfo_t *sertype_typeinfo (const struct ddsi_sertype *tpcmn)
{
  assert (tpcmn);
  const struct ddspy_sertype *type = (struct ddspy_sertype *)tpcmn;
  return ddsi_typeinfo_deser (type->typeinfo_ser_data, type->typeinfo_ser_sz);
}

static struct ddsi_sertype *sertype_derive_sertype (const struct ddsi_sertype *base_sertype, dds_data_representation_id_t repr, dds_type_consistency_enforcement_qospolicy_t tceqos)
{
  // The python sertype can handle all types by itself, no derives needed
  DDSRT_UNUSED_ARG (repr);
  DDSRT_UNUSED_ARG (tceqos);
  return (struct ddsi_sertype *)base_sertype;
}

const struct ddsi_sertype_ops ddspy_sertype_ops = {
  .version = ddsi_sertype_v0,
  .arg = NULL,
  .equal = sertype_equal,
  .hash = sertype_hash,
  .free = sertype_free,
  .zero_samples = sertype_zero_samples,
  .realloc_samples = sertype_realloc_samples,
  .free_samples = sertype_free_samples,

  .type_id = sertype_typeid,
  .type_map = sertype_typemap,
  .type_info = sertype_typeinfo,
  .derive_sertype = sertype_derive_sertype
};

static bool valid_py_allow_none_or_set_error (PyObject *py_obj)
{
  if (PyErr_Occurred ()) return false;
  if (py_obj != NULL) return true;

  PyErr_SetString (PyExc_TypeError, "Invalid python object.");
  return false;
}

static bool valid_topic_py_or_set_error (PyObject *py_obj)
{
  if (PyErr_Occurred ()) return false;
  if (py_obj != NULL && py_obj != Py_None) return true;

  PyErr_SetString (PyExc_TypeError, "Invalid python object used as topic datatype.");
  return false;
}

static ddspy_sertype_t *ddspy_sertype_new (PyObject *pytype)
{
  // PyObjects
  PyObject *idl = NULL, *pyname = NULL, *pydata_type_props = NULL, *pysupported_versions = NULL;
  PyObject *xt_type_data = NULL;
  Py_buffer xt_type_map_bytes, xt_type_info_bytes;
  ddspy_sertype_t *new = NULL;
  bool constructed = false;

  assert (pytype);

  // process
  idl = PyObject_GetAttrString (pytype, "__idl__");
  if (!valid_topic_py_or_set_error (idl)) goto err;

  pyname = PyObject_GetAttrString (idl, "idl_transformed_typename");
  if (!valid_topic_py_or_set_error (pyname)) goto err;

  pydata_type_props = PyObject_GetAttrString (idl, "data_type_props");
  if (!valid_topic_py_or_set_error (pydata_type_props)) goto err;

  pysupported_versions = PyObject_GetAttrString (idl, "supported_versions");
  if (!valid_topic_py_or_set_error (pysupported_versions)) goto err;

  xt_type_data = PyObject_GetAttrString (idl, "_xt_bytedata");
  if (!valid_py_allow_none_or_set_error (xt_type_data)) goto err;

  const char *name = PyUnicode_AsUTF8 (pyname);
  if (name == NULL) goto err;

  const dds_data_type_properties_t data_type_props = PyLong_AsUnsignedLongLong (pydata_type_props);
  const bool keyless = !(data_type_props & DDS_DATA_TYPE_CONTAINS_KEY);
  
  new = dds_alloc (sizeof (ddspy_sertype_t));

  Py_INCREF (pytype);
  new->my_py_type = pytype;
  new->keyless = keyless;

  if (xt_type_data != Py_None && PyTuple_GetItem (xt_type_data, 0) != Py_None)
  {
    if (!PyArg_ParseTuple (xt_type_data, "y*y*", &xt_type_info_bytes, &xt_type_map_bytes))
      goto err;

    new->typemap_ser_data = dds_alloc ((size_t)xt_type_map_bytes.len);

    if (new->typemap_ser_data == NULL)
    {
      PyBuffer_Release (&xt_type_map_bytes);
      PyBuffer_Release (&xt_type_info_bytes);
      Py_XDECREF (xt_type_data);
      goto err;
    }

    new->typeinfo_ser_data = dds_alloc ((size_t)xt_type_info_bytes.len);

    if (new->typeinfo_ser_data == NULL)
    {
      dds_free (new->typemap_ser_data);
      PyBuffer_Release (&xt_type_map_bytes);
      PyBuffer_Release (&xt_type_info_bytes);
      Py_XDECREF (xt_type_data);
      goto err;
    }

    new->typemap_ser_sz = (uint32_t)xt_type_map_bytes.len;
    memcpy (new->typemap_ser_data, xt_type_map_bytes.buf, new->typemap_ser_sz);

    new->typeinfo_ser_sz = (uint32_t)xt_type_info_bytes.len;
    memcpy (new->typeinfo_ser_data, xt_type_info_bytes.buf, new->typeinfo_ser_sz);

    PyBuffer_Release (&xt_type_info_bytes);
    PyBuffer_Release (&xt_type_map_bytes);
    Py_XDECREF (xt_type_data);
  }
  else
  {
    new->typemap_ser_data = NULL;
    new->typemap_ser_sz = 0;
    new->typeinfo_ser_data = NULL;
    new->typeinfo_ser_sz = 0;
  }

  ddsi_sertype_init_props (&new->my_c_type, name, &ddspy_sertype_ops, &ddspy_serdata_ops,
    sizeof (ddspy_sample_container_t),
    data_type_props,
    PyLong_AsLong(pysupported_versions),
    0);
  constructed = true;

 err:
  if (new && !constructed)
  {
    dds_free (new);
    PyErr_SetString (PyExc_RuntimeError, "Error in constructing DDS sertype.");
    new = NULL;
  }

  Py_XDECREF (idl);
  Py_XDECREF (pyname);
  Py_XDECREF (pydata_type_props);
  Py_XDECREF (pysupported_versions);
  return new;
}

static dds_return_t init_cdrstream_descriptor (ddspy_sertype_t *sertype)
{
  dds_return_t ret = DDS_RETCODE_OK;

  ddsi_typeinfo_t *type_info = ddsi_typeinfo_deser (sertype->typeinfo_ser_data, sertype->typeinfo_ser_sz);
  if (type_info == NULL) {
    ret = DDS_RETCODE_ERROR;
    goto err_typeinfo;
  }

  const ddsi_typeid_t *type_id = ddsi_typeinfo_complete_typeid (type_info);
  if (type_id == NULL) {
    ret = DDS_RETCODE_ERROR;
    goto err;
  }

  struct ddsi_domaingv *const gv = ddsrt_atomic_ldvoidp (&sertype->my_c_type.gv);
  if (gv == NULL) {
    ret = DDS_RETCODE_ERROR;
    goto err;
  }

  const struct ddsi_type *ddsi_type = ddsi_type_lookup (gv, type_id);
  if (ddsi_type == NULL) {
    ret = DDS_RETCODE_ERROR;
    goto err;
  }

  dds_topic_descriptor_t desc;
  if ((ret = ddsi_topic_descriptor_from_type (gv, &desc, ddsi_type)) != DDS_RETCODE_OK)
    goto err;

  dds_cdrstream_desc_init (&sertype->cdrstream_desc, &cdrstream_allocator, desc.m_size, desc.m_align, desc.m_flagset, desc.m_ops, desc.m_keys, desc.m_nkeys);
  sertype->v1_key_maxsize_bigger_16 = !(sertype->cdrstream_desc.flagset & DDS_TOPIC_FIXED_KEY);
  sertype->v2_key_maxsize_bigger_16 = !(sertype->cdrstream_desc.flagset & DDS_TOPIC_FIXED_KEY_XCDR2);
  ddsi_topic_descriptor_fini (&desc);

 err:
  ddsi_typeinfo_free (type_info);
 err_typeinfo:
  return ret;
}

/// Python BIND

static PyObject *ddspy_topic_create (PyObject *self, PyObject *args)
{
  const char *name;
  PyObject *datatype;
  dds_entity_t participant;
  dds_entity_t sts;
  PyObject *qospy;
  PyObject *listenerpy;
  dds_listener_t *listener = NULL;
  dds_qos_t *qos = NULL;
  (void)self;

  if (!PyArg_ParseTuple (args, "lsOOO", &participant, &name, &datatype, &qospy, &listenerpy))
    return NULL;

  if (listenerpy != Py_None)
    listener = PyLong_AsVoidPtr (listenerpy);
  if (qospy != Py_None)
    qos = PyLong_AsVoidPtr (qospy);

  ddspy_sertype_t *sertype = ddspy_sertype_new (datatype);

  if (sertype == NULL)
    return NULL;

  Py_BEGIN_ALLOW_THREADS
  sts = dds_create_topic_sertype (participant, name, (struct ddsi_sertype **) &sertype, qos, listener, NULL);
  Py_END_ALLOW_THREADS

  if (PyErr_Occurred () || sts < 0)
  {
    ddsi_sertype_unref ((struct ddsi_sertype *)sertype);
  }
  else
  {
    dds_return_t ret = init_cdrstream_descriptor (sertype);
    if (ret != DDS_RETCODE_OK)
    {
      dds_delete (sts);
      sts = ret;
    }
  }

  if (PyErr_Occurred ())
  {
    if (sts > 0)
    {
      dds_delete (sts);
      dds_cdrstream_desc_fini (&sertype->cdrstream_desc, &cdrstream_allocator);
    }
    return NULL;
  }

  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_write (PyObject *self, PyObject *args)
{
  ddspy_sample_container_t container;
  dds_entity_t writer;
  dds_return_t sts;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*", &writer, &sample_data))
    return NULL;

  assert (PyBuffer_IsContiguous (&sample_data, 'C'));

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_write (writer, &container);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_write_ts (PyObject *self, PyObject *args)
{
  ddspy_sample_container_t container;
  dds_entity_t writer;
  dds_return_t sts;
  dds_time_t time;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*L", &writer, &sample_data, &time))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_write_ts (writer, &container, time);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_dispose (PyObject *self, PyObject *args)
{
  ddspy_sample_container_t container;
  dds_entity_t writer;
  dds_return_t sts;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*", &writer, &sample_data))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_dispose (writer, &container);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_dispose_ts (PyObject *self, PyObject *args)
{
  ddspy_sample_container_t container;
  dds_entity_t writer;
  dds_return_t sts;
  dds_time_t time;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*L", &writer, &sample_data, &time))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_dispose_ts (writer, &container, time);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_writedispose (PyObject *self, PyObject *args)
{
  ddspy_sample_container_t container;
  dds_entity_t writer;
  dds_return_t sts;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*", &writer, &sample_data))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_writedispose (writer, &container);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_writedispose_ts (PyObject *self, PyObject *args)
{
  ddspy_sample_container_t container;
  dds_entity_t writer;
  dds_return_t sts;
  dds_time_t time;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*L", &writer, &sample_data, &time))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_writedispose_ts (writer, &container, time);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_dispose_handle (PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_return_t sts;
  dds_instance_handle_t handle;
  (void)self;

  if (!PyArg_ParseTuple (args, "iK", &writer, &handle))
    return NULL;

  sts = dds_dispose_ih (writer, handle);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_dispose_handle_ts (PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_return_t sts;
  dds_instance_handle_t handle;
  dds_time_t time;
  (void)self;

  if (!PyArg_ParseTuple (args, "iKL", &writer, &handle, &time))
    return NULL;

  sts = dds_dispose_ih_ts (writer, handle, time);
  return PyLong_FromLong ((long)sts);
}

static PyObject *sampleinfo_descriptor;

static PyObject *get_sampleinfo_pyobject (dds_sample_info_t *sampleinfo)
{
  PyObject *arguments = Py_BuildValue (
          "IIIOLKKkkkkk",
          sampleinfo->sample_state,
          sampleinfo->view_state,
          sampleinfo->instance_state,
          (sampleinfo->valid_data > 0) ? Py_True : Py_False,
          sampleinfo->source_timestamp,
          sampleinfo->instance_handle,
          sampleinfo->publication_handle,
          sampleinfo->disposed_generation_count,
          sampleinfo->no_writers_generation_count,
          sampleinfo->sample_rank,
          sampleinfo->generation_rank,
          sampleinfo->absolute_generation_rank);
  PyObject *pysampleinfo = PyObject_CallObject (sampleinfo_descriptor, arguments);
  Py_DECREF (arguments);
  return pysampleinfo;
}

static inline uint32_t check_number_of_samples (long long n)
{
  static const uint32_t max_samples = (UINT32_MAX / sizeof (dds_sample_info_t));

  if (n <= 0)
  {
    PyErr_SetString (PyExc_TypeError, "N must be a positive integer");
    return 0u;
  }
  if (n > (long long)max_samples)
  {
    PyErr_SetString (PyExc_TypeError, "N exceeds maximum");
    return 0u;
  }
  return (uint32_t)n;
}

static PyObject *readtake_post (int32_t sts, collector_state_t *state)
{
  if (sts < 0 && state->count == 0)
    return PyLong_FromLong ((long)sts);

  PyObject *list = PyList_New((Py_ssize_t)state->count);
  for (size_t i = 0; i < state->count; ++i)
  {
    PyObject *sampleinfo = get_sampleinfo_pyobject(&state->sample_infos[i]);
    PyObject *item = Py_BuildValue("(y#O)", 
                                   state->containers[i].usample,
                                   (Py_ssize_t)state->containers[i].usample_size,
                                   sampleinfo);
    PyList_SetItem(list, (Py_ssize_t)i, item); // steals ref
    Py_DECREF(sampleinfo);
    dds_free(state->containers[i].usample);
  }

  dds_free(state->containers);
  dds_free(state->sample_infos);

  return list;
}

dds_return_t collector_callback_fn(
  void *arg,
  const dds_sample_info_t *info,
  const struct ddsi_sertype *sertype,
  struct ddsi_serdata *serdata)
{
  collector_state_t *state = (collector_state_t *)arg;

  if (state->count >= state->capacity)
  {
    // Grow allocation, this ensures amortized linear growth while keeping allocation calls minimal.
    // Doubling gives exponential growth this makes adding N items only require log2(N) reallocations - efficient!
    size_t new_capacity = state->capacity ? state->capacity * 2 : 8;
    
    void *new_containers = dds_realloc(state->containers, new_capacity * sizeof(ddspy_sample_container_t));
    void *new_infos = dds_realloc(state->sample_infos, new_capacity * sizeof(dds_sample_info_t));

    if (!new_containers || !new_infos)
      return DDS_RETCODE_OUT_OF_RESOURCES;

    state->containers = new_containers;
    state->sample_infos = new_infos;
    state->capacity = new_capacity;
  }

  bool ok;
  if (info->valid_data)
    ok = ddsi_serdata_to_sample (serdata,  &state->containers[state->count], NULL, NULL);
  else
    ok = ddsi_serdata_untyped_to_sample (sertype, serdata, &state->containers[state->count], NULL, NULL);
  if (!ok)
    return DDS_RETCODE_OUT_OF_RESOURCES;

  state->sample_infos[state->count] = *info;
  state->count++;
  return DDS_RETCODE_OK;
}

static PyObject *ddspy_readtake (PyObject *args, dds_return_t (*readtake) (dds_entity_t, uint32_t, dds_instance_handle_t, uint32_t, dds_read_with_collector_fn_t, void *))
{
  dds_entity_t reader;
  uint32_t mask;
  long long N;
  if (!PyArg_ParseTuple (args, "iIL", &reader, &mask, &N))
    return NULL;

  if (!(check_number_of_samples (N)))
    return NULL;

  collector_state_t state = {
    .containers = NULL,
    .sample_infos = NULL,
    .count = 0,
    .capacity = 0
  };

  dds_return_t sts = readtake(
    reader,
    (uint32_t)N,
    DDS_HANDLE_NIL,
    mask,
    collector_callback_fn,
    &state);

  return readtake_post((int32_t)sts, &state);
}

static PyObject *ddspy_readtake_handle (PyObject *args, dds_return_t (*readtake) (dds_entity_t, uint32_t, dds_instance_handle_t, uint32_t, dds_read_with_collector_fn_t, void *))
{
  long long N;
  dds_entity_t reader;
  uint32_t mask;
  dds_instance_handle_t handle;

  if (!PyArg_ParseTuple (args, "iILK", &reader, &mask, &N, &handle))
    return NULL;

  collector_state_t state = {
    .containers = NULL,
    .sample_infos = NULL,
    .count = 0,
    .capacity = 0
  };

  dds_return_t sts = readtake(
    reader,
    (uint32_t)N,
    handle,
    mask,
    collector_callback_fn,
    &state);

  return readtake_post((int32_t)sts, &state);
}

static PyObject *ddspy_readtake_next (PyObject *args, dds_return_t (*readtake) (dds_entity_t, void **, dds_sample_info_t *))
{
  dds_entity_t reader;
  dds_return_t sts;
  dds_sample_info_t info;
  ddspy_sample_container_t container;
  ddspy_sample_container_t *pt_container;

  container.usample = NULL;

  if (!PyArg_ParseTuple (args, "i", &reader))
    return NULL;

  pt_container = &container;

  sts = readtake (reader, (void **) &pt_container, &info);
  if (sts < 0)
    return PyLong_FromLong ((long)sts);

  if (sts == 0 || container.usample == NULL)
  {
    Py_INCREF (Py_None);
    return Py_None;
  }

  PyObject *sampleinfo = get_sampleinfo_pyobject (&info);
  PyObject *item = Py_BuildValue ("(y#O)", container.usample, container.usample_size, sampleinfo);
  Py_DECREF (sampleinfo);
  dds_free (container.usample);
  return item;
}

static PyObject *ddspy_read (PyObject *self, PyObject *args)
{
  (void)self;
  return ddspy_readtake (args, dds_read_with_collector);
}

static PyObject *ddspy_take (PyObject *self, PyObject *args)
{
  (void)self;
  return ddspy_readtake (args, dds_take_with_collector);
}

static PyObject *ddspy_read_handle (PyObject *self, PyObject *args)
{
  (void)self;
  return ddspy_readtake_handle (args, dds_read_with_collector);
}

static PyObject *ddspy_take_handle (PyObject *self, PyObject *args)
{
  (void)self;
  return ddspy_readtake_handle (args, dds_take_with_collector);
}

static PyObject *ddspy_read_next (PyObject *self, PyObject *args)
{
  (void)self;
  return ddspy_readtake_next (args, dds_read_next);
}

static PyObject *ddspy_take_next (PyObject *self, PyObject *args)
{
  (void)self;
  return ddspy_readtake_next (args, dds_take_next);
}

static PyObject *ddspy_register_instance (PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_instance_handle_t handle;
  dds_return_t sts;
  ddspy_sample_container_t container;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*", &writer, &sample_data))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  handle = 0;
  container.usample_size = (size_t)sample_data.len;

  sts = dds_register_instance (writer, &handle, &container);

  PyBuffer_Release (&sample_data);

  if (sts < 0)
    return PyLong_FromLong ((long)sts);
  else
    return PyLong_FromUnsignedLongLong ((unsigned long long)handle);
}

static PyObject *ddspy_unregister_instance (PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_return_t sts;
  ddspy_sample_container_t container;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*", &writer, &sample_data))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_unregister_instance (writer, &container);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_unregister_instance_handle (PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_return_t sts;
  dds_instance_handle_t handle;
  (void)self;

  if (!PyArg_ParseTuple (args, "iK", &writer, &handle))
    return NULL;

  sts = dds_unregister_instance_ih (writer, handle);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_unregister_instance_ts (PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_return_t sts;
  ddspy_sample_container_t container;
  dds_time_t time;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*L", &writer, &sample_data, &time))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_unregister_instance_ts (writer, &container, time);

  PyBuffer_Release (&sample_data);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_unregister_instance_handle_ts (PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_return_t sts;
  dds_instance_handle_t handle;
  dds_time_t time;
  (void)self;

  if (!PyArg_ParseTuple (args, "iKL", &writer, &handle, &time))
    return NULL;

  sts = dds_unregister_instance_ih_ts (writer, handle, time);
  return PyLong_FromLong ((long)sts);
}

static PyObject *ddspy_lookup_instance (PyObject *self, PyObject *args)
{
  dds_entity_t entity;
  dds_instance_handle_t sts;
  ddspy_sample_container_t container;
  Py_buffer sample_data;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*", &entity, &sample_data))
    return NULL;

  container.usample = sample_data.buf;
  assert (sample_data.len >= 0);
  container.usample_size = (size_t)sample_data.len;

  sts = dds_lookup_instance (entity, &container);

  PyBuffer_Release (&sample_data);
  return PyLong_FromUnsignedLongLong ((unsigned long long)sts);
}

static PyObject *ddspy_calc_key (PyObject *self, PyObject *args)
{
  Py_buffer sample_data;
  dds_entity_t topic;
  (void)self;

  if (!PyArg_ParseTuple (args, "iy*", &topic, &sample_data))
    return NULL;

  const struct ddsi_sertype *sertype;
  dds_return_t ret = dds_get_entity_sertype (topic, &sertype);
  if (ret != DDS_RETCODE_OK)
    return NULL;
  const ddspy_sertype_t *pysertype = (const ddspy_sertype_t *) sertype;

  ddsrt_iovec_t sample_cdr;
  sample_cdr.iov_len = (ddsrt_iov_len_t)sample_data.len;
  sample_cdr.iov_base = (void *)sample_data.buf;

  ddsi_serdata_t *serdata = serdata_from_ser_iov (sertype, SDK_DATA, 1, &sample_cdr, sample_cdr.iov_len);
  if (!serdata)
    return NULL;

  ddspy_serdata_t *pyserdata = (ddspy_serdata_t *)serdata;
  PyBuffer_Release (&sample_data);

  // Extract key in correct CDR version (pyserdata->key is now always XCDR2)
  const uint32_t xcdr_version = pyserdata->is_v2 ? DDSI_RTPS_CDR_ENC_VERSION_2 : DDSI_RTPS_CDR_ENC_VERSION_1;
  dds_ostream_t os;
  dds_ostream_init (&os, &cdrstream_allocator, 0, xcdr_version);
  dds_istream_t is;
  dds_istream_init (&is, (uint32_t) pyserdata->data_size - 4, (char *) pyserdata->data + 4, xcdr_version);
  if (!dds_stream_extract_key_from_data (&is, &os, &cdrstream_allocator, &pysertype->cdrstream_desc))
  {
    ddsi_serdata_unref (serdata);
    return NULL;
  }

  uint32_t keysz = (uint32_t) os.m_index;
  unsigned char *keybuf = ddsrt_memdup ((char *) os.m_buffer, keysz);
  dds_ostream_fini (&os, &cdrstream_allocator);
  ddsi_serdata_unref (serdata);

  PyObject *returnv = Py_BuildValue ("y#", keybuf, keysz);
  return returnv;
}

/* builtin topic */

static PyObject *ddspy_readtake_participant (PyObject *self, PyObject *args, dds_return_t (*readtake) (dds_entity_t, void **, dds_sample_info_t *, size_t, uint32_t))
{
  uint32_t Nu32;
  long long N;
  dds_entity_t reader;
  dds_return_t sts;

  PyObject *participant_constructor;
  PyObject *cqos_to_qos;
  (void)self;

  if (!PyArg_ParseTuple (args, "iLOO", &reader, &N, &participant_constructor, &cqos_to_qos))
    return NULL;
  if (!(Nu32 = check_number_of_samples (N)))
    return NULL;

  dds_sample_info_t *info = dds_alloc (sizeof (*info) * Nu32);
  struct dds_builtintopic_participant **rcontainer = dds_alloc (sizeof (*rcontainer) * Nu32);

  for (uint32_t i = 0; i < Nu32; ++i)
    rcontainer[i] = NULL;

  sts = readtake (reader, (void **)rcontainer, info, Nu32, Nu32);
  if (sts < 0)
    return PyLong_FromLong ((long)sts);

  PyObject *list = PyList_New (sts);
  for (uint32_t i = 0; i < (uint32_t)sts; ++i)
  {
    PyObject *sampleinfo = get_sampleinfo_pyobject (&info[i]);
    if (PyErr_Occurred ())
      return NULL;
    PyObject *qos_p = PyLong_FromVoidPtr (rcontainer[i]->qos);
    if (PyErr_Occurred ())
      return NULL;
    PyObject *qos = PyObject_CallFunction (cqos_to_qos, "O", qos_p);
    if (PyErr_Occurred ())
      return NULL;
    PyObject *item = PyObject_CallFunction (participant_constructor, "y#OO", rcontainer[i]->key.v, (Py_ssize_t) 16, qos, sampleinfo);
    if (PyErr_Occurred ())
      return NULL;
    PyList_SetItem (list, i, item); // steals ref
    Py_DECREF (sampleinfo);
    Py_DECREF (qos_p);
    Py_DECREF (qos);
  }

  dds_return_loan (reader, (void **)rcontainer, sts);
  dds_free (info);
  dds_free (rcontainer);
  return list;
}

static PyObject *ddspy_read_participant (PyObject *self, PyObject *args)
{
  return ddspy_readtake_participant (self, args, dds_read);
}

static PyObject *ddspy_take_participant (PyObject *self, PyObject *args)
{
  return ddspy_readtake_participant (self, args, dds_take);
}

static PyObject *ddspy_construct_endpoint (struct dds_builtintopic_endpoint *endpoint, PyObject *sampleinfo, PyObject *endpoint_constructor, PyObject *cqos_to_qos)
{
  PyObject *type_id_bytes = NULL;

  dds_ostream_t type_obj_stream;
  const dds_typeinfo_t *type_info = NULL;

  // Fetch the type id
  dds_builtintopic_get_endpoint_type_info (endpoint, &type_info);

  // convert to cdr bytes
  if (type_info != NULL)
  {
    dds_ostream_init (&type_obj_stream, &cdrstream_allocator, 0, DDSI_RTPS_CDR_ENC_VERSION_2);
    const dds_typeid_t *type_id = ddsi_typeinfo_complete_typeid (type_info);
    typeid_ser (&type_obj_stream, type_id);
    type_id_bytes = Py_BuildValue ("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);
    dds_ostream_fini (&type_obj_stream, &cdrstream_allocator);
  }
  else
  {
    type_id_bytes = Py_None;
    Py_INCREF (type_id_bytes);
  }

  PyObject *qos_p, *qos;
  if (endpoint->qos != NULL)
  {
    qos_p = PyLong_FromVoidPtr (endpoint->qos);
    if (PyErr_Occurred ())
    {
      Py_DECREF (type_id_bytes);
      PyErr_Clear ();
      PyErr_SetString (PyExc_Exception, "VoidPtr errored.");
      return NULL;
    }
    qos = PyObject_CallFunction (cqos_to_qos, "O", qos_p);
    if (PyErr_Occurred ())
    {
      Py_DECREF (type_id_bytes);
      Py_DECREF (qos_p);
      PyErr_Clear ();
      PyErr_SetString (PyExc_Exception, "Callfunc cqos errored.");
      return NULL;
    }
  }
  else
  {
    Py_INCREF (Py_None);
    Py_INCREF (Py_None);
    qos_p = Py_None;
    qos = Py_None;
  }

  PyObject *item = PyObject_CallFunction (
          endpoint_constructor, "y#y#Ks#s#OOO",
          endpoint->key.v, (Py_ssize_t) 16,
          endpoint->participant_key.v, (Py_ssize_t) 16,
          endpoint->participant_instance_handle,
          endpoint->topic_name,
          endpoint->topic_name == NULL ? 0 : strlen(endpoint->topic_name),
          endpoint->type_name,
          endpoint->type_name == NULL ? 0 : strlen(endpoint->type_name),
          qos,
          sampleinfo,
          type_id_bytes);
  if (PyErr_Occurred ())
  {
    Py_DECREF (type_id_bytes);
    Py_DECREF (qos_p);
    Py_DECREF (qos);
    PyErr_Clear ();
    PyErr_SetString (PyExc_Exception, "Callfunc endpoint constructor errored.");
    return NULL;
  }

  Py_DECREF (type_id_bytes);
  Py_DECREF (qos_p);
  Py_DECREF (qos);
  return item;
}

static PyObject *ddspy_readtake_endpoint (PyObject *self, PyObject *args, dds_return_t (*readtake) (dds_entity_t, void **, dds_sample_info_t *, size_t, uint32_t))
{
  uint32_t Nu32;
  long long N;
  dds_entity_t reader;
  dds_return_t sts;

  PyObject *endpoint_constructor;
  PyObject *cqos_to_qos;
  (void)self;

  if (!PyArg_ParseTuple (args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
    return NULL;
  if (!(Nu32 = check_number_of_samples (N)))
    return NULL;

  dds_sample_info_t *info = dds_alloc (sizeof (*info) * Nu32);
  struct dds_builtintopic_endpoint **rcontainer = dds_alloc (sizeof (*rcontainer) * Nu32);

  for (uint32_t i = 0; i < Nu32; ++i)
    rcontainer[i] = NULL;

  sts = readtake (reader, (void **)rcontainer, info, Nu32, Nu32);
  if (sts < 0)
    return PyLong_FromLong ((long)sts);

  PyObject *list = PyList_New (sts);
  for (uint32_t i = 0; i < (uint32_t)sts; ++i)
  {
    PyObject *sampleinfo = get_sampleinfo_pyobject (&info[i]);
    if (PyErr_Occurred ())
    {
      PyErr_Clear ();
      PyErr_SetString (PyExc_Exception, "Sampleinfo errored.");
      return NULL;
    }

    PyObject *item = ddspy_construct_endpoint (rcontainer[i], sampleinfo, endpoint_constructor, cqos_to_qos);
    if (PyErr_Occurred ())
    {
      Py_DECREF (sampleinfo);
      PyErr_Clear ();
      PyErr_SetString (PyExc_Exception, "Callfunc endpoint constructor errored.");
      return NULL;
    }
    Py_DECREF (sampleinfo);

    PyList_SetItem (list, i, item); // steals ref
  }

  dds_return_loan (reader, (void **)rcontainer, sts);
  dds_free (info);
  dds_free (rcontainer);
  return list;
}

static PyObject *ddspy_read_endpoint (PyObject *self, PyObject *args)
{
  return ddspy_readtake_endpoint (self, args, dds_read);
}

static PyObject *ddspy_take_endpoint (PyObject *self, PyObject *args)
{
  return ddspy_readtake_endpoint (self, args, dds_take);
}

static PyObject *ddspy_readtake_topic (PyObject *self, PyObject *args, dds_return_t (*readtake) (dds_entity_t, void **, dds_sample_info_t *, size_t, uint32_t))
{
  uint32_t Nu32;
  long long N;
  dds_entity_t reader;
  dds_return_t sts;

  PyObject *endpoint_constructor;
  PyObject *cqos_to_qos;
  (void)self;

  if (!PyArg_ParseTuple (args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
    return NULL;
  if (!(Nu32 = check_number_of_samples (N)))
    return NULL;

  dds_sample_info_t *info = dds_alloc (sizeof (*info) * Nu32);
  struct dds_builtintopic_topic **rcontainer = dds_alloc (sizeof (*rcontainer) * Nu32);

  for (uint32_t i = 0; i < Nu32; ++i)
    rcontainer[i] = NULL;

  sts = readtake (reader, (void **)rcontainer, info, Nu32, Nu32);
  if (sts < 0)
    return PyLong_FromLong ((long)sts);

  PyObject *list = PyList_New (sts);
  for (uint32_t i = 0; i < (uint32_t)sts; ++i)
  {
    PyObject *type_id_bytes = NULL;

    dds_ostream_t type_obj_stream;
    const dds_typeinfo_t *type_info = NULL;

    // Fetch the type id
    // dds_builtintopic_get_endpoint_type_info (rcontainer[i], &type_info);
    if (rcontainer[i]->qos && rcontainer[i]->qos->present & DDSI_QP_TYPE_INFORMATION)
      type_info = rcontainer[i]->qos->type_information;

    // convert to cdr bytes
    if (type_info != NULL)
    {
      dds_ostream_init (&type_obj_stream, &cdrstream_allocator, 0, DDSI_RTPS_CDR_ENC_VERSION_2);
      const dds_typeid_t *type_id = ddsi_typeinfo_complete_typeid (type_info);
      typeid_ser (&type_obj_stream, type_id);
      type_id_bytes = Py_BuildValue ("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);
      dds_ostream_fini (&type_obj_stream, &cdrstream_allocator);
    }
    else
    {
      type_id_bytes = Py_None;
      Py_INCREF (type_id_bytes);
    }

    PyObject *sampleinfo = get_sampleinfo_pyobject (&info[i]);
    if (PyErr_Occurred ())
    {
      PyErr_Clear ();
      PyErr_SetString (PyExc_Exception, "Sampleinfo errored.");
      return NULL;
    }

    PyObject *qos_p, *qos;
    if (rcontainer[i]->qos != NULL)
    {
      qos_p = PyLong_FromVoidPtr (rcontainer[i]->qos);
      if (PyErr_Occurred ())
      {
        PyErr_Clear ();
        PyErr_SetString (PyExc_Exception, "VoidPtr errored.");
        return NULL;
      }
      qos = PyObject_CallFunction (cqos_to_qos, "O", qos_p);
      if (PyErr_Occurred ())
      {
        PyErr_Clear ();
        PyErr_SetString (PyExc_Exception, "Callfunc cqos errored.");
        return NULL;
      }
    }
    else
    {
      Py_INCREF (Py_None);
      Py_INCREF (Py_None);
      qos_p = Py_None;
      qos = Py_None;
    }

    PyObject *item = PyObject_CallFunction (
            endpoint_constructor, "y#s#s#OOO",
            rcontainer[i]->key.d, (Py_ssize_t) 16,
            rcontainer[i]->topic_name,
            rcontainer[i]->topic_name == NULL ? 0 : strlen(rcontainer[i]->topic_name),
            rcontainer[i]->type_name,
            rcontainer[i]->type_name == NULL ? 0 : strlen(rcontainer[i]->type_name),
            qos,
            sampleinfo,
            type_id_bytes);
    if (PyErr_Occurred ())
    {
      PyErr_Clear ();
      PyErr_SetString (PyExc_Exception, "Callfunc endpoint constructor errored.");
      return NULL;
    }
    PyList_SetItem (list, i, item); // steals ref
    Py_DECREF (sampleinfo);
    Py_DECREF (qos_p);
    Py_DECREF (qos);
  }

  dds_return_loan (reader, (void **)rcontainer, sts);
  dds_free (info);
  dds_free (rcontainer);
  return list;
}

static PyObject *ddspy_read_topic (PyObject *self, PyObject *args)
{
  return ddspy_readtake_topic (self, args, dds_read);
}

static PyObject *ddspy_take_topic (PyObject *self, PyObject *args)
{
  return ddspy_readtake_topic (self, args, dds_take);
}

/* end builtin topic */

#ifdef DDS_HAS_TYPE_DISCOVERY

static PyObject *ddspy_get_typeobj (PyObject *self, PyObject *args)
{
  dds_entity_t participant;
  Py_buffer type_id_buffer;
  dds_istream_t type_id_stream;
  dds_ostream_t type_obj_stream;
  dds_typeid_t *type_id = NULL;
  dds_typeobj_t *type_obj = NULL;
  dds_duration_t timeout;
  dds_return_t sts = DDS_RETCODE_ERROR;

  (void)self;

  if (!PyArg_ParseTuple (args, "iy*L", &participant, &type_id_buffer, &timeout))
    return NULL;

  type_id_stream.m_buffer = type_id_buffer.buf;
  type_id_stream.m_size = (uint32_t)type_id_buffer.len;
  type_id_stream.m_index = 0;
  type_id_stream.m_xcdr_version = DDSI_RTPS_CDR_ENC_VERSION_2;

  typeid_deser (&type_id_stream, &type_id);
  PyBuffer_Release (&type_id_buffer);

  if (type_id == NULL)
    return PyLong_FromLong (-1l);

  Py_BEGIN_ALLOW_THREADS
  sts = dds_get_typeobj (participant, type_id, timeout, &type_obj);
  Py_END_ALLOW_THREADS

  dds_free (type_id);

  if (sts < 0 || type_obj == NULL)
    return PyLong_FromLong ((long)sts);

  dds_ostream_init (&type_obj_stream, &cdrstream_allocator, 0, DDSI_RTPS_CDR_ENC_VERSION_2);
  typeobj_ser (&type_obj_stream, type_obj);
  dds_free_typeobj (type_obj);

  PyObject *typeobj_cdr = Py_BuildValue ("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);

  dds_ostream_fini (&type_obj_stream, &cdrstream_allocator);
  if (PyErr_Occurred () || typeobj_cdr == NULL)
    return NULL;
  return typeobj_cdr;
}

#endif

static PyObject *
ddspy_get_matched_subscription_data(PyObject *self, PyObject *args)
{
  dds_entity_t writer;
  dds_instance_handle_t handle;
  dds_builtintopic_endpoint_t* endpoint = NULL;

  PyObject* endpoint_constructor;
  PyObject* cqos_to_qos;
  (void)self;

  if (!PyArg_ParseTuple(args, "iKOO", &writer, &handle, &endpoint_constructor, &cqos_to_qos))
    return NULL;

  endpoint = dds_get_matched_subscription_data(writer, handle);
  if (endpoint == NULL) {
    Py_INCREF(Py_None);
    return Py_None;
  }

  PyObject *item = ddspy_construct_endpoint (endpoint, Py_None, endpoint_constructor, cqos_to_qos);
  dds_builtintopic_free_endpoint(endpoint);
  return item;
}


static PyObject *
ddspy_get_matched_publication_data(PyObject *self, PyObject *args)
{
  dds_entity_t reader;
  dds_instance_handle_t handle;
  dds_builtintopic_endpoint_t* endpoint = NULL;

  PyObject* endpoint_constructor;
  PyObject* cqos_to_qos;
  (void)self;

  if (!PyArg_ParseTuple(args, "iKOO", &reader, &handle, &endpoint_constructor, &cqos_to_qos))
    return NULL;

  endpoint = dds_get_matched_publication_data(reader, handle);
  if (endpoint == NULL) {
    Py_INCREF(Py_None);
    return Py_None;
  }

  PyObject *item = ddspy_construct_endpoint (endpoint, Py_None, endpoint_constructor, cqos_to_qos);
  dds_builtintopic_free_endpoint(endpoint);
  return item;
}


char ddspy_docs[] = "DDSPY module";

PyMethodDef ddspy_funcs[] = {
  { "ddspy_calc_key", (PyCFunction)ddspy_calc_key, METH_VARARGS, ddspy_docs },
  { "ddspy_topic_create", (PyCFunction)ddspy_topic_create, METH_VARARGS, ddspy_docs },
  { "ddspy_read", (PyCFunction)ddspy_read, METH_VARARGS, ddspy_docs },
  { "ddspy_take", (PyCFunction)ddspy_take, METH_VARARGS, ddspy_docs },
  { "ddspy_read_handle", (PyCFunction)ddspy_read_handle, METH_VARARGS, ddspy_docs },
  { "ddspy_take_handle", (PyCFunction)ddspy_take_handle, METH_VARARGS, ddspy_docs },
  { "ddspy_write", (PyCFunction)ddspy_write, METH_VARARGS, ddspy_docs },
  { "ddspy_write_ts", (PyCFunction)ddspy_write_ts, METH_VARARGS, ddspy_docs },
  { "ddspy_writedispose", (PyCFunction)ddspy_writedispose, METH_VARARGS, ddspy_docs },
  { "ddspy_writedispose_ts", (PyCFunction)ddspy_writedispose_ts, METH_VARARGS, ddspy_docs },
  { "ddspy_dispose", (PyCFunction)ddspy_dispose, METH_VARARGS, ddspy_docs },
  { "ddspy_dispose_ts", (PyCFunction)ddspy_dispose_ts, METH_VARARGS, ddspy_docs },
  { "ddspy_dispose_handle", (PyCFunction)ddspy_dispose_handle, METH_VARARGS, ddspy_docs },
  { "ddspy_dispose_handle_ts", (PyCFunction)ddspy_dispose_handle_ts, METH_VARARGS, ddspy_docs },
  { "ddspy_register_instance", (PyCFunction)ddspy_register_instance, METH_VARARGS, ddspy_docs },
  { "ddspy_unregister_instance", (PyCFunction)ddspy_unregister_instance, METH_VARARGS, ddspy_docs },
  { "ddspy_unregister_instance_handle", (PyCFunction)ddspy_unregister_instance_handle, METH_VARARGS, ddspy_docs },
  { "ddspy_unregister_instance_ts", (PyCFunction)ddspy_unregister_instance_ts, METH_VARARGS, ddspy_docs },
  { "ddspy_unregister_instance_handle_ts", (PyCFunction)ddspy_unregister_instance_handle_ts, METH_VARARGS, ddspy_docs },
  { "ddspy_lookup_instance", (PyCFunction)ddspy_lookup_instance, METH_VARARGS, ddspy_docs },
  { "ddspy_read_next", (PyCFunction)ddspy_read_next, METH_VARARGS, ddspy_docs },
  { "ddspy_take_next", (PyCFunction)ddspy_take_next, METH_VARARGS, ddspy_docs },
  { "ddspy_read_participant", (PyCFunction)ddspy_read_participant, METH_VARARGS, ddspy_docs },
  { "ddspy_take_participant", (PyCFunction)ddspy_take_participant, METH_VARARGS, ddspy_docs },
  { "ddspy_read_endpoint", (PyCFunction)ddspy_read_endpoint, METH_VARARGS, ddspy_docs },
  { "ddspy_take_endpoint", (PyCFunction)ddspy_take_endpoint, METH_VARARGS, ddspy_docs },
  { "ddspy_read_topic", (PyCFunction)ddspy_read_topic, METH_VARARGS, ddspy_docs },
  { "ddspy_take_topic", (PyCFunction)ddspy_take_topic, METH_VARARGS, ddspy_docs },
#ifdef DDS_HAS_TYPE_DISCOVERY
  { "ddspy_get_typeobj", (PyCFunction)ddspy_get_typeobj, METH_VARARGS, ddspy_docs },
#endif
  { "ddspy_get_matched_subscription_data", (PyCFunction)ddspy_get_matched_subscription_data, METH_VARARGS, ddspy_docs },
  { "ddspy_get_matched_publication_data", (PyCFunction)ddspy_get_matched_publication_data, METH_VARARGS, ddspy_docs },
  { NULL }
};

char ddspymod_docs[] = "This is the CycloneDDS internal C module.";

PyModuleDef _clayer_mod = {
  PyModuleDef_HEAD_INIT,
  "cyclonedds._clayer",
  ddspymod_docs,
  -1,
  ddspy_funcs,
  NULL,
  NULL,
  NULL,
  NULL
};

PyMODINIT_FUNC PyInit__clayer (void)
{
  PyObject *import = PyImport_ImportModule ("cyclonedds.internal");

  if (PyErr_Occurred ())
    return NULL;
  if (import == NULL)
  {
    PyObject *msg = PyUnicode_FromString ("Failed to import cyclonedds.internal to get SampleInfo cls.");
    PyObject *name = PyUnicode_FromString ("cyclonedds.internal");
    PyObject *path = PyUnicode_FromString ("cyclonedds.internal");
    PyErr_SetImportError (msg, name, path);
    Py_DECREF (msg);
    Py_DECREF (name);
    Py_DECREF (path);
    return NULL;
  }

  sampleinfo_descriptor = PyObject_GetAttrString (import, "SampleInfo");

  if (PyErr_Occurred ())
    return NULL;
  if (sampleinfo_descriptor == NULL)
  {
    PyObject *msg = PyUnicode_FromString ("Failed to import cyclonedds.internal to get SampleInfo cls.");
    PyObject *name = PyUnicode_FromString ("cyclonedds.internal");
    PyObject *path = PyUnicode_FromString ("cyclonedds.internal");
    PyErr_SetImportError (msg, name, path);
    Py_DECREF (msg);
    Py_DECREF (name);
    Py_DECREF (path);
    return NULL;
  }
  Py_DECREF (import);

  PyObject *module = PyModule_Create (&_clayer_mod);

  PyModule_AddObject (module, "DDS_INFINITY", PyLong_FromLongLong (DDS_INFINITY));
  PyModule_AddObject (module, "UINT32_MAX", PyLong_FromUnsignedLong (UINT32_MAX));
  PyModule_AddObject (module, "DDS_DOMAIN_DEFAULT", PyLong_FromUnsignedLong (DDS_DOMAIN_DEFAULT));
#ifdef DDS_HAS_TYPELIB
  Py_INCREF (Py_True);
  PyModule_AddObject (module, "HAS_TYPELIB", Py_True);
#else
  Py_INCREF (Py_False);
  PyModule_AddObject (module, "HAS_TYPELIB", Py_False);
#endif
#ifdef DDS_HAS_TYPE_DISCOVERY
  Py_INCREF (Py_True);
  PyModule_AddObject (module, "HAS_TYPE_DISCOVERY", Py_True);
#else
  Py_INCREF (Py_False);
  PyModule_AddObject (module, "HAS_TYPE_DISCOVERY", Py_False);
#endif
#ifdef DDS_HAS_TOPIC_DISCOVERY
  Py_INCREF (Py_True);
  PyModule_AddObject (module, "HAS_TOPIC_DISCOVERY", Py_True);
#else
  Py_INCREF (Py_False);
  PyModule_AddObject (module, "HAS_TOPIC_DISCOVERY", Py_False);
#endif
  return module;
}
