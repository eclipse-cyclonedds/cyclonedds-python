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

#include <Python.h>

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include "dds/dds.h"

#include "dds/ddsrt/endian.h"
#include "dds/ddsrt/md5.h"
#include "dds/ddsi/q_radmin.h"
#include "dds/ddsi/ddsi_serdata.h"
#include "dds/ddsi/ddsi_sertype.h"

//#define TRACE_SAMPL_ALLOC 1
#ifdef TRACE_SAMPL_ALLOC
void py_take_ref_(PyObject* object, int line)
{
    if (object == NULL) {
        printf("TRIEDTAKEREFNULL on %i\n", line);
        return;
    }
    printf("TAKEREF(%p) on %i\n", (void *) object, line);
    Py_INCREF(object);
}

void py_release_ref_(PyObject* object, int line)
{
    if (object == NULL) {
        printf("TRIEDRELEASEREFNULL on %i\n", line);
        return;
    }
    printf("RELEASEREF(%p) on %i\n", (void *) object, line);
    Py_DECREF(object);
}

void py_return_ref_(PyObject* object, int line)
{
    if (object == NULL) {
        printf("TRIEDRETURNNULL on %i\n", line);
        return;
    }
    printf("RETURNEDREF(%p) on %i\n", (void *) object, line);
}

void py_check(PyObject* object, const char* msg)
{
    if (!object) {
        printf("%s", msg);
        assert(0);
    }
    if (PyErr_Occurred() != NULL) {
        printf("Error occurred before %s", msg);
        assert(0);
    }
}

void print_trace (void)
{
  void *array[10];
  char **strings;
  int size, i;

  size = backtrace (array, 10);
  strings = backtrace_symbols (array, size);
  if (strings != NULL)
  {

    printf ("Obtained %d stack frames.\n", size);
    for (i = 0; i < size; i++)
      printf ("%s\n", strings[i]);
  }

  free (strings);
}

#define py_take_ref(T) py_take_ref_(T, __LINE__)
#define py_release_ref(T) py_release_ref_(T, __LINE__)
#define py_return_ref(T) py_return_ref_(T, __LINE__)
#define trace
#else
void py_take_ref(PyObject* object)
{
    Py_INCREF(object);
}

void py_release_ref(PyObject* object)
{
    Py_DECREF(object);
}

void py_check(PyObject* object, const char* msg)
{
    (void*) object;
    (void*) msg;
}

void py_return_ref(PyObject* object)
{
    (void*) object;
}

#define trace
#endif


typedef struct ddsi_serdata ddsi_serdata_t;
typedef struct ddsi_sertype ddsi_sertype_t;


// Python refcount: one ref for each PyObject*.
typedef struct ddspy_sertype {
    ddsi_sertype_t my_c_type;
    PyObject* my_py_type;
    PyObject* deserialize_attr;
    PyObject* serialize_attr;
    PyObject* key_calc_attr;
    PyObject* keyhash_calc_attr;
    bool key_maxsize_bigger_16;
} ddspy_sertype_t;

// Python refcount: one ref for sample.
typedef struct ddspy_serdata {
    ddsi_serdata_t c_data;
    PyObject* sample;
    void* data;
    size_t data_size;
    ddsi_keyhash_t key;
    bool hash_populated;
} ddspy_serdata_t;

// Python refcount: one ref for sample.
typedef struct ddspy_sample_container {
    PyObject* sample;
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
    ddspy_serdata_t *new = (ddspy_serdata_t*) malloc(sizeof(ddspy_serdata_t));
    ddsi_serdata_init((ddsi_serdata_t*) new, type, kind);

    new->data = malloc(data_size);
    new->data_size = data_size;
    new->hash_populated = false;
    new->sample = NULL;

    return new;
}


