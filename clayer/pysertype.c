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
#include "dds/ddsi/q_radmin.h"
#include "dds/ddsi/ddsi_serdata.h"
#include "dds/ddsi/ddsi_sertype.h"
#include "dds/ddsi/ddsi_typelib.h"
#include "dds/cdr/dds_cdrstream.h"


#include "cdrkeyvm.h"
#include "pysertype.h"
#ifdef DDS_HAS_TYPE_DISCOVERY
#include "typeser.h"
#endif

static cdr_key_vm_op* make_vm_ops_from_py_op_list(PyObject* list)
{
    Py_ssize_t len = PyList_Size(list);
    if (len < 0 || PyErr_Occurred())
        return NULL;

    cdr_key_vm_op* ops = (cdr_key_vm_op*) dds_alloc(sizeof(struct cdr_key_vm_op_s) * ((size_t)len + 1));
    if (ops == NULL)
        return NULL;
    ops[len].type = CdrKeyVMOpDone;

    for (Py_ssize_t i = 0; i < len; ++i) {
        PyObject* borrow_i = PyList_GetItem(list, i);
        PyObject* attr_type = PyObject_GetAttrString(borrow_i, "type");
        PyObject* int_attr_type = PyNumber_Long(attr_type);
        PyObject* attr_skip = PyObject_GetAttrString(borrow_i, "skip");
        PyObject* attr_size = PyObject_GetAttrString(borrow_i, "size");
        PyObject* attr_align = PyObject_GetAttrString(borrow_i, "align");
        PyObject* attr_value = PyObject_GetAttrString(borrow_i, "value");

        ops[i].type = (cdr_key_vm_op_type) PyLong_AsUnsignedLong(int_attr_type);
        ops[i].skip = attr_skip == Py_True;
        ops[i].size = (uint32_t) PyLong_AsUnsignedLong(attr_size);
        ops[i].align = (uint8_t) PyLong_AsUnsignedLong(attr_align);
        ops[i].value = (uint64_t) PyLong_AsUnsignedLongLong(attr_value);

        Py_DECREF(attr_type);
        Py_DECREF(int_attr_type);
        Py_DECREF(attr_skip);
        Py_DECREF(attr_size);
        Py_DECREF(attr_align);
        Py_DECREF(attr_value);
    }

    for (Py_ssize_t i = len; i > 0; --i) {
        if (ops[i-1].skip) {
            ops[i-1].type = CdrKeyVMOpDone;
        } else {
            break;
        }
    }

    return ops;
}

static cdr_key_vm* make_key_vm(PyObject* idl, bool v2)
{
    PyObject* attr_keymachine = PyObject_GetAttrString(idl, "cdr_key_machine");

    if (attr_keymachine == NULL) return NULL;

    PyObject* args = PyTuple_New(2);
    Py_INCREF(Py_False);
    Py_INCREF(v2 ? Py_True : Py_False);
    PyTuple_SetItem(args, 0, Py_False);
    PyTuple_SetItem(args, 1, v2 ? Py_True : Py_False);
    PyObject* list = PyObject_CallObject(attr_keymachine, args);
    Py_DECREF(attr_keymachine);
    Py_DECREF(args);

    if (list == NULL) return NULL;
    cdr_key_vm* vm = (cdr_key_vm*) dds_alloc(sizeof(struct cdr_key_vm_s));
    if (vm == NULL) {
        Py_DECREF(list);
        return NULL;
    }

    vm->instructions = make_vm_ops_from_py_op_list(list);
    vm->final_size_is_static = false;
    vm->initial_alloc_size = 128;

    Py_DECREF(list);

    return vm;
}

typedef struct ddsi_serdata ddsi_serdata_t;
typedef struct ddsi_sertype ddsi_sertype_t;


// Python refcount: one ref for each PyObject*.
typedef struct ddspy_sertype {
    ddsi_sertype_t my_c_type;
    PyObject* my_py_type;
    bool keyless;
    bool is_v2_by_default;

    cdr_key_vm* v0_key_vm;
    bool v0_key_maxsize_bigger_16;
    cdr_key_vm* v2_key_vm;
    bool v2_key_maxsize_bigger_16;

    // xtypes
#ifdef DDS_HAS_TYPE_DISCOVERY
    unsigned char * typeinfo_ser_data;
    uint32_t typeinfo_ser_sz;
    unsigned char * typemap_ser_data;
    uint32_t typemap_ser_sz;
#endif

} ddspy_sertype_t;

// Python refcount: one ref for sample.
typedef struct ddspy_serdata {
    ddsi_serdata_t c_data;
    void* data;
    size_t data_size;
    void* key;
    size_t key_size;
    ddsi_keyhash_t hash;
    bool key_populated;
    bool data_is_key;
    bool is_v2;
} ddspy_serdata_t;

// Python refcount: one ref for sample.
typedef struct ddspy_sample_container {
    void* usample;
    size_t usample_size;
} ddspy_sample_container_t;


static inline ddspy_sertype_t* sertype(ddspy_serdata_t *this)
{
    return (ddspy_sertype_t*) (this->c_data.type);
}

static inline const ddspy_sertype_t* csertype(const ddspy_serdata_t *this)
{
    return (const ddspy_sertype_t*) (this->c_data.type);
}

static inline ddspy_serdata_t* serdata(ddsi_serdata_t *this)
{
    return (ddspy_serdata_t*) (this);
}

static inline const ddspy_serdata_t* cserdata(const ddsi_serdata_t *this)
{
    return (const ddspy_serdata_t*) (this);
}

static ddspy_serdata_t *ddspy_serdata_new(const struct ddsi_sertype* type, enum ddsi_serdata_kind kind, size_t data_size)
{
    ddspy_serdata_t *new = (ddspy_serdata_t*) dds_alloc(sizeof(struct ddspy_serdata));
    ddsi_serdata_init((ddsi_serdata_t*) new, type, kind);

    new->data = dds_alloc(data_size);
    new->data_size = data_size;
    new->key = NULL;
    new->key_size = 0;
    new->key_populated = false;
    new->data_is_key = false;
    new->is_v2 = ((ddspy_sertype_t*)type)->is_v2_by_default;
    memset((unsigned char*) &(new->hash), 0, 16);

    return new;
}

static void ddspy_serdata_calc_hash(ddspy_serdata_t* this)
{
    if (this->is_v2) {
        if (csertype(this)->v2_key_maxsize_bigger_16) {
            ddsrt_md5_state_t md5st;
            ddsrt_md5_init(&md5st);
            ddsrt_md5_append(&md5st, (void*)(((char*)this->key) + 4), (unsigned int)this->key_size - 4);
            ddsrt_md5_finish(&md5st, this->hash.value);
        } else {
            assert(this->key_size <= 20);
            memset(this->hash.value, 0, 16);
            memcpy(this->hash.value, ((char*)this->key) + 4, this->key_size - 4);
        }
        this->c_data.hash = ddsrt_mh3(this->key, this->key_size, 0) ^ this->c_data.type->serdata_basehash;
    } else {
        if (csertype(this)->v0_key_maxsize_bigger_16) {
            ddsrt_md5_state_t md5st;
            ddsrt_md5_init(&md5st);
            ddsrt_md5_append(&md5st, (void*)(((char*)this->key) + 4), (unsigned int)this->key_size - 4);
            ddsrt_md5_finish(&md5st, this->hash.value);
        } else {
            assert(this->key_size <= 20);
            memset(this->hash.value, 0, 16);
            memcpy(this->hash.value, ((char*)this->key) + 4, this->key_size - 4);
        }
        this->c_data.hash = ddsrt_mh3(this->key, this->key_size, 0) ^ this->c_data.type->serdata_basehash;
    }
}


