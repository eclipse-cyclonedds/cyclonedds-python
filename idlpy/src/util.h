#ifndef IDLPY_UTIL_H
#define IDLPY_UTIL_H

#ifdef WIN32
#include <direct.h>
#define mkdir(dir, mode) _mkdir(dir)
#else
#include <sys/stat.h>
#endif
#include <stdio.h>

FILE* open_file(const char *pathname, const char *mode);

#endif // IDLPY_UTIL_H