void ddspy_serdata_ensure_sample(ddspy_serdata_t* this)
{
    if (this->sample)
        return;

    PyGILState_STATE state = PyGILState_Ensure();

    /// This is not a copy
    PyObject* memory = PyMemoryView_FromMemory((char*) this->data + 4, this->data_size - 4, PyBUF_READ);
    PyObject* arglist = Py_BuildValue("(O)", memory);

    PyObject* result = PyObject_CallObject(sertype(this)->deserialize_attr, arglist);
    // We already have a ref to result.

    Py_DECREF(arglist);
    Py_DECREF(memory);

    this->sample = result;

    PyGILState_Release(state);
}


void ddspy_serdata_populate_hash(ddspy_serdata_t* this)
{
    if (this->hash_populated) {
        return;
    }

    if (csertype(this)->keyhash_calc_attr == NULL) {
        return;
    }

    ddspy_serdata_ensure_sample(this);

    /// Make calls into python possible.
    PyGILState_STATE state = PyGILState_Ensure();

    PyObject* arglist = Py_BuildValue("(O)", this->sample);
    PyObject* result = PyObject_CallObject(sertype(this)->keyhash_calc_attr, arglist);
    Py_DECREF(arglist);

    if (result == NULL) {
        // Error condition: This is when python has set an error code, the keyhash is unfilled.
        // We won't set hash_populated, but we have to start the python interpreter back up
        PyGILState_Release(state);
        assert(0);
        return;
    }

    /// This is not a copy
    const char* buf = PyBytes_AsString(result);
    int size = PyBytes_Size(result);

    if (size != 16) {
        // Error condition: Python did not give us 16 bytes exactly
        // We won't set hash_populated, but we have to start the python interpreter back up
        PyGILState_Release(state);
        assert(0);
        return;
    }

    memcpy(this->key.value, buf, 16);
    memcpy(&(this->c_data.hash), buf, 4);

    Py_DECREF(result);

    PyGILState_Release(state);
    this->hash_populated = true;
}

bool serdata_eqkey(const struct ddsi_serdata* a, const struct ddsi_serdata* b)
{
    return 0 == memcmp(cserdata(a)->key.value, cserdata(b)->key.value, 16);
}

uint32_t serdata_size(const struct ddsi_serdata* dcmn)
{
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

    switch (kind)
    {
    case SDK_KEY:
        assert(0); //ddspy_serdata_key_read(d);
        break;
    case SDK_DATA:
        ddspy_serdata_ensure_sample(d);
        break;
    case SDK_EMPTY:
        assert(0);
    }

    ddspy_serdata_populate_hash(d);

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

    switch (kind)
    {
    case SDK_KEY:
        assert(0); //ddspy_serdata_key_read(d);
        break;
    case SDK_DATA:
        ddspy_serdata_ensure_sample(d);
        break;
    case SDK_EMPTY:
        assert(0);
    }

    ddspy_serdata_populate_hash(d);

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
  return NULL;
}


ddsi_serdata_t *serdata_from_sample(
  const ddsi_sertype_t* type,
  enum ddsi_serdata_kind kind,
  const void* sample)
{
    ddspy_sample_container_t *container = (ddspy_sample_container_t*) sample;

    /// If there is no PyObject in the container this is not possible.
    assert(container->sample);

    /// Make calls into python possible.
    PyGILState_STATE state = PyGILState_Ensure();

    ddspy_serdata_t *d;
    switch(kind)
    {
        case SDK_DATA:
        {
            PyObject* arglist = Py_BuildValue("(O)", container->sample);
            PyObject* result = PyObject_CallObject(((const ddspy_sertype_t*) type)->serialize_attr, arglist);
            Py_DECREF(arglist);

            if (result == NULL) {
                // Error condition: This is when python has set an error code, no serialization happened.
                // We won't set hash_populated, but we have to start the python interpreter back up
                PyGILState_Release(state);
                return NULL;
            }

            /// This is not a copy
            const char* buf = PyBytes_AsString(result);
            int size = PyBytes_Size(result);

            d = ddspy_serdata_new(type, kind, size + 4);
            memcpy((char*) d->data + 4, buf, size);
            Py_DECREF(result);
        }
        break;
        case SDK_KEY:
        {
            PyObject* arglist = Py_BuildValue("(O)", container->sample);
            PyObject* result = PyObject_CallObject(((const ddspy_sertype_t*) type)->key_calc_attr, arglist);
            Py_DECREF(arglist);

            if (result == NULL) {
                // Error condition: This is when python has set an error code, the keyhash is unfilled.
                // We won't set hash_populated, but we have to start the python interpreter back up
                PyGILState_Release(state);
                return NULL;
            }

            /// This is not a copy
            const char* buf = PyBytes_AsString(result);
            int size = PyBytes_Size(result);

            d = ddspy_serdata_new(type, kind, size + 4);
            memcpy((char*) d->data + 4, buf, size);
            Py_DECREF(result);
        }
        break;
        default:
        case SDK_EMPTY:
            assert(0);
    }

    /// Container already has a reference, take one extra for serdata.
    d->sample = container->sample;
    py_take_ref(d->sample);
    PyGILState_Release(state);

    memset(d->data, 0x0, 4);
    if (DDSRT_ENDIAN == DDSRT_LITTLE_ENDIAN)
        memset((char*) d->data + 1, 0x1, 1);

    ddspy_serdata_populate_hash(d);
    return (ddsi_serdata_t*) d;
}


