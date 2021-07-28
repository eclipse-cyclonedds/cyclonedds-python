#include "util.h"


FILE* open_file(const char *pathname, const char *mode)
{
#if _WIN32
    FILE *handle = NULL;
    if (fopen_s(&handle, pathname, mode) != 0)
        return NULL;
    return handle;
#else
    return fopen(pathname, mode);
#endif
}