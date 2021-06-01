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

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "cdrkeyvm.h"

#include "dds/dds.h"

#include "dds/ddsrt/endian.h"
#include "dds/ddsrt/heap.h"
#include "dds/ddsrt/mh3.h"
#include "dds/ddsrt/md5.h"
#include "dds/ddsi/q_radmin.h"
#include "dds/ddsi/ddsi_serdata.h"
#include "dds/ddsi/ddsi_sertype.h"


cdr_key_vm_op* make_vm_ops_from_py_op_list(PyObject* list)
{
    size_t len = PyList_Size(list);
    if (!len || PyErr_Occurred())
        return NULL;

    cdr_key_vm_op* ops = (cdr_key_vm_op*) malloc(sizeof(struct cdr_key_vm_op_s) * (len + 1));
    if (ops == NULL)
        return NULL;
    ops[len].type = CdrKeyVMOpDone;

    for (size_t i = 0; i < len; ++i) {
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

    for (size_t i = len; i > 0; --i) {
        if (ops[i-1].skip) {
            ops[i-1].type = CdrKeyVMOpDone;
        } else {
            break;
        }
    }

    return ops;
}

cdr_key_vm* make_key_vm(PyObject* cdr)
{
    PyObject* attr_keymachine = PyObject_GetAttrString(cdr, "cdr_key_machine");
    
    if (attr_keymachine == NULL) return NULL;

    PyObject* args = PyTuple_New(0);
    PyObject* list = PyObject_CallObject(attr_keymachine, args);
    Py_DECREF(attr_keymachine);
    Py_DECREF(args);

    if (list == NULL) return NULL;
    cdr_key_vm* vm = (cdr_key_vm*) malloc(sizeof(struct cdr_key_vm_s));
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
    cdr_key_vm* key_vm;
    bool keyless;
    bool key_maxsize_bigger_16;
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

ddspy_serdata_t *ddspy_serdata_new(const struct ddsi_sertype* type, enum ddsi_serdata_kind kind, size_t data_size)
{
    ddspy_serdata_t *new = (ddspy_serdata_t*) malloc(sizeof(struct ddspy_serdata));
    ddsi_serdata_init((ddsi_serdata_t*) new, type, kind);

    new->data = malloc(data_size);
    new->data_size = data_size;
    new->key = NULL;
    new->key_size = 0;
    new->key_populated = false;
    new->data_is_key = false;
    memset((unsigned char*) &(new->hash), 0, 16);

    return new;
}

void ddspy_serdata_calc_hash(ddspy_serdata_t* this)
{
    if (csertype(this)->key_maxsize_bigger_16) {
        ddsrt_md5_state_t md5st;
        ddsrt_md5_init(&md5st);
        ddsrt_md5_append(&md5st, this->key, this->key_size);
        ddsrt_md5_finish(&md5st, (unsigned char*) &(this->hash));
    } else {
        memcpy((char*) &(this->hash), (char*) this->key, 16);
    }
    this->c_data.hash = ddsrt_mh3(this->key, this->key_size, 0) ^ this->c_data.type->serdata_basehash;
}


void ddspy_serdata_populate_key(ddspy_serdata_t* this)
{
    if (sertype(this)->keyless) {
        this->key = ddsrt_malloc(16);
        this->key_size = 16;
        memset(this->key, 0, 16);
        memset((char*) &(this->hash), 0, 16);
        this->key_populated = true;
        return;
    }

    cdr_key_vm_runner* runner = cdr_key_vm_create_runner(csertype(this)->key_vm);
    this->key_size = cdr_key_vm_run(runner, this->data, this->data_size);
    this->key = runner->workspace;
    this->key_populated = true;

    free(runner);

    ddspy_serdata_calc_hash(this);
}


bool serdata_eqkey(const struct ddsi_serdata* a, const struct ddsi_serdata* b)
{
    if (csertype(a)->keyless ^ csertype(b)->keyless) {
        return false;
    }
    if (csertype(a)->keyless & csertype(b)->keyless) {
        return true;
    }

    assert(cserdata(a)->key != NULL);
    assert(cserdata(b)->key != NULL);
    return 0 == memcmp(&cserdata(a)->hash, &cserdata(b)->hash, 16);
}

uint32_t serdata_size(const struct ddsi_serdata* dcmn)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    if (cserdata(dcmn)->data_is_key) {
        return (uint32_t) cserdata(dcmn)->key_size;
    }
    return (uint32_t) cserdata(dcmn)->data_size;
}

ddsi_serdata_t *serdata_from_ser(
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
    
    ddspy_serdata_populate_key(d);
    
    switch (kind)
    {
    case SDK_KEY:
        d->data_is_key = true;
        break;
    case SDK_DATA:
        break;
    case SDK_EMPTY:
        assert(0);
    }
    
    assert(d->key != NULL);
    assert(d->data != NULL);
    assert(d->data_size != 0);
    assert(d->key_size >= 16);

    return (ddsi_serdata_t*) d;
}

ddsi_serdata_t *serdata_from_ser_iov(
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
    
    ddspy_serdata_populate_key(d);
    
    switch (kind)
    {
    case SDK_KEY:
        d->data_is_key = true;
        break;
    case SDK_DATA:
        break;
    case SDK_EMPTY:
        assert(0);
    }
    
    assert(d->key != NULL);
    assert(d->data != NULL);
    assert(d->data_size != 0);
    assert(d->key_size >= 16);

    return (ddsi_serdata_t*) d;
}

ddsi_serdata_t *serdata_from_keyhash(
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


ddsi_serdata_t *serdata_from_sample(
  const ddsi_sertype_t* type,
  enum ddsi_serdata_kind kind,
  const void* sample)
{
    ddspy_sample_container_t *container = (ddspy_sample_container_t*) sample;

    ddspy_serdata_t* d = ddspy_serdata_new(type, kind, container->usample_size);
    memcpy((char*) d->data, container->usample, container->usample_size);

    ddspy_serdata_populate_key(d);
    
    switch (kind)
    {
    case SDK_KEY:
        d->data_is_key = true;
        break;
    case SDK_DATA:
        break;
    case SDK_EMPTY:
        assert(0);
    }
    
    assert(d->key != NULL);
    assert(d->data != NULL);
    assert(d->data_size != 0);
    assert(d->key_size >= 16);
    
    return (ddsi_serdata_t*) d;
}

void serdata_to_ser(const ddsi_serdata_t* dcmn, size_t off, size_t sz, void* buf)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 16);
    if (cserdata(dcmn)->data_is_key) {
        memcpy(buf, (char*) cserdata(dcmn)->key + off, sz);
    }
    else {
        memcpy(buf, (char*) cserdata(dcmn)->data + off, sz);
    }
}