void serdata_to_ser(const ddsi_serdata_t* dcmn, size_t off, size_t sz, void* buf)
{
    memcpy(buf, (char*) cserdata(dcmn)->data + off, sz);
}

ddsi_serdata_t *serdata_to_ser_ref(
  const struct ddsi_serdata* dcmn, size_t off,
  size_t sz, ddsrt_iovec_t* ref)
{
    ref->iov_base = (char*) cserdata(dcmn)->data + off;
    ref->iov_len = sz;
    return ddsi_serdata_ref(dcmn);
}

void serdata_to_ser_unref(struct ddsi_serdata* dcmn, const ddsrt_iovec_t* ref)
{
    (void)ref;    // unused
    ddsi_serdata_unref(dcmn);
}

bool serdata_to_sample(
  ddsi_serdata_t* dcmn, void* sample, void** bufptr,
  void* buflim)
{
    (void)bufptr;
    (void)buflim;

    ddspy_sample_container_t *container = (ddspy_sample_container_t*) sample;
    ddspy_serdata_ensure_sample(cserdata(dcmn));

    // Take a reference for the container
    container->sample = cserdata(dcmn)->sample;
    py_take_ref(container->sample);

    return false;
}

ddsi_serdata_t *serdata_to_typeless(const ddsi_serdata_t* dcmn)
{
    ddspy_serdata_t *d_tl = ddspy_serdata_new(dcmn->type, SDK_KEY, 16);

    d_tl->c_data.type = NULL;
    d_tl->c_data.hash = dcmn->hash;
    d_tl->c_data.timestamp.v = INT64_MIN;
    d_tl->key = cserdata(dcmn)->key;
    d_tl->hash_populated = true;

    return (ddsi_serdata_t*) d_tl;
}

bool serdata_typeless_to_sample(
  const struct ddsi_sertype* type,
  const struct ddsi_serdata* dcmn, void* sample,
  void** bufptr, void* buflim)
{
    // TODO
    (void)type;
    (void)bufptr;
    (void)buflim;
    (void)sample;
    (void)dcmn;

    printf("Passing through typeless\n");

    return true;
}

void serdata_free(struct ddsi_serdata* dcmn)
{
    if (dcmn->kind == SDK_DATA && serdata(dcmn)->sample != NULL) {
        // Technically during a full on crash we can deadlock here.
        PyGILState_STATE state = PyGILState_Ensure();
        py_release_ref(serdata(dcmn)->sample);
        PyGILState_Release(state);
    }

    free(serdata(dcmn)->data);
    free(dcmn);
    trace
}

