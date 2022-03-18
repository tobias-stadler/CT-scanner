#ifndef DEFUTIL_H
#define DEFUTIL_H

#include <string.h>

//String helper functions
#define ENDS_WITH(str, ext) (!strcasecmp(&str[strlen(str) - sizeof(ext) + 1], ext))
#define STARTS_WITH(str, start) (!strncasecmp(str, start, strlen(start)))


#endif