ddsi_serdata_t *serdata_to_ser_ref(
  const struct ddsi_serdata* dcmn, size_t off,
  size_t sz, ddsrt_iovec_t* ref)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 16);

    if (cserdata(dcmn)->data_is_key) {
        ref->iov_base = (char*) cserdata(dcmn)->key + off;
        ref->iov_len = sz;
    }
    else {
        ref->iov_base = (char*) cserdata(dcmn)->data + off;
        ref->iov_len = sz;
    }
    return ddsi_serdata_ref(dcmn);
}

void serdata_to_ser_unref(struct ddsi_serdata* dcmn, const ddsrt_iovec_t* ref)
{
    (void)ref;    // unused
    ddsi_serdata_unref(dcmn);
}

bool serdata_to_sample(
  const ddsi_serdata_t* dcmn, void* sample, void** bufptr,
  void* buflim)
{
    (void)bufptr;
    (void)buflim;
    ddspy_sample_container_t *container = (ddspy_sample_container_t*) sample;
    
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 16);
    assert(container->usample == NULL);

    container->usample = malloc(cserdata(dcmn)->data_size);
    memcpy(container->usample, cserdata(dcmn)->data, cserdata(dcmn)->data_size);
    container->usample_size = cserdata(dcmn)->data_size;

    return true;
}