static void ddspy_serdata_populate_key(ddspy_serdata_t* this)
{
    if (sertype(this)->keyless) {
        this->key = dds_alloc(20);
        this->key_size = 20;
        memset(this->key, 0, 20);
        memset(this->hash.value, 0, 16);
        this->key_populated = true;
        return;
    }

    cdr_key_vm_runner* runner = cdr_key_vm_create_runner(
        this->is_v2 ? csertype(this)->v2_key_vm : csertype(this)->v0_key_vm
    );
    this->key_size = cdr_key_vm_run(runner, this->data, this->data_size);
    if (this->key_size < 20) this->key_size = 20;

    this->key = runner->header;
    this->key_populated = true;

    dds_free(runner);

    ddspy_serdata_calc_hash(this);
}


static bool serdata_eqkey(const struct ddsi_serdata* a, const struct ddsi_serdata* b)
{
    const ddspy_serdata_t *apy = cserdata(a), *bpy = cserdata(b);
    if (csertype(apy)->keyless ^ csertype(bpy)->keyless) {
        return false;
    }
    if (csertype(apy)->keyless && csertype(bpy)->keyless) {
        return true;
    }

    assert(cserdata(a)->key != NULL);
    assert(cserdata(b)->key != NULL);
    if (cserdata(a)->key_size != cserdata(b)->key_size) return false;
    return 0 == memcmp(cserdata(a)->key, cserdata(b)->key, cserdata(a)->key_size);
}

static uint32_t serdata_size(const struct ddsi_serdata* dcmn)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    if (dcmn->kind == SDK_KEY) {
        return (uint32_t) cserdata(dcmn)->key_size;
    }
    return (uint32_t) cserdata(dcmn)->data_size;
}

static ddsi_serdata_t *serdata_from_ser(
  const struct ddsi_sertype* type,
  enum ddsi_serdata_kind kind,
  const struct nn_rdata* fragchain, size_t size)
{
    ddspy_serdata_t *d = ddspy_serdata_new(type, kind, size);

    uint32_t off = 0;
    assert(fragchain->min == 0);
    assert(fragchain->maxp1 >= off);    //CDR header must be in first fragment

    unsigned char* cursor = d->data;
    while (fragchain) {
        if (fragchain->maxp1 > off) {
            //only copy if this fragment adds data
            const unsigned char* payload =
                NN_RMSG_PAYLOADOFF(fragchain->rmsg, NN_RDATA_PAYLOAD_OFF(fragchain));
            const unsigned char* src = payload + off - fragchain->min;
            size_t n_bytes = fragchain->maxp1 - off;
            memcpy(cursor, src, n_bytes);
            cursor += n_bytes;
            off = fragchain->maxp1;
            assert(off <= size);
        }
        fragchain = fragchain->nextfrag;
    }

    d->is_v2 = ((char*)d->data)[1] > 1;

    switch (kind)
    {
    case SDK_KEY:
        d->data_is_key = true;
        d->key = d->data;
        d->key_size = d->data_size;
        break;
    case SDK_DATA:
        ddspy_serdata_populate_key(d);
        break;
    case SDK_EMPTY:
        assert(0);
    }

    assert(d->key != NULL);
    assert(d->data != NULL);
    assert(d->data_size != 0);
    assert(d->key_size >= 20);

    return (ddsi_serdata_t*) d;
}

static ddsi_serdata_t *serdata_from_ser_iov(
  const struct ddsi_sertype* type,
  enum ddsi_serdata_kind kind,
  ddsrt_msg_iovlen_t niov,
  const ddsrt_iovec_t* iov,
  size_t size)
{
    ddspy_serdata_t *d = ddspy_serdata_new(type, kind, size);

    size_t off = 0;
    unsigned char* cursor = d->data;
    for (ddsrt_msg_iovlen_t i = 0; i < niov && off < size; i++)
    {
        size_t n_bytes = iov[i].iov_len;
        if (n_bytes + off > size) n_bytes = size - off;
        memcpy(cursor, iov[i].iov_base, n_bytes);
        cursor += n_bytes;
        off += n_bytes;
    }

    d->is_v2 = ((char*)d->data)[1] > 1;

    switch (kind)
    {
    case SDK_KEY:
        d->data_is_key = true;
        d->key = d->data;
        d->key_size = d->data_size;
        break;
    case SDK_DATA:
        ddspy_serdata_populate_key(d);
        break;
    case SDK_EMPTY:
        assert(0);
    }

    assert(d->key != NULL);
    assert(d->data != NULL);
    assert(d->data_size != 0);
    assert(d->key_size >= 20);

    return (ddsi_serdata_t*) d;
}

static ddsi_serdata_t *serdata_from_keyhash(
  const struct ddsi_sertype* topic,
  const struct ddsi_keyhash* keyhash)
{
  (void)keyhash;
  (void)topic;
  //replace with (if key_size_max <= 16) then populate the data class with the key hash (key_read)
  // TODO
  assert(0);
  return NULL;
}


static ddsi_serdata_t *serdata_from_sample(
  const ddsi_sertype_t* type,
  enum ddsi_serdata_kind kind,
  const void* sample)
{
    ddspy_sample_container_t *container = (ddspy_sample_container_t*) sample;

    ddspy_serdata_t* d = ddspy_serdata_new(type, kind, container->usample_size);
    memcpy((char*) d->data, container->usample, container->usample_size);

    d->is_v2 = ((char*)d->data)[1] > 1;
    ddspy_serdata_populate_key(d);

    assert(d->key != NULL);
    assert(d->data != NULL);
    assert(d->data_size != 0);
    assert(d->key_size >= 20);

    return (ddsi_serdata_t*) d;
}

static void serdata_to_ser(const ddsi_serdata_t* dcmn, size_t off, size_t sz, void* buf)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 20);
    if (dcmn->kind == SDK_KEY) {
        memcpy(buf, (char*) cserdata(dcmn)->key + off, sz);
    }
    else {
        memcpy(buf, (char*) cserdata(dcmn)->data + off, sz);
    }
}

static ddsi_serdata_t *serdata_to_ser_ref(
  const struct ddsi_serdata* dcmn, size_t off,
  size_t sz, ddsrt_iovec_t* ref)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 20);

    if (dcmn->kind == SDK_KEY) {
        ref->iov_base = (char*) cserdata(dcmn)->key + off;
        ref->iov_len = (ddsrt_iov_len_t)sz;
    }
    else {
        ref->iov_base = (char*) cserdata(dcmn)->data + off;
        ref->iov_len = (ddsrt_iov_len_t)sz;
    }
    return ddsi_serdata_ref(dcmn);
}

static void serdata_to_ser_unref(struct ddsi_serdata* dcmn, const ddsrt_iovec_t* ref)
{
    (void)ref;    // unused
    ddsi_serdata_unref(dcmn);
}

static bool serdata_to_sample(
  const ddsi_serdata_t* dcmn, void* sample, void** bufptr,
  void* buflim)
{
    (void)bufptr;
    (void)buflim;
    ddspy_sample_container_t *container = (ddspy_sample_container_t*) sample;

    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 20);
    assert(container->usample == NULL);

    container->usample = dds_alloc(cserdata(dcmn)->data_size);
    memcpy(container->usample, cserdata(dcmn)->data, cserdata(dcmn)->data_size);
    container->usample_size = cserdata(dcmn)->data_size;

    return true;
}

static ddsi_serdata_t *serdata_to_typeless(const ddsi_serdata_t* dcmn)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 20);

    if (dcmn->kind == SDK_KEY) {
        return ddsi_serdata_ref(dcmn);
    } else {
        const ddspy_serdata_t *d = cserdata(dcmn);
        ddspy_serdata_t* d_tl = (ddspy_serdata_t*) dds_alloc(sizeof(struct ddspy_serdata));
        assert(d_tl);
        ddsi_serdata_init((ddsi_serdata_t*) d_tl, dcmn->type, SDK_KEY);
        d_tl->data = ddsrt_memdup(d->key, d->key_size);
        d_tl->key = d_tl->data;
        d_tl->data_size = d->key_size;
        d_tl->key_size = d->key_size;
        d_tl->key_populated = true;
        d_tl->data_is_key = true;
        d_tl->is_v2 = false;
        d_tl->c_data.hash = d->c_data.hash;
        d_tl->hash = d->hash;
        return (struct ddsi_serdata *)d_tl;
    }
}