size_t serdata_print(const struct ddsi_sertype* tpcmn, const struct ddsi_serdata* dcmn, char* buf, size_t bufsize)
{
    (void)tpcmn;

    //ddspy_serdata_ensure_sample(cserdata(dcmn));

    PyGILState_STATE state = PyGILState_Ensure();

    PyObject* repr = PyObject_Repr(cserdata(dcmn)->sample);
    PyObject* str = PyUnicode_AsEncodedString(repr, "utf-8", "~E~");
    const char *bytes = PyBytes_AS_STRING(str);

    strncpy(buf, bytes, bufsize);

    Py_XDECREF(repr);
    Py_XDECREF(str);

    PyGILState_Release(state);

    return 0;
}

void serdata_get_keyhash(const ddsi_serdata_t* d, struct ddsi_keyhash* buf, bool force_md5)
{
    if (force_md5 && !(((const ddspy_sertype_t*) d->type)->key_maxsize_bigger_16))
    {
        /// Since the maxkeysize < 16 the key is normally not md5 encoded
        /// We encode the key we already computed to avoid diving into python again
        ddsrt_md5_state_t md5st;
        ddsrt_md5_init(&md5st);
        ddsrt_md5_append(&md5st, cserdata(d)->key.value, 16);
        ddsrt_md5_finish(&md5st, buf->value);
    }
    else
    {
        memcpy(buf->value, cserdata(d)->key.value, 16);
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
    PyGILState_STATE state = PyGILState_Ensure();

    Py_XDECREF(((ddspy_sertype_t*) tpcmn)->my_py_type);
    Py_XDECREF(((ddspy_sertype_t*) tpcmn)->deserialize_attr);
    Py_XDECREF(((ddspy_sertype_t*) tpcmn)->serialize_attr);
    Py_XDECREF(((ddspy_sertype_t*) tpcmn)->key_calc_attr);
    Py_XDECREF(((ddspy_sertype_t*) tpcmn)->keyhash_calc_attr);

    ddsi_sertype_fini(tpcmn);

    PyGILState_Release(state);
}

void sertype_zero_samples(const struct ddsi_sertype* d, void* _sample, size_t size)
{
    (void) d;

    ddspy_sample_container_t *sample = (ddspy_sample_container_t*) _sample;

    for(size_t i = 0; i < size; ++i) {
        (sample+i)->sample = NULL;
        // TODO: decrease ref here
    }

    return;
}

void sertype_realloc_samples(void** ptrs, const struct ddsi_sertype* d, void* sample, size_t old, size_t new)
{
    ddspy_sample_container_t* newsamples = (ddspy_sample_container_t*) malloc(new * sizeof(ddspy_sample_container_t));

    if (sample == NULL) {
        // Initial alloc
        for(size_t i = 0; i < new; ++i)
            (newsamples+i)->sample = NULL;
        *ptrs = newsamples;
        return;
    }
    if (new > old) {
        memcpy(newsamples, sample, old * sizeof(ddspy_sample_container_t));

        for(size_t i = old; i < new; ++i)
            (newsamples+i)->sample = NULL;
    }
    else {
        ddspy_sample_container_t* newsamples = (ddspy_sample_container_t*) malloc(new * sizeof(ddspy_sample_container_t));
        memcpy(newsamples, sample, new * sizeof(ddspy_sample_container_t));
        sertype_zero_samples(d, ((ddspy_sample_container_t*) sample) + old, old - new);
    }

    free(sample);
    *ptrs = newsamples;
}

void sertype_free_samples(const struct ddsi_sertype* d, void** ptrs, size_t size, dds_free_op_t op)
{
    sertype_zero_samples(d, *ptrs, size);

    if (op & DDS_FREE_ALL_BIT) {
        free(*ptrs);
        *ptrs = NULL;
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


ddspy_sertype_t *ddspy_sertype_new(PyObject *pytype)
{
    ddspy_sertype_t *new = (ddspy_sertype_t*) malloc(sizeof(ddspy_sertype_t));
    py_take_ref(pytype);

    /// Check all return values
    PyObject *cdr = PyObject_GetAttrString(pytype, "cdr");
    if (!valid_topic_py_or_set_error(cdr)) return NULL;

    PyObject* pyname = PyObject_GetAttrString(cdr, "typename");
    if (!valid_topic_py_or_set_error(pyname)) return NULL;

    PyObject* pykeyless = PyObject_GetAttrString(cdr, "keyless");
    if (!valid_topic_py_or_set_error(pykeyless)) return NULL;

    const char *name = PyUnicode_AsUTF8(pyname);
    bool keyless = pykeyless == Py_True;

    ddsi_sertype_init(
        &(new->my_c_type),
        name,
        &ddspy_sertype_ops,
        &ddspy_serdata_ops,
        keyless
    );
    Py_DECREF(pyname);
    Py_DECREF(pykeyless);

    new->my_py_type = pytype;

    PyObject* finalize = PyObject_GetAttrString(cdr, "finalize");
    if (!valid_topic_py_or_set_error(finalize)) return NULL;
    PyObject* args = PyTuple_New(0);
    PyObject* result = PyObject_CallObject(finalize, args);
    Py_DECREF(args);
    Py_DECREF(finalize);
    Py_XDECREF(result);

    new->deserialize_attr = PyObject_GetAttrString(cdr, "deserialize");
    new->serialize_attr = PyObject_GetAttrString(cdr, "serialize");
    new->key_calc_attr = PyObject_GetAttrString(cdr, "key");
    new->keyhash_calc_attr = PyObject_GetAttrString(cdr, "keyhash");

    if (!valid_topic_py_or_set_error(new->deserialize_attr) ||
        !valid_topic_py_or_set_error(new->serialize_attr) ||
        !valid_topic_py_or_set_error(new->key_calc_attr) ||
        !valid_topic_py_or_set_error(new->keyhash_calc_attr))
        return NULL;

    PyObject* pykeysize = PyObject_GetAttrString(cdr, "key_max_size");
    if (!valid_topic_py_or_set_error(pykeysize)) return NULL;

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

    Py_DECREF(cdr);

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

    sts = dds_create_topic_sertype(participant, name, (void**) &rsertype, qos, listener, NULL);

    if (PyErr_Occurred()) return NULL;

    return PyLong_FromLong((long)sts);
}

static PyObject *
ddspy_write(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;

    if (!PyArg_ParseTuple(args, "iO", &writer, &container.sample))
        return NULL;

    sts = dds_write(writer, &container);

    return PyLong_FromLong((long) sts);
}

static PyObject *
ddspy_dispose(PyObject *self, PyObject *args)
{
    ddspy_sample_container_t container;
    dds_entity_t writer;
    dds_return_t sts;

    if (!PyArg_ParseTuple(args, "iO", &writer, &container.sample))
        return NULL;

    sts = dds_dispose(writer, &container);

    return PyLong_FromLong((long) sts);
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
    }

    sts = dds_read(reader, rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < sts; ++i) {
        PyList_SetItem(list, i, container[i].sample);
        py_return_ref(container[i].sample);
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
    }

    sts = dds_take(reader, rcontainer, info, N, N);
    if (sts < 0) {
        return PyLong_FromLong((long) sts);
    }

    PyObject* list = PyList_New(sts);

    for(int i = 0; i < sts; ++i) {
        PyList_SetItem(list, i, container[i].sample);
        py_return_ref(container[i].sample);
    }
    free(info);
    free(container);
    free(rcontainer);

    return list;
}

char ddspy_docs[] = "DDSPY module";

PyMethodDef ddspy_funcs[] = {
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
    {	"ddspy_write",
		(PyCFunction)ddspy_write,
		METH_VARARGS,
		ddspy_docs},
    {	"ddspy_dispose",
		(PyCFunction)ddspy_dispose,
		METH_VARARGS,
		ddspy_docs},
	{	NULL}
};

char ddspymod_docs[] = "This is hello world module.";

PyModuleDef ddspy_mod = {
	PyModuleDef_HEAD_INIT,
	"ddspy",
	ddspymod_docs,
	-1,
	ddspy_funcs,
	NULL,
	NULL,
	NULL,
	NULL
};

PyMODINIT_FUNC PyInit_ddspy(void) {
	return PyModule_Create(&ddspy_mod);
}