ddsi_serdata_t *serdata_to_typeless(const ddsi_serdata_t* dcmn)
{
    /*ddspy_serdata_t *d_tl = ddspy_serdata_new(dcmn->type, SDK_DATA, cserdata(dcmn)->data_size);

    d_tl->c_data.type = NULL; 
    d_tl->c_data.hash = cserdata(dcmn)->c_data.hash;
    d_tl->c_data.timestamp.v = INT64_MIN;
    memcpy((unsigned char*) &(d_tl->hash), (unsigned char*) &(cserdata(dcmn)->hash), 16);
    d_tl->key = malloc(cserdata(dcmn)->key_size);
    
    memcpy(d_tl->data, cserdata(dcmn)->data, cserdata(dcmn)->data_size);
    memcpy(d_tl->key, cserdata(dcmn)->key, cserdata(dcmn)->key_size);
    d_tl->key_size = cserdata(dcmn)->key_size;*/
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 16);

    return ddsi_serdata_ref(dcmn);
}

bool serdata_typeless_to_sample(
  const struct ddsi_sertype* type,
  const struct ddsi_serdata* dcmn, void* sample,
  void**buf, void*buflim)
{
    ddspy_sample_container_t* container = (ddspy_sample_container_t*) sample;
    
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 16);
    assert(container->usample == NULL);

    container->usample = malloc(cserdata(dcmn)->data_size);
    container->usample_size = cserdata(dcmn)->data_size;

    memcpy(container->usample, cserdata(dcmn)->data, container->usample_size);
    
    return true;
}

void serdata_free(struct ddsi_serdata* dcmn)
{
    assert(cserdata(dcmn)->key != NULL);
    assert(cserdata(dcmn)->data != NULL);
    assert(cserdata(dcmn)->data_size != 0);
    assert(cserdata(dcmn)->key_size >= 16);

    free(serdata(dcmn)->data);
    free(serdata(dcmn)->key);
    free(dcmn);
}

size_t serdata_print(const struct ddsi_sertype* tpcmn, const struct ddsi_serdata* dcmn, char* buf, size_t bufsize)
{
    (void)tpcmn;

    return 0;
}