static bool serdata_typeless_to_sample(
  const struct ddsi_sertype* type,
  const struct ddsi_serdata* dcmn, void* sample,
  void** buf,
  void* buflim)
{
    ddspy_sample_container_t* container = (ddspy_sample_container_t*) sample;
    (void)type;
    (void)buf;
    (void)buflim;

    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 20);
    assert(container->usample == NULL);

    container->usample = dds_alloc(cserdata(dcmn)->data_size);
    container->usample_size = cserdata(dcmn)->data_size;

    memcpy(container->usample, cserdata(dcmn)->data, container->usample_size);

    return true;
}

static void serdata_free(struct ddsi_serdata* dcmn)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 20);

    dds_free(serdata(dcmn)->data);
    if (!serdata(dcmn)->data_is_key)
        dds_free(serdata(dcmn)->key);
    dds_free(dcmn);
}

static size_t serdata_print(const struct ddsi_sertype* tpcmn, const struct ddsi_serdata* dcmn, char* buf, size_t bufsize)
{
    (void)tpcmn;
    (void)dcmn;
    (void)buf;
    (void)bufsize;
    return 0;
}

static void serdata_get_keyhash(const ddsi_serdata_t* d, struct ddsi_keyhash* buf, bool force_md5)
{
    assert(cserdata(d)->key != NULL);
    assert(cserdata(d)->data != NULL);
    assert(cserdata(d)->data_size != 0);
    assert(cserdata(d)->key_size >= 20);
    assert(d->type != NULL);

    if (csertype(cserdata(d))->keyless) {
        memset(buf->value, 0, 16);
        return;
    }

    if (force_md5 && !(
        cserdata(d)->is_v2 ?
            ((const ddspy_sertype_t*) d->type)->v2_key_maxsize_bigger_16 :
            ((const ddspy_sertype_t*) d->type)->v0_key_maxsize_bigger_16
    ))
    {
        ddsrt_md5_state_t md5st;
        ddsrt_md5_init(&md5st);
        ddsrt_md5_append(&md5st, cserdata(d)->hash.value, 16);
        ddsrt_md5_finish(&md5st, buf->value);
    }
    else
    {
        memcpy(buf->value, cserdata(d)->hash.value, 16);
    }
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


static void sertype_free(struct ddsi_sertype* tpcmn)
{
    struct ddspy_sertype* this = (struct ddspy_sertype*) tpcmn;
    if (this->v0_key_vm != NULL) {
        dds_free(this->v0_key_vm->instructions);
        dds_free(this->v0_key_vm);
    }
    if (this->v2_key_vm != NULL) {
        dds_free(this->v2_key_vm->instructions);
        dds_free(this->v2_key_vm);
    }
#ifdef DDS_HAS_TYPE_DISCOVERY
    if (this->typeinfo_ser_sz) {
        dds_free(this->typeinfo_ser_data);
    }
    if (this->typemap_ser_sz) {
        dds_free(this->typemap_ser_data);
    }
#endif

    // dds_free the python type if python isn't already shutting down (deadlock).
#if PY_MINOR_VERSION > 6
    if (!_Py_IsFinalizing()) {
        PyGILState_STATE state = PyGILState_Ensure();
        Py_DECREF(this->my_py_type);
        PyGILState_Release(state);
    }
#else
    if (PyGILState_GetThisThreadState() != _Py_Finalizing) {
        PyGILState_STATE state = PyGILState_Ensure();
        Py_DECREF(this->my_py_type);
        PyGILState_Release(state);
    }
#endif
    ddsi_sertype_fini(tpcmn);
    dds_free(this);
}

static void sertype_zero_samples(const struct ddsi_sertype *sertype_common, void *samples, size_t count)
{
    (void)sertype_common;
    memset(samples, 0, sizeof(ddspy_sample_container_t) * count);
}

static void sertype_realloc_samples(void **ptrs, const struct ddsi_sertype *sertype_common, void *old, size_t oldcount, size_t count)
{
    (void)sertype_common;
    char *new = (oldcount == count) ? old : dds_realloc (old, sizeof(ddspy_sample_container_t) * count);
    if (new && count > oldcount)
        memset (new + sizeof(ddspy_sample_container_t) * oldcount, 0, sizeof(ddspy_sample_container_t) * (count - oldcount));

    for (size_t i = 0; i < count; i++)
    {
        void *ptr = (char *) new + i * sizeof(ddspy_sample_container_t);
        ptrs[i] = ptr;
    }
}

static void sertype_free_samples(const struct ddsi_sertype *sertype_common, void **ptrs, size_t count, dds_free_op_t op)
{
    (void)sertype_common;
    if (count > 0)
    {
        if (op & DDS_FREE_CONTENTS_BIT)
        {
            if (((ddspy_sample_container_t*) ptrs[0])->usample != NULL)
                dds_free(((ddspy_sample_container_t*) ptrs[0])->usample);
        }

        if (op & DDS_FREE_ALL_BIT)
        {
            dds_free (ptrs[0]);
        }
    }
}

static bool sertype_equal(const ddsi_sertype_t* acmn, const ddsi_sertype_t* bcmn)
{
    /// Sertypes are equal if:
    ///    1: they point to the same point in memory (trivial)
    ///    1: they point to the same python object
    ///    2: the python objects they point to contain the same type info

    const ddspy_sertype_t *A = (const ddspy_sertype_t*) acmn;
    const ddspy_sertype_t *B = (const ddspy_sertype_t*) bcmn;

    if (A == B)
        return true;

    if (A->my_py_type == NULL || B->my_py_type == NULL) // should never be true
        return false;

    if (A->my_py_type == B->my_py_type)
        return true;

    // Expensive stuff coming up here
    PyGILState_STATE state = PyGILState_Ensure();
    int result = PyObject_RichCompareBool(A->my_py_type, B->my_py_type, Py_EQ);
    PyGILState_Release(state);

    return result == 1;
}

static uint32_t sertype_hash(const struct ddsi_sertype* tpcmn)
{
  (void)tpcmn;
  return 0x0u;
}

static ddsi_typeid_t* sertype_typeid (const struct ddsi_sertype *tpcmn, ddsi_typeid_kind_t kind)
{
#ifdef DDS_HAS_TYPE_DISCOVERY
  assert (tpcmn);
  assert (kind == DDSI_TYPEID_KIND_MINIMAL || kind == DDSI_TYPEID_KIND_COMPLETE);

  const struct ddspy_sertype *type = (struct ddspy_sertype *) tpcmn;
  ddsi_typeinfo_t *type_info = ddsi_typeinfo_deser (type->typeinfo_ser_data, type->typeinfo_ser_sz);
  if (type_info == NULL)
    return NULL;
  ddsi_typeid_t *type_id = ddsi_typeinfo_typeid (type_info, kind);
  ddsi_typeinfo_fini (type_info);
  ddsrt_free (type_info);
  return type_id;
#else
  DDSRT_UNUSED_ARG (tpcmn);
  DDSRT_UNUSED_ARG (kind);
  return NULL;
#endif
}

static ddsi_typemap_t * sertype_typemap (const struct ddsi_sertype *tpcmn)
{
#ifdef DDS_HAS_TYPE_DISCOVERY
  assert (tpcmn);
  const struct ddspy_sertype *type = (struct ddspy_sertype *) tpcmn;
  return ddsi_typemap_deser (type->typemap_ser_data, type->typemap_ser_sz);
#else
  DDSRT_UNUSED_ARG (tpcmn);
  return NULL;
#endif
}

static ddsi_typeinfo_t *sertype_typeinfo (const struct ddsi_sertype *tpcmn)
{
#ifdef DDS_HAS_TYPE_DISCOVERY
  assert (tpcmn);
  const struct ddspy_sertype *type = (struct ddspy_sertype *) tpcmn;
  return ddsi_typeinfo_deser (type->typeinfo_ser_data, type->typeinfo_ser_sz);
#else
  DDSRT_UNUSED_ARG (tpcmn);
  return NULL;
#endif
}

static struct ddsi_sertype * sertype_derive_sertype (const struct ddsi_sertype *base_sertype, dds_data_representation_id_t repr, dds_type_consistency_enforcement_qospolicy_t tceqos)
{
    // The python sertype can handle all types by itself, no derives needed
    DDSRT_UNUSED_ARG (repr);
    DDSRT_UNUSED_ARG (tceqos);
    return (struct ddsi_sertype *) base_sertype;
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


static bool valid_py_allow_none_or_set_error(PyObject *py_obj)
{
    if (PyErr_Occurred()) return false;
    if (py_obj != NULL) return true;

    PyErr_SetString(PyExc_TypeError, "Invalid python object.");
    return false;
}

static bool valid_topic_py_or_set_error(PyObject *py_obj)
{
    if (PyErr_Occurred()) return false;
    if (py_obj != NULL && py_obj != Py_None) return true;

    PyErr_SetString(PyExc_TypeError, "Invalid python object used as topic datatype.");
    return false;
}

static bool valid_pt_or_set_error(void *py_obj)
{
    if (PyErr_Occurred()) return false;
    if (py_obj != NULL) return true;

    PyErr_SetString(PyExc_TypeError, "Invalid c object created.");
    return false;
}


static ddspy_sertype_t *ddspy_sertype_new(PyObject *pytype)
{
    // PyObjects
    PyObject *idl = NULL, *pyname = NULL, *pykeyless = NULL, *pyversion_support = NULL, *v0pykeysize = NULL, *v2pykeysize = NULL;
#ifdef DDS_HAS_TYPE_DISCOVERY
    PyObject *xt_type_data = NULL;
    Py_buffer xt_type_map_bytes, xt_type_info_bytes;
#endif
    ddspy_sertype_t *new = NULL;
    bool constructed = false;

    assert(pytype);

    // process
    idl = PyObject_GetAttrString(pytype, "__idl__");
    if (!valid_topic_py_or_set_error(idl)) goto err;

    pyname = PyObject_GetAttrString(idl, "idl_transformed_typename");
    if (!valid_topic_py_or_set_error(pyname)) goto err;

    pykeyless = PyObject_GetAttrString(idl, "keyless");
    if (!valid_topic_py_or_set_error(pykeyless)) goto err;

    pyversion_support = PyObject_GetAttrString(idl, "version_support");
    if (!valid_topic_py_or_set_error(pyversion_support)) goto err;

#ifdef DDS_HAS_TYPE_DISCOVERY
    xt_type_data = PyObject_GetAttrString(idl, "_xt_bytedata");
    if (!valid_py_allow_none_or_set_error(xt_type_data)) goto err;
#endif

    const char *name = PyUnicode_AsUTF8(pyname);
    if (name == NULL) goto err;

    bool keyless = pykeyless == Py_True;

    new = (ddspy_sertype_t*) dds_alloc(sizeof(ddspy_sertype_t));

    Py_INCREF(pytype);
    new->my_py_type = pytype;
    new->keyless = keyless;
    new->is_v2_by_default = PyLong_AsLong(pyversion_support) == 2; // XCDRSupported.SupportsBasic = 1, SupportsV2 = 2

#ifdef DDS_HAS_TYPE_DISCOVERY
    if (xt_type_data != Py_None && PyTuple_GetItem(xt_type_data, 0) != Py_None) {
        if (!PyArg_ParseTuple(xt_type_data, "y*y*", &xt_type_info_bytes, &xt_type_map_bytes))
            goto err;

        new->typemap_ser_data = (unsigned char*) dds_alloc((size_t) xt_type_map_bytes.len);

        if (new->typemap_ser_data == NULL) {
            PyBuffer_Release(&xt_type_map_bytes);
            PyBuffer_Release(&xt_type_info_bytes);
            Py_XDECREF(xt_type_data);
            goto err;
        }

        new->typeinfo_ser_data = (unsigned char*) dds_alloc((size_t)xt_type_info_bytes.len);

        if (new->typeinfo_ser_data == NULL) {
            dds_free(new->typemap_ser_data);
            PyBuffer_Release(&xt_type_map_bytes);
            PyBuffer_Release(&xt_type_info_bytes);
            Py_XDECREF(xt_type_data);
            goto err;
        }

        new->typemap_ser_sz = (uint32_t) xt_type_map_bytes.len;
        memcpy(new->typemap_ser_data, xt_type_map_bytes.buf, new->typemap_ser_sz);


        new->typeinfo_ser_sz = (uint32_t) xt_type_info_bytes.len;
        memcpy(new->typeinfo_ser_data, xt_type_info_bytes.buf, new->typeinfo_ser_sz);

        PyBuffer_Release(&xt_type_info_bytes);
        PyBuffer_Release(&xt_type_map_bytes);
        Py_XDECREF(xt_type_data);
    } else {
        new->typemap_ser_data = NULL;
        new->typemap_ser_sz = 0;
        new->typeinfo_ser_data = NULL;
        new->typeinfo_ser_sz = 0;
    }

#endif

    if (!keyless) {
        new->v2_key_vm = make_key_vm(idl, true);
        if (!valid_pt_or_set_error(new->v2_key_vm)) goto err;

        v0pykeysize = PyObject_GetAttrString(idl, "v0_key_max_size");
        if (!valid_topic_py_or_set_error(v0pykeysize)) {
            // No support for v0
            if ((PyLong_AsLong(pyversion_support) & 1) > 0)
                goto err;
            new->v0_key_vm = NULL;
            new->v0_key_maxsize_bigger_16 = false;
        } else {
            new->v0_key_vm = make_key_vm(idl, false);
            if (!valid_pt_or_set_error(new->v0_key_vm)) goto err;
            long long v0keysize = PyLong_AsLongLong(v0pykeysize);
            new->v0_key_maxsize_bigger_16 = v0keysize > 16;
        }

        v2pykeysize = PyObject_GetAttrString(idl, "v2_key_max_size");
        if (!valid_topic_py_or_set_error(v2pykeysize)) {
            // No support for v0
            if ((PyLong_AsLong(pyversion_support) & 2) > 0)
                goto err;
            new->v2_key_vm = NULL;
            new->v2_key_maxsize_bigger_16 = false;
        } else {
            new->v2_key_vm = make_key_vm(idl, true);
            if (!valid_pt_or_set_error(new->v2_key_vm)) goto err;
            long long v2keysize = PyLong_AsLongLong(v2pykeysize);
            new->v2_key_maxsize_bigger_16 = v2keysize > 16;
        }
    } else {
        new->v0_key_vm = NULL;
        new->v0_key_maxsize_bigger_16 = true;
        new->v2_key_vm = NULL;
        new->v2_key_maxsize_bigger_16 = true;
    }

    ddsi_sertype_init(
        &(new->my_c_type),
        name,
        &ddspy_sertype_ops,
        &ddspy_serdata_ops,
        keyless
    );

    if (new->is_v2_by_default)
        new->my_c_type.allowed_data_representation = DDS_DATA_REPRESENTATION_FLAG_XCDR2;
    else
        new->my_c_type.allowed_data_representation = DDS_DATA_REPRESENTATION_FLAG_XCDR1 | DDS_DATA_REPRESENTATION_FLAG_XCDR2;

    constructed = true;

err:
    if (new && !constructed) {
        dds_free(new);
        PyErr_SetString(PyExc_RuntimeError, "Error in constructing DDS sertype.");
        new = NULL;
    }

    Py_XDECREF(idl);
    Py_XDECREF(pyname);
    Py_XDECREF(pykeyless);
    Py_XDECREF(pyversion_support);
    Py_XDECREF(v0pykeysize);
    Py_XDECREF(v2pykeysize);

    return new;
}

/// Python BIND

static PyObject *
ddspy_topic_create(PyObject *self, PyObject *args)
{
    const char* name;
    PyObject* datatype;
    dds_entity_t participant;
    dds_entity_t sts;
    PyObject* qospy;
    PyObject* listenerpy;
    dds_listener_t* listener = NULL;
    dds_qos_t* qos = NULL;
    (void)self;

    if (!PyArg_ParseTuple(args, "lsOOO", &participant, &name, &datatype, &qospy, &listenerpy))
        return NULL;

    if (listenerpy != Py_None) listener = PyLong_AsVoidPtr(listenerpy);
    if (qospy != Py_None) qos = PyLong_AsVoidPtr(qospy);

    ddspy_sertype_t *sertype = ddspy_sertype_new(datatype);

    if (sertype == NULL) return NULL;

    Py_BEGIN_ALLOW_THREADS
    sts = dds_create_topic_sertype(participant, name, (struct ddsi_sertype **) &sertype, qos, listener, NULL);
    Py_END_ALLOW_THREADS

    if (PyErr_Occurred() || sts < 0) {
        ddsi_sertype_unref((struct ddsi_sertype *) sertype);
    }

    if (PyErr_Occurred()) return NULL;

    return PyLong_FromLong((long)sts);
}

static PyObject *
ddspy_write(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    assert(PyBuffer_IsContiguous(&sample_data, 'C'));

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_write(writer, &container);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_write_ts(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;
    dds_time_t time;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_write_ts(writer, &container, time);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_dispose(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_dispose(writer, &container);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_dispose_ts(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;
    dds_time_t time;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_dispose_ts(writer, &container, time);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_writedispose(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_writedispose(writer, &container);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_writedispose_ts(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;
    dds_time_t time;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_writedispose_ts(writer, &container, time);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_dispose_handle(PyObject *self, PyObject *args)
{
    dds_entity_t writer;
    dds_return_t sts;
    dds_instance_handle_t handle;
    (void)self;

    if (!PyArg_ParseTuple(args, "iK", &writer, &handle))
        return NULL;

    sts = dds_dispose_ih(writer, handle);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_dispose_handle_ts(PyObject *self, PyObject *args)
{
    dds_entity_t writer;
    dds_return_t sts;
    dds_instance_handle_t handle;
    dds_time_t time;
    (void)self;

    if (!PyArg_ParseTuple(args, "iKL", &writer, &handle, &time))
        return NULL;

    sts = dds_dispose_ih_ts(writer, handle, time);

    return PyLong_FromLong((long) sts);
}

static PyObject * sampleinfo_descriptor;

static PyObject* get_sampleinfo_pyobject(dds_sample_info_t *sampleinfo)
{
    PyObject* arguments = Py_BuildValue("IIIOLKKkkkkk",
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
        sampleinfo->absolute_generation_rank
    );
    PyObject *pysampleinfo = PyObject_CallObject(sampleinfo_descriptor, arguments);
    Py_DECREF(arguments);
    return pysampleinfo;
}

static inline uint32_t
check_number_of_samples(long long n)
{
    static const uint32_t max_samples = (UINT32_MAX / sizeof(dds_sample_info_t));

    if (n <= 0) {
        PyErr_SetString(PyExc_TypeError, "N must be a positive integer");
        return 0u;
    }
    if (n > (long long)max_samples) {
        PyErr_SetString(PyExc_TypeError, "N exceeds maximum");
        return 0u;
    }

    return (uint32_t)n;
}

static PyObject *
ddspy_read(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;
    (void)self;

    if (!PyArg_ParseTuple(args, "iL", &reader, &N))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    ddspy_sample_container_t* container = dds_alloc(sizeof(ddspy_sample_container_t) * Nu32);
    ddspy_sample_container_t** rcontainer = dds_alloc(sizeof(ddspy_sample_container_t*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = &container[i];
        container[i].usample = NULL;
    }

    sts = dds_read(reader, (void**) rcontainer, info, Nu32, Nu32);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        dds_free(container[i].usample);
    }
    dds_free(info);
    dds_free(container);
    dds_free(rcontainer);

    return list;
}


static PyObject *
ddspy_take(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;
    (void)self;

    if (!PyArg_ParseTuple(args, "iL", &reader, &N))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    ddspy_sample_container_t* container = dds_alloc(sizeof(ddspy_sample_container_t) * Nu32);
    ddspy_sample_container_t** rcontainer = dds_alloc(sizeof(ddspy_sample_container_t*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = &container[i];
        container[i].usample = NULL;
    }

    sts = dds_take(reader, (void**) rcontainer, info, Nu32, Nu32);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        dds_free(container[i].usample);
    }
    dds_free(info);
    dds_free(container);
    dds_free(rcontainer);

    return list;
}


static PyObject *
ddspy_read_handle(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;
    dds_instance_handle_t handle;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLK", &reader, &N, &handle))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    ddspy_sample_container_t* container = dds_alloc(sizeof(ddspy_sample_container_t) * Nu32);
    ddspy_sample_container_t** rcontainer = dds_alloc(sizeof(ddspy_sample_container_t*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = &container[i];
        container[i].usample = NULL;
    }

    sts = dds_read_instance(reader, (void**)rcontainer, info, Nu32, Nu32, handle);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        dds_free(container[i].usample);
    }
    dds_free(info);
    dds_free(container);
    dds_free(rcontainer);

    return list;
}


static PyObject *
ddspy_take_handle(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;
    dds_instance_handle_t handle;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLK", &reader, &N, &handle))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    ddspy_sample_container_t* container = dds_alloc(sizeof(ddspy_sample_container_t) * Nu32);
    ddspy_sample_container_t** rcontainer = dds_alloc(sizeof(ddspy_sample_container_t*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = &(container[i]);
        container[i].usample = NULL;
    }

    sts = dds_take_instance(reader, (void**) rcontainer, info, Nu32, Nu32, handle);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        dds_free(container[i].usample);
    }
    dds_free(info);
    dds_free(container);
    dds_free(rcontainer);

    return list;
}


static PyObject *
ddspy_register_instance(PyObject *self, PyObject *args)
{
    dds_entity_t writer;
    dds_instance_handle_t handle;
    dds_return_t sts;
    ddspy_sample_container_t container;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    handle = 0;
    container.usample_size = (size_t)sample_data.len;

    sts = dds_register_instance(writer, &handle, &container);

    PyBuffer_Release(&sample_data);

    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }
    return PyLong_FromUnsignedLongLong((unsigned long long) handle);
}


static PyObject *
ddspy_unregister_instance(PyObject *self, PyObject *args)
{
    dds_entity_t writer;
    dds_return_t sts;
    ddspy_sample_container_t container;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_unregister_instance(writer, &container);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}


static PyObject *
ddspy_unregister_instance_handle(PyObject *self, PyObject *args)
{
    dds_entity_t writer;
    dds_return_t sts;
    dds_instance_handle_t handle;
    (void)self;

    if (!PyArg_ParseTuple(args, "iK", &writer, &handle))
        return NULL;

    sts = dds_unregister_instance_ih(writer, handle);

    return PyLong_FromLong((long) sts);
}


static PyObject *
ddspy_unregister_instance_ts(PyObject *self, PyObject *args)
{
    dds_entity_t writer;
    dds_return_t sts;
    ddspy_sample_container_t container;
    dds_time_t time;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_unregister_instance_ts(writer, &container, time);

    PyBuffer_Release(&sample_data);

    return PyLong_FromLong((long) sts);
}


static PyObject *
ddspy_unregister_instance_handle_ts(PyObject *self, PyObject *args)
{
    dds_entity_t writer;
    dds_return_t sts;
    dds_instance_handle_t handle;
    dds_time_t time;
    (void)self;

    if (!PyArg_ParseTuple(args, "iKL", &writer, &handle, &time))
        return NULL;

    sts = dds_unregister_instance_ih_ts(writer, handle, time);

    return PyLong_FromLong((long) sts);
}


static PyObject *
ddspy_lookup_instance(PyObject *self, PyObject *args)
{
    dds_entity_t entity;
    dds_instance_handle_t sts;
    ddspy_sample_container_t container;
    Py_buffer sample_data;
    (void)self;

    if (!PyArg_ParseTuple(args, "iy*", &entity, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    assert(sample_data.len >= 0);
    container.usample_size = (size_t)sample_data.len;

    sts = dds_lookup_instance(entity, &container);

    PyBuffer_Release(&sample_data);

    return PyLong_FromUnsignedLongLong((unsigned long long) sts);
}

static PyObject *
ddspy_read_next(PyObject *self, PyObject *args)
{
    dds_entity_t reader;
    dds_return_t sts;
    dds_sample_info_t info;
    ddspy_sample_container_t container;
    ddspy_sample_container_t* pt_container;
    (void)self;
    container.usample = NULL;

    if (!PyArg_ParseTuple(args, "i", &reader))
        return NULL;

    pt_container = &container;

    sts = dds_read_next(reader, (void**) &pt_container, &info);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    if (sts == 0 || container.usample == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyObject* sampleinfo = get_sampleinfo_pyobject(&info);
    PyObject* item = Py_BuildValue("(y#O)", container.usample, container.usample_size, sampleinfo);
    Py_DECREF(sampleinfo);
    dds_free(container.usample);

    return item;
}

static PyObject *
ddspy_take_next(PyObject *self, PyObject *args)
{
    dds_entity_t reader;
    dds_return_t sts;
    dds_sample_info_t info;
    ddspy_sample_container_t container;
    ddspy_sample_container_t* pt_container;
    (void)self;
    container.usample = NULL;

    if (!PyArg_ParseTuple(args, "i", &reader))
        return NULL;

    pt_container = &container;

    sts = dds_take_next(reader, (void**) &pt_container, &info);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    if (sts == 0 || container.usample == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyObject* sampleinfo = get_sampleinfo_pyobject(&info);
    PyObject* item = Py_BuildValue("(y#O)", container.usample, container.usample_size, sampleinfo);
    Py_DECREF(sampleinfo);
    dds_free(container.usample);

    return item;
}


static PyObject *
ddspy_calc_key(PyObject *self, PyObject *args)
{
    PyObject* idl;
    Py_buffer sample_data;
    int v2;
    (void)self;

    if (!PyArg_ParseTuple(args, "Oy*p", &idl, &sample_data, &v2))
        return NULL;

    cdr_key_vm* vm = make_key_vm(idl, (bool)v2);

    if (vm == NULL) return NULL;

    cdr_key_vm_runner* runner = cdr_key_vm_create_runner(vm);

    size_t enc = cdr_key_vm_run(runner, (const uint8_t*) sample_data.buf, (size_t)sample_data.len);

    PyBuffer_Release(&sample_data);

    PyObject* returnv = Py_BuildValue("y#", (char*) runner->workspace, enc - 4);

    dds_free(runner->header);
    dds_free(runner);
    dds_free(vm->instructions);
    dds_free(vm);
    return returnv;
}


/* builtin topic */

static PyObject *
ddspy_read_participant(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* participant_constructor;
    PyObject* cqos_to_qos;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &participant_constructor, &cqos_to_qos))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    struct dds_builtintopic_participant** rcontainer = dds_alloc(sizeof(struct dds_builtintopic_participant*) * Nu32);

    if (!info || !rcontainer) {
        PyErr_SetString(PyExc_Exception, "Could not allocate memory");
        return NULL;
    }

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_read(reader, (void**) rcontainer, info, Nu32, Nu32);

    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos_p = PyLong_FromVoidPtr(rcontainer[i]->qos);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos = PyObject_CallFunction(cqos_to_qos, "O", qos_p);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* item = PyObject_CallFunction(participant_constructor, "y#OO", rcontainer[i]->key.v, 16, qos, sampleinfo);
        if (PyErr_Occurred()) { return NULL; }
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        Py_DECREF(qos_p);
        Py_DECREF(qos);
    }

    dds_return_loan(reader, (void**) rcontainer, sts);
    dds_free(info);
    dds_free(rcontainer);

    return list;
}

static PyObject *
ddspy_take_participant(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* participant_constructor;
    PyObject* cqos_to_qos;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &participant_constructor, &cqos_to_qos))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    struct dds_builtintopic_participant** rcontainer = dds_alloc(sizeof(struct dds_builtintopic_participant*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_take(reader, (void**) rcontainer, info, Nu32, Nu32);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos_p = PyLong_FromVoidPtr(rcontainer[i]->qos);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos = PyObject_CallFunction(cqos_to_qos, "O", qos_p);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* item = PyObject_CallFunction(participant_constructor, "y#OO", rcontainer[i]->key.v, 16, qos, sampleinfo);
        if (PyErr_Occurred()) { return NULL; }
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        Py_DECREF(qos_p);
        Py_DECREF(qos);
    }

    dds_return_loan(reader, (void**) rcontainer, sts);
    dds_free(info);
    dds_free(rcontainer);

    return list;
}

static PyObject *
ddspy_read_endpoint(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* endpoint_constructor;
    PyObject* cqos_to_qos;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    struct dds_builtintopic_endpoint** rcontainer = dds_alloc(sizeof(struct dds_builtintopic_endpoint*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_read(reader, (void**) rcontainer, info, Nu32, Nu32);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject *type_id_bytes = NULL;

#ifdef DDS_HAS_TYPE_DISCOVERY
        dds_ostream_t type_obj_stream;
        const dds_typeinfo_t *type_info = NULL;

        /// Fetch the type id
        dds_builtintopic_get_endpoint_type_info(rcontainer[i], &type_info);

        /// convert to cdr bytes
        if (type_info != NULL) {
            dds_ostream_init(&type_obj_stream, 0, DDS_CDR_ENC_VERSION_2);
            const dds_typeid_t *type_id = ddsi_typeinfo_complete_typeid(type_info);
            ddspy_typeid_ser(&type_obj_stream, type_id);
            type_id_bytes = Py_BuildValue("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);
            dds_ostream_fini(&type_obj_stream);
        }
        else {
            type_id_bytes = Py_None;
            Py_INCREF(type_id_bytes);
        }
#else
        type_id_bytes = Py_None;
        Py_INCREF(type_id_bytes);
#endif

        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos_p = PyLong_FromVoidPtr(rcontainer[i]->qos);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos = PyObject_CallFunction(cqos_to_qos, "O", qos_p);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* item = PyObject_CallFunction( \
            endpoint_constructor, "y#y#KssOOO", \
            rcontainer[i]->key.v, 16, \
            rcontainer[i]->participant_key.v, 16, \
            rcontainer[i]->participant_instance_handle,
            rcontainer[i]->topic_name,
            rcontainer[i]->type_name,
            qos,
            sampleinfo,
            type_id_bytes
        );
        if (PyErr_Occurred()) { return NULL; }
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        Py_DECREF(qos_p);
        Py_DECREF(qos);
    }

    dds_return_loan(reader, (void**) rcontainer, sts);
    dds_free(info);
    dds_free(rcontainer);

    return list;
}

static PyObject *
ddspy_read_topic(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* endpoint_constructor;
    PyObject* cqos_to_qos;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    struct dds_builtintopic_topic** rcontainer = dds_alloc(sizeof(struct dds_builtintopic_topic*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_read(reader, (void**) rcontainer, info, Nu32, Nu32);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject *type_id_bytes = NULL;

#ifdef DDS_HAS_TYPE_DISCOVERY
        dds_ostream_t type_obj_stream;
        const dds_typeinfo_t *type_info = NULL;

        /// Fetch the type id
        // dds_builtintopic_get_endpoint_type_info(rcontainer[i], &type_info);
        if (rcontainer[i]->qos && rcontainer[i]->qos->present & QP_TYPE_INFORMATION)
            type_info = rcontainer[i]->qos->type_information;

        /// convert to cdr bytes
        if (type_info != NULL) {
            dds_ostream_init(&type_obj_stream, 0, DDS_CDR_ENC_VERSION_2);
            const dds_typeid_t *type_id = ddsi_typeinfo_complete_typeid(type_info);
            ddspy_typeid_ser(&type_obj_stream, type_id);
            type_id_bytes = Py_BuildValue("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);
            dds_ostream_fini(&type_obj_stream);
        }
        else {
            type_id_bytes = Py_None;
            Py_INCREF(type_id_bytes);
        }
#else
        type_id_bytes = Py_None;
        Py_INCREF(type_id_bytes);
#endif

        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos_p = PyLong_FromVoidPtr(rcontainer[i]->qos);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos = PyObject_CallFunction(cqos_to_qos, "O", qos_p);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* item = PyObject_CallFunction( \
            endpoint_constructor, "y#ssOOO", \
            rcontainer[i]->key.d, 16, \
            rcontainer[i]->topic_name,
            rcontainer[i]->type_name,
            qos,
            sampleinfo,
            type_id_bytes
        );
        if (PyErr_Occurred()) { return NULL; }
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        Py_DECREF(qos_p);
        Py_DECREF(qos);
    }

    dds_return_loan(reader, (void**) rcontainer, sts);
    dds_free(info);
    dds_free(rcontainer);

    return list;
}

static PyObject *
ddspy_take_endpoint(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* endpoint_constructor;
    PyObject* cqos_to_qos;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    struct dds_builtintopic_endpoint** rcontainer = dds_alloc(sizeof(struct dds_builtintopic_endpoint*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_take(reader, (void**) rcontainer, info, Nu32, Nu32);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject *type_id_bytes = NULL;

#ifdef DDS_HAS_TYPE_DISCOVERY
        dds_ostream_t type_obj_stream;
        const dds_typeinfo_t *type_info = NULL;

        /// Fetch the type id
        dds_builtintopic_get_endpoint_type_info(rcontainer[i], &type_info);

        /// convert to cdr bytes
        if (type_info != NULL) {
            dds_ostream_init(&type_obj_stream, 0, DDS_CDR_ENC_VERSION_2);
            const dds_typeid_t *type_id = ddsi_typeinfo_complete_typeid(type_info);
            ddspy_typeid_ser(&type_obj_stream, type_id);
            type_id_bytes = Py_BuildValue("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);
            dds_ostream_fini(&type_obj_stream);
        }
        else {
            type_id_bytes = Py_None;
            Py_INCREF(type_id_bytes);
        }
#else
        type_id_bytes = Py_None;
        Py_INCREF(type_id_bytes);
#endif

        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        if (PyErr_Occurred()) {
            PyErr_Clear();
            PyErr_SetString(PyExc_Exception, "Sampleinfo errored.");
            return NULL;
        }

        PyObject* qos_p, *qos;

        if (rcontainer[i]->qos != NULL) {
            qos_p = PyLong_FromVoidPtr(rcontainer[i]->qos);
            if (PyErr_Occurred()) {
                PyErr_Clear();
                PyErr_SetString(PyExc_Exception, "VoidPtr errored.");
                return NULL;
            }
            qos = PyObject_CallFunction(cqos_to_qos, "O", qos_p);
            if (PyErr_Occurred()) {
                PyErr_Clear();
                PyErr_SetString(PyExc_Exception, "Callfunc cqos errored.");
                return NULL;
            }
        } else {
            Py_INCREF(Py_None);
            Py_INCREF(Py_None);
            qos_p = Py_None;
            qos = Py_None;
        }
        PyObject* item = PyObject_CallFunction( \
            endpoint_constructor, "y#y#Ks#s#OOO", \
            rcontainer[i]->key.v, (Py_ssize_t) 16, \
            rcontainer[i]->participant_key.v, (Py_ssize_t) 16, \
            rcontainer[i]->participant_instance_handle,
            rcontainer[i]->topic_name, rcontainer[i]->topic_name == NULL ? 0 : strlen(rcontainer[i]->topic_name),
            rcontainer[i]->type_name, rcontainer[i]->type_name == NULL ? 0 : strlen(rcontainer[i]->type_name),
            qos,
            sampleinfo,
            type_id_bytes
        );
        if (PyErr_Occurred()) {
            PyErr_Clear();
            PyErr_SetString(PyExc_Exception, "Callfunc endpoint constructor errored.");
            return NULL;
        }
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        Py_DECREF(qos_p);
        Py_DECREF(qos);
    }

    dds_return_loan(reader, (void**) rcontainer, sts);
    dds_free(info);
    dds_free(rcontainer);

    return list;
}

static PyObject *
ddspy_take_topic(PyObject *self, PyObject *args)
{
    uint32_t Nu32;
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* endpoint_constructor;
    PyObject* cqos_to_qos;
    (void)self;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
        return NULL;
    if (!(Nu32 = check_number_of_samples(N)))
        return NULL;

    dds_sample_info_t* info = dds_alloc(sizeof(dds_sample_info_t) * Nu32);
    struct dds_builtintopic_topic** rcontainer = dds_alloc(sizeof(struct dds_builtintopic_topic*) * Nu32);

    for(uint32_t i = 0; i < Nu32; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_take(reader, (void**) rcontainer, info, Nu32, Nu32);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(uint32_t i = 0; i < ((uint32_t)sts > Nu32 ? Nu32 : (uint32_t)sts); ++i) {
        PyObject *type_id_bytes = NULL;

#ifdef DDS_HAS_TYPE_DISCOVERY
        dds_ostream_t type_obj_stream;
        const dds_typeinfo_t *type_info = NULL;

        /// Fetch the type id
        // dds_builtintopic_get_endpoint_type_info(rcontainer[i], &type_info);
        if (rcontainer[i]->qos && rcontainer[i]->qos->present & QP_TYPE_INFORMATION)
            type_info = rcontainer[i]->qos->type_information;

        /// convert to cdr bytes
        if (type_info != NULL) {
            dds_ostream_init(&type_obj_stream, 0, DDS_CDR_ENC_VERSION_2);
            const dds_typeid_t *type_id = ddsi_typeinfo_complete_typeid(type_info);
            ddspy_typeid_ser(&type_obj_stream, type_id);
            type_id_bytes = Py_BuildValue("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);
            dds_ostream_fini(&type_obj_stream);
        }
        else {
            type_id_bytes = Py_None;
            Py_INCREF(type_id_bytes);
        }
#else
        type_id_bytes = Py_None;
        Py_INCREF(type_id_bytes);
#endif

        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        if (PyErr_Occurred()) {
            PyErr_Clear();
            PyErr_SetString(PyExc_Exception, "Sampleinfo errored.");
            return NULL;
        }

        PyObject* qos_p, *qos;

        if (rcontainer[i]->qos != NULL) {
            qos_p = PyLong_FromVoidPtr(rcontainer[i]->qos);
            if (PyErr_Occurred()) {
                PyErr_Clear();
                PyErr_SetString(PyExc_Exception, "VoidPtr errored.");
                return NULL;
            }
            qos = PyObject_CallFunction(cqos_to_qos, "O", qos_p);
            if (PyErr_Occurred()) {
                PyErr_Clear();
                PyErr_SetString(PyExc_Exception, "Callfunc cqos errored.");
                return NULL;
            }
        } else {
            Py_INCREF(Py_None);
            Py_INCREF(Py_None);
            qos_p = Py_None;
            qos = Py_None;
        }
        PyObject* item = PyObject_CallFunction( \
            endpoint_constructor, "y#s#s#OOO", \
            rcontainer[i]->key.d, (Py_ssize_t) 16, \
            rcontainer[i]->topic_name, rcontainer[i]->topic_name == NULL ? 0 : strlen(rcontainer[i]->topic_name),
            rcontainer[i]->type_name, rcontainer[i]->type_name == NULL ? 0 : strlen(rcontainer[i]->type_name),
            qos,
            sampleinfo,
            type_id_bytes
        );
        if (PyErr_Occurred()) {
            PyErr_Clear();
            PyErr_SetString(PyExc_Exception, "Callfunc endpoint constructor errored.");
            return NULL;
        }
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        Py_DECREF(qos_p);
        Py_DECREF(qos);
    }

    dds_return_loan(reader, (void**) rcontainer, sts);
    dds_free(info);
    dds_free(rcontainer);

    return list;
}
/* end builtin topic */



#ifdef DDS_HAS_TYPE_DISCOVERY

static PyObject *
ddspy_get_typeobj(PyObject *self, PyObject *args)
{
    dds_entity_t participant;
    Py_buffer type_id_buffer;
    dds_istream_t type_id_stream;
    dds_ostream_t type_obj_stream;
    dds_typeid_t * type_id = NULL;
    dds_typeobj_t * type_obj = NULL;
    dds_duration_t timeout;
    dds_return_t sts = DDS_RETCODE_ERROR;

    (void)self;

    if (!PyArg_ParseTuple(args, "iy*L", &participant, &type_id_buffer, &timeout))
        return NULL;

    type_id_stream.m_buffer = type_id_buffer.buf;
    type_id_stream.m_size = (uint32_t) type_id_buffer.len;
    type_id_stream.m_index = 0;
    type_id_stream.m_xcdr_version = DDS_CDR_ENC_VERSION_2;

    ddspy_typeid_deser(&type_id_stream, &type_id);
    PyBuffer_Release(&type_id_buffer);

    if (type_id == NULL) {
        return PyLong_FromLong(-1l);
    }

    Py_BEGIN_ALLOW_THREADS
    sts = dds_get_typeobj(participant, type_id, timeout, &type_obj);
    Py_END_ALLOW_THREADS

    dds_free(type_id);

    if (sts < 0 || type_obj == NULL) {
        return PyLong_FromLong((long) sts);
    }

    dds_ostream_init(&type_obj_stream, 0, DDS_CDR_ENC_VERSION_2);
    ddspy_typeobj_ser(&type_obj_stream, type_obj);
    dds_free_typeobj(type_obj);

    PyObject* typeobj_cdr = Py_BuildValue("y#", type_obj_stream.m_buffer, type_obj_stream.m_index);

    dds_ostream_fini(&type_obj_stream);

    if (PyErr_Occurred() || typeobj_cdr == NULL) {
        return NULL;
    }

    return typeobj_cdr;
}

#endif


char ddspy_docs[] = "DDSPY module";

PyMethodDef ddspy_funcs[] = {
	{	"ddspy_calc_key",
		(PyCFunction)ddspy_calc_key,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_topic_create",
		(PyCFunction)ddspy_topic_create,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_read",
		(PyCFunction)ddspy_read,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_take",
		(PyCFunction)ddspy_take,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_read_handle",
		(PyCFunction)ddspy_read_handle,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_take_handle",
		(PyCFunction)ddspy_take_handle,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_write",
		(PyCFunction)ddspy_write,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_write_ts",
		(PyCFunction)ddspy_write_ts,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_writedispose",
		(PyCFunction)ddspy_writedispose,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_writedispose_ts",
		(PyCFunction)ddspy_writedispose_ts,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_dispose",
		(PyCFunction)ddspy_dispose,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_dispose_ts",
		(PyCFunction)ddspy_dispose_ts,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_dispose_handle",
		(PyCFunction)ddspy_dispose_handle,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_dispose_handle_ts",
		(PyCFunction)ddspy_dispose_handle_ts,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_register_instance",
		(PyCFunction)ddspy_register_instance,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_unregister_instance",
		(PyCFunction)ddspy_unregister_instance,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_unregister_instance_handle",
		(PyCFunction)ddspy_unregister_instance_handle,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_unregister_instance_ts",
		(PyCFunction)ddspy_unregister_instance_ts,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_unregister_instance_handle_ts",
		(PyCFunction)ddspy_unregister_instance_handle_ts,
		METH_VARARGS,
		ddspy_docs},
    {   "ddspy_lookup_instance",
        (PyCFunction)ddspy_lookup_instance,
        METH_VARARGS,
        ddspy_docs},
    {   "ddspy_read_next",
        (PyCFunction)ddspy_read_next,
        METH_VARARGS,
        ddspy_docs},
    {   "ddspy_take_next",
        (PyCFunction)ddspy_take_next,
        METH_VARARGS,
        ddspy_docs},
    {	"ddspy_read_participant",
		(PyCFunction)ddspy_read_participant,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_take_participant",
		(PyCFunction)ddspy_take_participant,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_read_endpoint",
		(PyCFunction)ddspy_read_endpoint,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_take_endpoint",
		(PyCFunction)ddspy_take_endpoint,
		METH_VARARGS,
		ddspy_docs},
    {   "ddspy_read_topic",
        (PyCFunction)ddspy_read_topic,
        METH_VARARGS,
        ddspy_docs},
    {   "ddspy_take_topic",
        (PyCFunction)ddspy_take_topic,
        METH_VARARGS,
        ddspy_docs},
#ifdef DDS_HAS_TYPE_DISCOVERY
    {   "ddspy_get_typeobj",
        (PyCFunction)ddspy_get_typeobj,
        METH_VARARGS,
        ddspy_docs
    },
#endif
	{	NULL}
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



PyMODINIT_FUNC PyInit__clayer(void) {
    PyObject* import = PyImport_ImportModule("cyclonedds.internal");

    if (PyErr_Occurred()) return NULL;
    if (import == NULL) {
        PyObject* msg = PyUnicode_FromString("Failed to import cyclonedds.internal to get SampleInfo cls.");
        PyObject* name = PyUnicode_FromString("cyclonedds.internal");
        PyObject* path = PyUnicode_FromString("cyclonedds.internal");
        PyErr_SetImportError(msg, name, path);
        Py_DECREF(msg);
        Py_DECREF(name);
        Py_DECREF(path);
        return NULL;
    }

    sampleinfo_descriptor = PyObject_GetAttrString(import, "SampleInfo");

    if (PyErr_Occurred()) return NULL;
    if (sampleinfo_descriptor == NULL) {
        PyObject* msg = PyUnicode_FromString("Failed to import cyclonedds.internal to get SampleInfo cls.");
        PyObject* name = PyUnicode_FromString("cyclonedds.internal");
        PyObject* path = PyUnicode_FromString("cyclonedds.internal");
        PyErr_SetImportError(msg, name, path);
        Py_DECREF(msg);
        Py_DECREF(name);
        Py_DECREF(path);
        return NULL;
    }
    Py_DECREF(import);

    PyObject* module = PyModule_Create(&_clayer_mod);

    PyModule_AddObject(module, "DDS_INFINITY", PyLong_FromLongLong(DDS_INFINITY));
    PyModule_AddObject(module, "UINT32_MAX", PyLong_FromUnsignedLong(UINT32_MAX));
#ifdef DDS_HAS_TYPE_DISCOVERY
    Py_INCREF(Py_True);
    PyModule_AddObject(module, "HAS_TYPE_DISCOVERY", Py_True);
#else
    Py_INCREF(Py_False);
    PyModule_AddObject(module, "HAS_TYPE_DISCOVERY", Py_False);
#endif
#ifdef DDS_HAS_TOPIC_DISCOVERY
    Py_INCREF(Py_True);
    PyModule_AddObject(module, "HAS_TOPIC_DISCOVERY", Py_True);
#else
    Py_INCREF(Py_False);
    PyModule_AddObject(module, "HAS_TOPIC_DISCOVERY", Py_False);
#endif

	return module;
}
