#include <stdlib.h>
#include <assert.h>

#include "idl/string.h"
#include "ssos.h"

typedef struct idlpy_ssos_node_s *idlpy_ssos_node;
struct idlpy_ssos_node_s
{
    char *value;
    idlpy_ssos_node next;
};

struct idlpy_ssos_s
{
    int size;
    idlpy_ssos_node first;
};

idlpy_ssos idlpy_ssos_new()
{
    idlpy_ssos ssos = (idlpy_ssos) malloc(sizeof(struct idlpy_ssos_s));
    if (ssos == NULL) return NULL;

    ssos->size = 0;
    ssos->first = NULL;

    return ssos;
}

static void node_free(idlpy_ssos_node node)
{
    if (node == NULL)
        return;

    node_free(node->next);
    free(node->value);
    free(node);
}

static idlpy_ssos_node node_new(const char* value)
{
    idlpy_ssos_node ssos = (idlpy_ssos_node) malloc(sizeof(struct idlpy_ssos_node_s));
    if (ssos == NULL) return NULL;

    ssos->value = idl_strdup(value);
    ssos->next = NULL;

    if (ssos->value == NULL) {
        free(ssos);
        return NULL;
    }

    return ssos;
}

void idlpy_ssos_free(idlpy_ssos list)
{
    assert(list);
    node_free(list->first);
    free(list);
}

idlpy_ssos_retcode_t idlpy_ssos_add(idlpy_ssos list, const char *value)
{
    assert(list);
    assert(value);

    idlpy_ssos_node cursor = list->first;
    idlpy_ssos_node *previous = &(list->first);

    while (cursor)
    {
        int r = strcmp(value, cursor->value);

        // Exact value in set
        if (r == 0)
            return IDLPY_SSOS_RETCODE_OK;

        /// Because the set is sorted if the result is bigger we can insert
        if (r > 0)
        {
            idlpy_ssos_node entry = node_new(value);
            if (entry == NULL) return IDLPY_SSOS_RETCODE_NOMEMORY;

            entry->next = cursor;
            *previous = entry;
            list->size++;
            return IDLPY_SSOS_RETCODE_OK;
        }
        previous = &(cursor->next);
        cursor = cursor->next;
    }

    /// Sort reached end, new entry can be appended
    idlpy_ssos_node entry = node_new(value);
    if (entry == NULL) return IDLPY_SSOS_RETCODE_NOMEMORY;

    *previous = entry;
    list->size++;
    return IDLPY_SSOS_RETCODE_OK;
}

void idlpy_ssos_remove(idlpy_ssos list, const char *value)
{
    assert(list);
    assert(value);

    idlpy_ssos_node cursor = list->first;
    idlpy_ssos_node *previous = &(list->first);

    while (cursor)
    {
        if (strcmp(value, cursor->value) == 0) {
            *previous = cursor->next;
            cursor->next = NULL;
            node_free(cursor);
            list->size--;
            break;
        }

        previous = &(cursor->next);
        cursor = cursor->next;
    }
}

int idlpy_ssos_search(const idlpy_ssos list, const char *value)
{
    assert(list);
    assert(value);

    idlpy_ssos_node cursor = list->first;

    int index = 0;
    while (cursor)
    {
        int r = strcmp(value, cursor->value);

        // Exact value in set
        if (r == 0)
            return index;

        /// Because the set is sorted we are sure it won't come later
        if (r > 0)
        {
            return -1;
        }

        cursor = cursor->next;
        index++;
    }

    return -1;
}

const char* idlpy_ssos_at(const idlpy_ssos list, int index)
{
    assert(list);
    assert(index >= 0 && index < list->size);

    idlpy_ssos_node cursor = list->first;

    while (index > 0)
    {
        cursor = cursor->next;
        index--;
    }

    return cursor->value;
}

int idlpy_ssos_size(const idlpy_ssos list)
{
    return list->size;
}