void serdata_get_keyhash(const ddsi_serdata_t* d, struct ddsi_keyhash* buf, bool force_md5)
{
    assert(cserdata(d)->key != NULL);
    assert(cserdata(d)->data != NULL);
    assert(cserdata(d)->data_size != 0);
    assert(cserdata(d)->key_size >= 16);
    assert(d->type != NULL);

    if (csertype(d)->keyless) {
        memset(buf->value, 0, 16);
    }

    if (force_md5 && !(((const ddspy_sertype_t*) d->type)->key_maxsize_bigger_16))
    {
        ddsrt_md5_state_t md5st;
        ddsrt_md5_init(&md5st);
        ddsrt_md5_append(&md5st, (unsigned char*) &(cserdata(d)->hash), 16);
        ddsrt_md5_finish(&md5st, buf->value);
    }
    else
    {
        memcpy(buf->value, (unsigned char*)  &(cserdata(d)->hash), 16);
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

void sertype_free(struct ddsi_sertype* tpcmn)
{
    struct ddspy_sertype* this = (struct ddspy_sertype*) tpcmn;
    if (this->key_vm != NULL) {
        free(this->key_vm->instructions);
        free(this->key_vm);
    }

    // Free the python type if python isn't already shutting down.
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
}

void sertype_zero_samples(const struct ddsi_sertype *sertype_common, void *samples, size_t count)
{
    memset(samples, 0, sizeof(ddspy_sample_container_t) * count);
}

void sertype_realloc_samples(void **ptrs, const struct ddsi_sertype *sertype_common, void *old, size_t oldcount, size_t count)
{
    char *new = (oldcount == count) ? old : dds_realloc (old, sizeof(ddspy_sample_container_t) * count);
    if (new && count > oldcount)
        memset (new + sizeof(ddspy_sample_container_t) * oldcount, 0, sizeof(ddspy_sample_container_t) * (count - oldcount));

    for (size_t i = 0; i < count; i++)
    {
        void *ptr = (char *) new + i * sizeof(ddspy_sample_container_t);
        ptrs[i] = ptr;
    }
}

void sertype_free_samples(const struct ddsi_sertype *sertype_common, void **ptrs, size_t count, dds_free_op_t op)
{
    if (count > 0)
    {
        if (op & DDS_FREE_CONTENTS_BIT)
        {
            if (((ddspy_sample_container_t*) ptrs[0])->usample != NULL)
                free(((ddspy_sample_container_t*) ptrs[0])->usample);
        }
        
        if (op & DDS_FREE_ALL_BIT)
        {
            dds_free (ptrs[0]);
        }
    }
}

bool sertype_equal(const ddsi_sertype_t* acmn, const ddsi_sertype_t* bcmn)
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

uint32_t sertype_hash(const struct ddsi_sertype* tpcmn)
{
  (void)tpcmn;
  return 0x0;
}


const struct ddsi_sertype_ops ddspy_sertype_ops = {
    ddsi_sertype_v0,
    NULL,

    &sertype_free,
    &sertype_zero_samples,
    &sertype_realloc_samples,
    &sertype_free_samples,
    &sertype_equal,
    &sertype_hash,

    /*typid_hash*/ NULL,
    /*serialized_size*/NULL,
    /*serialize*/NULL,
    /*deserialize*/NULL,
    /*assignable_from*/NULL
};


bool valid_topic_py_or_set_error(PyObject *py_obj)
{
    if (PyErr_Occurred()) return false;
    if (py_obj != NULL && py_obj != Py_None) return true;

    PyErr_SetString(PyExc_TypeError, "Invalid python object used as topic datatype.");
    return false;
}

bool valid_pt_or_set_error(void *py_obj)
{
    if (PyErr_Occurred()) return false;
    if (py_obj != NULL) return true;

    PyErr_SetString(PyExc_TypeError, "Invalid c object created.");
    return false;
}


ddspy_sertype_t *ddspy_sertype_new(PyObject *pytype)
{
    /// Check all return values
    PyObject *cdr = PyObject_GetAttrString(pytype, "cdr");
    if (!valid_topic_py_or_set_error(cdr)) return NULL;

    PyObject* pyname = PyObject_GetAttrString(cdr, "typename");
    if (!valid_topic_py_or_set_error(pyname)) {
        Py_DECREF(cdr);    
        return NULL;
    }

    PyObject* pykeyless = PyObject_GetAttrString(cdr, "keyless");
    if (!valid_topic_py_or_set_error(pykeyless))  {
        Py_DECREF(cdr); 
        Py_DECREF(pyname);   
        return NULL;
    }
    
    const char *name = PyUnicode_AsUTF8(pyname);
    bool keyless = pykeyless == Py_True;

    ddspy_sertype_t *new = (ddspy_sertype_t*) malloc(sizeof(ddspy_sertype_t));
    Py_INCREF(pytype);
    Py_DECREF(pykeyless);
    
    new->my_py_type = pytype;
    new->keyless = keyless;

    if (!keyless) {
        new->key_vm = make_key_vm(cdr);
        if (!valid_pt_or_set_error(new->key_vm)) {
            free(new);
            Py_DECREF(pytype);
            Py_DECREF(pyname);
            return NULL;
        }

        PyObject* pykeysize = PyObject_GetAttrString(cdr, "key_max_size");
        if (!valid_topic_py_or_set_error(pykeysize)) {
            free(new);
            Py_DECREF(pytype);
            Py_DECREF(pyname);
            return NULL;
        }

        long long keysize = PyLong_AsLongLong(pykeysize);
        Py_DECREF(pykeysize);

        if (PyErr_Occurred()) {
            // Overflow
            PyErr_Clear();
            new->key_maxsize_bigger_16 = true;
        }
        else {
            new->key_maxsize_bigger_16 = keysize > 16;
        }
    } else {
        new->key_vm = NULL;
        new->key_maxsize_bigger_16 = true; // arbitrary
    }

    Py_DECREF(cdr);

    ddsi_sertype_init(
        &(new->my_c_type),
        name,
        &ddspy_sertype_ops,
        &ddspy_serdata_ops,
        keyless
    );
    Py_DECREF(pyname);

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

    if (!PyArg_ParseTuple(args, "lsOOO", &participant, &name, &datatype, &qospy, &listenerpy))
        return NULL;

    if (listenerpy != Py_None) listener = PyLong_AsVoidPtr(listenerpy);
    if (qospy != Py_None) qos = PyLong_AsVoidPtr(qospy);

    ddspy_sertype_t *sertype = ddspy_sertype_new(datatype);
    ddsi_sertype_t *rsertype = (ddsi_sertype_t*) sertype;

    sts = dds_create_topic_sertype(participant, name, (struct ddsi_sertype **) &rsertype, qos, listener, NULL);

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

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    assert(PyBuffer_IsContiguous(sample_data, 'C'));

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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
        sampleinfo->valid_data ? Py_True : Py_False,
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

static PyObject *
ddspy_read(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    if (!PyArg_ParseTuple(args, "iL", &reader, &N))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    ddspy_sample_container_t* container = malloc(sizeof(ddspy_sample_container_t) * N);
    ddspy_sample_container_t** rcontainer = malloc(sizeof(ddspy_sample_container_t*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = &container[i];
        container[i].usample = NULL;
    }

    sts = dds_read(reader, (void**) rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        free(container[i].usample);
    }
    free(info);
    free(container);
    free(rcontainer);

    return list;
}


static PyObject *
ddspy_take(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    if (!PyArg_ParseTuple(args, "iL", &reader, &N))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    ddspy_sample_container_t* container = malloc(sizeof(ddspy_sample_container_t) * N);
    ddspy_sample_container_t** rcontainer = malloc(sizeof(ddspy_sample_container_t*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = &container[i];
        container[i].usample = NULL;
    }

    sts = dds_take(reader, (void**)rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        free(container[i].usample);
    }
    free(info);
    free(container);
    free(rcontainer);

    return list;
}


static PyObject *
ddspy_read_handle(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;
    dds_instance_handle_t handle;

    if (!PyArg_ParseTuple(args, "iLK", &reader, &N, &handle))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    ddspy_sample_container_t* container = malloc(sizeof(ddspy_sample_container_t) * N);
    ddspy_sample_container_t** rcontainer = malloc(sizeof(ddspy_sample_container_t*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = &container[i];
        container[i].usample = NULL;
    }

    sts = dds_read_instance(reader, (void**)rcontainer, info, N, N, handle);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        free(container[i].usample);
    }
    free(info);
    free(container);
    free(rcontainer);

    return list;
}


static PyObject *
ddspy_take_handle(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;
    dds_instance_handle_t handle;

    if (!PyArg_ParseTuple(args, "iLK", &reader, &N, &handle))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    ddspy_sample_container_t* container = malloc(sizeof(ddspy_sample_container_t) * N);
    ddspy_sample_container_t** rcontainer = malloc(sizeof(ddspy_sample_container_t*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = &(container[i]);
        container[i].usample = NULL;
    }

    sts = dds_take_instance(reader, (void**) rcontainer, info, N, N, handle);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        PyObject* item = Py_BuildValue("(y#O)", container[i].usample, container[i].usample_size, sampleinfo);
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        free(container[i].usample);
    }
    free(info);
    free(container);
    free(rcontainer);

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

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*", &writer, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*L", &writer, &sample_data, &time))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

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

    if (!PyArg_ParseTuple(args, "iy*", &entity, &sample_data))
        return NULL;

    container.usample = sample_data.buf;
    container.usample_size = sample_data.len;

    sts = dds_lookup_instance(entity, &container);

    PyBuffer_Release(&sample_data);

    return PyLong_FromUnsignedLongLong(sts);
}

static PyObject *
ddspy_read_next(PyObject *self, PyObject *args)
{
    dds_entity_t reader;
    dds_return_t sts;
    dds_sample_info_t info;
    ddspy_sample_container_t container;
    ddspy_sample_container_t* pt_container;
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
    free(container.usample);

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
    free(container.usample);

    return item;
}


static PyObject *
ddspy_calc_key(PyObject *self, PyObject *args)
{
    PyObject* cdr;
    Py_buffer sample_data;

    if (!PyArg_ParseTuple(args, "Oy*", &cdr, &sample_data))
        return NULL;

    cdr_key_vm* vm = make_key_vm(cdr);

    if (vm == NULL) return NULL;

    cdr_key_vm_runner* runner = cdr_key_vm_create_runner(vm);

    size_t enc = cdr_key_vm_run(runner, (const uint8_t*) sample_data.buf, (size_t)sample_data.len);

    PyBuffer_Release(&sample_data);

    PyObject* returnv = Py_BuildValue("y#", (char*) runner->workspace, enc);

    free(runner->workspace);
    free(runner);
    free(vm->instructions);
    free(vm);
    return returnv;
}


/* builtin topic */


static PyObject *
ddspy_read_participant(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* participant_constructor;
    PyObject* cqos_to_qos;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &participant_constructor, &cqos_to_qos))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    struct dds_builtintopic_participant** rcontainer = malloc(sizeof(struct dds_builtintopic_participant*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_read(reader, (void**) rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
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
    free(info);
    free(rcontainer);

    return list;
}

static PyObject *
ddspy_take_participant(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* participant_constructor;
    PyObject* cqos_to_qos;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &participant_constructor, &cqos_to_qos))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    struct dds_builtintopic_participant** rcontainer = malloc(sizeof(struct dds_builtintopic_participant*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_take(reader, (void**) rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
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
    free(info);
    free(rcontainer);

    return list;
}

static PyObject *
ddspy_read_endpoint(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* endpoint_constructor;
    PyObject* cqos_to_qos;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    struct dds_builtintopic_endpoint** rcontainer = malloc(sizeof(struct dds_builtintopic_endpoint*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_read(reader, (void**) rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
        PyObject* sampleinfo = get_sampleinfo_pyobject(&info[i]);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos_p = PyLong_FromVoidPtr(rcontainer[i]->qos);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* qos = PyObject_CallFunction(cqos_to_qos, "O", qos_p);
        if (PyErr_Occurred()) { return NULL; }
        PyObject* item = PyObject_CallFunction( \
            endpoint_constructor, "y#y#KssOO", \
            rcontainer[i]->key.v, 16, \
            rcontainer[i]->participant_key.v, 16, \
            rcontainer[i]->participant_instance_handle,
            rcontainer[i]->topic_name,
            rcontainer[i]->type_name,
            qos,
            sampleinfo
        );
        if (PyErr_Occurred()) { return NULL; }
        PyList_SetItem(list, i, item); // steals ref
        Py_DECREF(sampleinfo);
        Py_DECREF(qos_p);
        Py_DECREF(qos);
    }

    dds_return_loan(reader, (void**) rcontainer, sts);
    free(info);
    free(rcontainer);

    return list;
}

static PyObject *
ddspy_take_endpoint(PyObject *self, PyObject *args)
{
    long long N;
    dds_entity_t reader;
    dds_return_t sts;

    PyObject* endpoint_constructor;
    PyObject* cqos_to_qos;

    if (!PyArg_ParseTuple(args, "iLOO", &reader, &N, &endpoint_constructor, &cqos_to_qos))
        return NULL;

    if (N <= 0) {
        PyErr_SetString(PyExc_TypeError, "N should be a positive integer");
        return NULL;
    }

    dds_sample_info_t* info = malloc(sizeof(dds_sample_info_t) * N);
    struct dds_builtintopic_endpoint** rcontainer = malloc(sizeof(struct dds_builtintopic_endpoint*) * N);

    for(int i = 0; i < N; ++i) {
        rcontainer[i] = NULL;
    }

    sts = dds_take(reader, (void**) rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < (sts > N ? N : sts); ++i) {
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
            endpoint_constructor, "y#y#Ks#s#OO", \
            rcontainer[i]->key.v, (Py_ssize_t) 16, \
            rcontainer[i]->participant_key.v, (Py_ssize_t) 16, \
            rcontainer[i]->participant_instance_handle,
            rcontainer[i]->topic_name, rcontainer[i]->topic_name == NULL ? 0 : strlen(rcontainer[i]->topic_name),
            rcontainer[i]->type_name, rcontainer[i]->type_name == NULL ? 0 : strlen(rcontainer[i]->type_name),
            qos,
            sampleinfo
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
    free(info);
    free(rcontainer);

    return list;
}
/* end builtin topic */


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
	{	NULL}
};

char ddspymod_docs[] = "This is hello world module.";

void free_ddspy(void) {
    Py_DECREF(sampleinfo_descriptor);
}

PyModuleDef ddspy_mod = {
	PyModuleDef_HEAD_INIT,
	"ddspy",
	ddspymod_docs,
	-1,
	ddspy_funcs,
	NULL,
	NULL,
	NULL,
	free_ddspy
};

PyMODINIT_FUNC PyInit_ddspy(void) {
    PyObject* import = PyImport_ImportModule("cyclonedds.internal"); 
    sampleinfo_descriptor = PyObject_GetAttrString(import, "SampleInfo");
    Py_DECREF(import);
	return PyModule_Create(&ddspy_mod);
}