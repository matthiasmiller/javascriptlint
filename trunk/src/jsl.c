/* -*- Mode: C; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 4 -*-
 *
 * ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Mozilla Communicator client code, released
 * March 31, 1998.
 *
 * The Initial Developer of the Original Code is
 * Netscape Communications Corporation.
 * Portions created by the Initial Developer are Copyright (C) 1998
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either of the GNU General Public License Version 2 or later (the "GPL"),
 * or the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

/*
 * JavaScript lint.
 */
#include "jsstddef.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "jstypes.h"
#include "jsarena.h"
#include "jsutil.h"
#include "jsprf.h"
#include "jsapi.h"
#include "jsatom.h"
#include "jscntxt.h"
#include "jsdbgapi.h"
#include "jsemit.h"
#include "jsfun.h"
#include "jsgc.h"
#include "jslock.h"
#include "jsobj.h"
#include "jsparse.h"
#include "jsscope.h"
#include "jsscript.h"
#include "jsstr.h"

#ifdef XP_UNIX
#include <unistd.h>
#include <sys/types.h>
#include <dirent.h>
#include <sys/wait.h>
#include <sys/stat.h>
#endif

#if defined(XP_WIN) || defined(XP_OS2)
#include <io.h>     /* for isatty() */
#endif

#ifdef WIN32
#include <windows.h> /*to find files*/
#include <direct.h>
#include <conio.h>
#endif

#define JSL_VERSION "0.1f"

/* exit code values */
#define EXITCODE_JS_WARNING 1
#define EXITCODE_USAGE_OR_CONFIGERR 2
#define EXITCODE_JS_ERROR 3
#define EXITCODE_FILE_ERROR 4

/* file constants */
#define MAXPATHLEN 1024

#ifdef WIN32
#define DEFAULT_DIRECTORY_SEPARATOR '\\'
#else
#define DEFAULT_DIRECTORY_SEPARATOR '/'
#endif

#ifdef WIN32
#ifndef INVALID_FILE_ATTRIBUTES
#define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
#endif
#endif

/* configuration constants */
#define MAX_CONF_LINE 500

typedef enum {
    JSL_PLACEHOLDER_FILE,
    JSL_PLACEHOLDER_LINE,
    JSL_PLACEHOLDER_COL,
    JSL_PLACEHOLDER_ERROR,
    JSL_PLACEHOLDER_ERROR_NAME,
    JSL_PLACEHOLDER_ERROR_PREFIX,
    JSL_PLACEHOLDER_ERROR_MSGENC,
    JSLPlaceholder_Limit
} JSLPlaceholder;

const char *placeholders[] = {
    "__FILE__",
    "__LINE__",
    "__COL__",
    "__ERROR__",
    "__ERROR_NAME__",
    "__ERROR_PREFIX__",
    "__ERROR_MSGENC__"
};


/* Warning information */
#define IS_JSL_WARNING_MSG(errnum) ((errnum) > JSMSG_START_LINT_MESSAGES)

#define CAN_DISABLE_WARNING(errnum) ((IS_JSL_WARNING_MSG(errnum) || \
    ((errnum) == JSMSG_NO_RETURN_VALUE) || \
    ((errnum) == JSMSG_DUPLICATE_FORMAL) || \
    ((errnum) == JSMSG_EQUAL_AS_ASSIGN) || \
    ((errnum) == JSMSG_VAR_HIDES_ARG) || \
    ((errnum) == JSMSG_REDECLARED_VAR) || \
    ((errnum) == JSMSG_ANON_NO_RETURN_VALUE) || \
    ((errnum) == JSMSG_USELESS_EXPR)) && \
    ((errnum) != JSMSG_UNDECLARED_IDENTIFIER) && \
    ((errnum) != JSMSG_INVALID_CONTROL_COMMENT))

#define WARNING_PREFIX          "warning";
#define STRICT_WARNING_PREFIX   "warning";
#define LINT_WARNING_PREFIX     "lint warning";

char *errorNames[JSErr_Limit] = {
#define MSG_DEF(name, number, count, exception, format) #name,
#include "js.msg"
#undef MSG_DEF
};

/* globals */
int gExitCode = 0;
int gNumWarnings = 0, gNumErrors = 0;

typedef enum {
    JSL_FILETYPE_UNKNOWN,
    JSL_FILETYPE_JS,
    JSL_FILETYPE_HTML
} JSLFileType;

typedef struct JSLScriptDependencyList {
    JSCList links;
    struct JSLScriptList *script;
} JSLScriptDependencyList;

typedef struct JSLPathList {
    JSCList links;
    char path[MAXPATHLEN+1];
} JSLPathList;

typedef struct JSLScriptList {
    JSCList links;

    char path[MAXPATHLEN+1];
    JSObject *obj;
    JSLScriptDependencyList directDependencies;
} JSLScriptList;

JSLScriptList gScriptList;


/* settings */
JSBool gAlwaysUseOptionExplicit = JS_FALSE;
JSBool gRecurse = JS_FALSE;
JSBool gShowContext = JS_TRUE;
// Error format; this is the default for backward compatibility reasons
char gOutputFormat[MAX_CONF_LINE+1] = "__FILE__(__LINE__): __ERROR__";
#ifdef WIN32
JSBool gPauseAtEnd = JS_FALSE;
#endif

JSBool showErrMsgs[JSErr_Limit] = {
#define MSG_DEF(name, number, count, exception, format) \
    (number != JSMSG_BLOCK_WITHOUT_BRACES && \
    number != JSMSG_MISSING_OPTION_EXPLICIT),
#include "js.msg"
#undef MSG_DEF
};


/* compatibility */

#ifdef WIN32
#define strcasecmp(src, dest) stricmp((src), (dest))
#define strncasecmp(src, dest, count) strnicmp((src), (dest), (count))
#endif

#ifdef WIN32
#define path_cmp(src, dest) strcasecmp((src), (dest))
#else
#define path_cmp(src, dest) strcmp((src), (dest))
#endif


static const char *
GetFileName(const char *path);

/*
 * From http://xoomer.virgilio.it/acantato/dev/wildcard/wildmatch.html:
 *
 * I found this on a Walnut Creek CD (C/C++ user group library).
 *
 * The original code is from the C/C++ Users Journal. The author is Mike Cornelison.
 * No use restriction is mentioned in the source file or the other files I found in the CD.
 *
 * NOTE: Renamed function and modified not to use mapCaseTable.
 */
static JSBool
PathMatchesWildcards(const char *pat, const char *str) {
   int i, star;

new_segment:

   star = 0;
   if (*pat == '*') {
      star = 1;
      do { pat++; } while (*pat == '*'); /* enddo */
   } /* endif */

test_match:

   for (i = 0; pat[i] && (pat[i] != '*'); i++) {
      if (toupper(str[i]) != toupper(pat[i])) {
         if (!str[i]) return 0;
         if ((pat[i] == '?') && (str[i] != '.')) continue;
         if (!star) return 0;
         str++;
         goto test_match;
      }
   }
   if (pat[i] == '*') {
      str += i;
      pat += i;
      goto new_segment;
   }
   if (!str[i]) return 1;
   if (i && pat[i - 1] == '*') return 1;
   if (!star) return 0;
   str++;
   goto test_match;
}

#ifdef WIN32

static JSBool
IsDir(char *path)
{
    DWORD attr = GetFileAttributes(path);
    return attr != INVALID_FILE_ATTRIBUTES &&
        (attr & FILE_ATTRIBUTE_DIRECTORY) != 0;
}

#else

static JSBool
IsDir(char *filename)
{
    struct stat tmp;
    if (stat(filename, &tmp) >= 0) {
        return (tmp.st_mode & S_IFMT) == S_IFDIR;
    }
    else
        return JS_FALSE;
}

#endif




#ifdef WIN32

struct dirent {
    char d_name[MAXPATHLEN];
};

typedef struct DIR {
    long handle;
    JSBool more;
    struct _finddata_t finddata;
    struct dirent cur;
} DIR;

static DIR*
opendir(const char *name)
{
    char *qualifiedPath;
    DIR *dir;

    dir = malloc(sizeof(DIR));
    if (!dir)
        return NULL;
    memset(dir, 0, sizeof(DIR));

    /* do the find */
    qualifiedPath = JS_smprintf("%s\\*", name);
    dir->handle = _findfirst(qualifiedPath, &dir->finddata);
    JS_smprintf_free(qualifiedPath);

    if (dir->handle > 0) {
        dir->more = JS_TRUE;
        return dir;
    }
    else if (errno == ENOENT) {
        dir->more = JS_FALSE;
        return dir;
    }
    else {
        free(dir);
        return NULL;
    }
}

static
struct dirent *readdir(DIR *dir)
{
    if (!dir || !dir->more)
        return NULL;

    /* copy name */
    strcpy(dir->cur.d_name, dir->finddata.name);
    /* more? */
    dir->more = (_findnext(dir->handle, &dir->finddata) >= 0);
    return &dir->cur;
};

static int
closedir(DIR *dir)
{
    if (dir) {
        _findclose(dir->handle);
        memset(dir, 0, sizeof(DIR));
        free (dir);
    }
    return 0;
}

/* caller should allocate MAXPATHLEN; does not set errno; returns null on failure */
static char *
JSL_RealPath(const char *path, char *resolved_path)
{
	int ret = GetFullPathName(path, _MAX_PATH, resolved_path, NULL);
	if (!ret || ret > _MAX_PATH) {
		return NULL;
	}
	return resolved_path;
}

#else

static const char *
JSL_RealPath(const char *path, char *resolved_path)
{
    char *folder, *resolved;
    const char *file;

    resolved = realpath(path, resolved_path);
    if (resolved)
        return resolved;

    /* get the folder name */
    file = GetFileName(path);
    folder = JS_smprintf("%s%c", path, DEFAULT_DIRECTORY_SEPARATOR);
    folder[file - path] = 0;

    resolved = realpath(folder, resolved_path);
    JS_smprintf_free(folder);

    if (resolved) {
        char dirSeparator[] = { DEFAULT_DIRECTORY_SEPARATOR, 0 };
        strcat(resolved, dirSeparator);
        strcat(resolved, file);
    }
    return resolved;
}

#endif



static void
SetExitCode(int level)
{
    if (level > gExitCode)
        gExitCode = level;
}

static const char *
GetFileName(const char *path)
{
    const char *file, *tmp;
    file = strrchr(path, '/');
    tmp = strrchr(path, '\\');
    if (tmp && (!file || file < tmp)) {
        file = tmp;
    }
    if (file)
        file++;
    else
        file = path;
    return file;
}

#define COUNT_AND_SKIP_NEWLINES(bufptr, lineno) \
    do { \
        if (*(bufptr) == '\r') { \
            (lineno)++; \
            (bufptr)++; \
            if (*(bufptr) == '\n') \
                (bufptr)++; \
        } \
        else if (*(bufptr) == '\n') { \
            (lineno)++; \
            (bufptr)++; \
        } \
        else \
            break; \
    } while (1)

/* lineno may be zero if line number is not given */
static void
OutputErrorMessage(const char *filename, int lineno, int colno, const char *errName,
                   const char *messagePrefix, const char *message)
{
    const char *formatPos;
    formatPos = gOutputFormat;

    while (JS_TRUE) {
        int i;
        JSLPlaceholder placeholderType;
        const char *placeholderPos;

        placeholderType = JSLPlaceholder_Limit;
        placeholderPos = NULL;

        for (i = 0; i < JSLPlaceholder_Limit; i++) {
            const char *tmp;
            tmp = strstr(formatPos, placeholders[i]);
            if (tmp && (!placeholderPos || tmp < placeholderPos))
            {
                placeholderType = i;
                placeholderPos = tmp;
            }
        }

        /* print any skip any skipped text */
        if (placeholderPos) {
            while (formatPos < placeholderPos) {
                fputc(*formatPos, stdout);
                formatPos++;
            }
        }

        switch (placeholderType) {
          case JSL_PLACEHOLDER_FILE:
            if (filename)
                fputs(filename, stdout);
            break;

          case JSL_PLACEHOLDER_LINE:
            if (lineno) {
                char *tmp;
                tmp = JS_smprintf("%i", lineno);
                fputs(tmp, stdout);
                JS_smprintf_free(tmp);
            }
            else {
                fputc('?', stdout);
            }
            break;

          case JSL_PLACEHOLDER_COL:
            if (colno) {
                char *tmp;
                tmp = JS_smprintf("%i", colno);
                fputs(tmp, stdout);
                JS_smprintf_free(tmp);
            }
            else {
                fputc('?', stdout);
            }
            break;

          case JSL_PLACEHOLDER_ERROR:
            if (messagePrefix)
                fputs(messagePrefix, stdout);
            if (messagePrefix && message)
                fputs(": ", stdout);
            if (message)
                fputs(message, stdout);
            break;

          case JSL_PLACEHOLDER_ERROR_NAME:
            if (errName) {
                const char *tmp;
                tmp = errName;
                while (*tmp) {
                    fputc(tolower(*tmp), stdout);
                    tmp++;
                }
            }
            break;

          case JSL_PLACEHOLDER_ERROR_PREFIX:
            if (messagePrefix)
                fputs(messagePrefix, stdout);
            break;

          case JSL_PLACEHOLDER_ERROR_MSGENC:
            if (message) {
                const char *tmp;
                tmp = message;
                while (*tmp) {
                    if (*tmp == '\\')
                        fputs("\\\\", stdout);
                    else if (*tmp == '\r')
                        fputs("\\r", stdout);
                    else if (*tmp == '\n')
                        fputs("\\n", stdout);
                    else
                        fputc(*tmp, stdout);
                    tmp++;
                }
            }
            break;

          case JSLPlaceholder_Limit:
          default:
            JS_ASSERT(!placeholderPos);
            fputs(formatPos, stdout);
            fputc('\n', stdout);
            return;
        }

        /* only called if there was a placeholder; skip the placeholder */
        JS_ASSERT(placeholderPos);
        formatPos += strlen(placeholders[placeholderType]);
    }
}

static JSLPathList*
AllocPathListItem(const char *path)
{
    JSLPathList *pathItem;

    /* alloc */
    pathItem = malloc(sizeof(JSLPathList));
    memset(pathItem, 0, sizeof(JSLPathList));

    /* init path */
    JS_INIT_CLIST(&pathItem->links);
    strncpy(pathItem->path, path, MAXPATHLEN);

    return pathItem;
}

/* returns false if already in list */
static void
AddPathToList(JSLPathList *pathList, const char *path)
{
    JSLPathList *pathItem;
    pathItem = AllocPathListItem(path);
    JS_APPEND_LINK(&pathItem->links, &pathList->links);
}

static JSLScriptList*
AllocScriptListItem(JSContext *cx, const char *path)
{
    JSLScriptList *script;

    /* alloc */
    script = malloc(sizeof(JSLScriptList));
    memset(script, 0, sizeof(JSLScriptList));

    /* init path */
    JS_INIT_CLIST(&script->links);
    strncpy(script->path, path, MAXPATHLEN);

    /* init object */
    script->obj = JS_NewObject(cx, NULL, NULL, NULL);

    /* init depends */
    JS_INIT_CLIST(&script->directDependencies.links);
    script->directDependencies.script = NULL;

    return script;
}

/* returns false if already in list */
static JSBool
AddNewScriptToList(JSContext *cx, const char *path, JSLScriptList **script)
{
    JSLScriptList *cur;
    cur = (JSLScriptList*)JS_LIST_HEAD(&gScriptList.links);

    while (cur != &gScriptList) {
        if (path_cmp(path, cur->path) == 0) {
            if (script)
                *script = cur;
            return JS_FALSE;
        }
        cur = (JSLScriptList*)JS_NEXT_LINK(&cur->links);
    }

    cur = AllocScriptListItem(cx, path);
    JS_APPEND_LINK(&cur->links, &gScriptList.links);

    if (script)
        *script = cur;
    return JS_TRUE;
}

static void
AddDirectDependency(JSLScriptDependencyList *dependencies, JSLScriptList *dependencyScript)
{
    /* create dependency item */
    JSLScriptDependencyList *dependency;
    dependency = malloc(sizeof(JSLScriptDependencyList));
    memset(dependency, 0, sizeof(JSLScriptDependencyList));
    dependency->script = dependencyScript;

    /* add to list */
    JS_APPEND_LINK(&dependency->links, &dependencies->links);
}

static JSBool
IsObjectInList(JSLObjectList *dependencies, JSObject *dependency)
{
    JSLObjectList *cur = (JSLObjectList*)JS_LIST_HEAD(&dependencies->links);
    while (cur != dependencies) {
        if (cur->obj == dependency)
            return JS_TRUE;

        cur = (JSLObjectList*)JS_NEXT_LINK(&cur->links);
    }

    return JS_FALSE;
}

static void
AddObjectToList(JSLObjectList *dependencies, JSObject *dependency)
{
    /* create list object item */
    JSLObjectList *listItem;
    listItem = malloc(sizeof(JSLObjectList));
    memset(listItem, 0, sizeof(JSLObjectList));
    listItem->obj = dependency;

    /* add to list */
    JS_APPEND_LINK(&listItem->links, &dependencies->links);
}

static void
LoadScriptDependencies(JSLObjectList *dependencies, JSLScriptList *script)
{
    /* load script dependencies for direct dependencies */
    JSLScriptDependencyList *cur = (JSLScriptDependencyList*)JS_LIST_HEAD(&script->directDependencies.links);
    while (cur != &script->directDependencies) {
        /* check recursion */
        if (!IsObjectInList(dependencies, cur->script->obj)) {
            AddObjectToList(dependencies, cur->script->obj);
            LoadScriptDependencies(dependencies, cur->script);
        }
        cur = (JSLScriptDependencyList*)JS_NEXT_LINK(&cur->links);
    }
}


static JSBool
ProcessScriptContents(JSContext *cx, JSObject *obj, JSLFileType type,
                      const char *path, const char *contents,
                      JSLImportCallback callback, void *callbackParms);

static JSBool
ProcessSingleScript(JSContext *cx, JSObject *obj, const char *relpath, JSLScriptList *parentScript);


typedef struct JSLImportScriptParms {
    JSObject *obj;
    JSLScriptList *script;
    JSLObjectList *dependencies;
} JSLImportScriptParms;

static void
ImportScript(JSContext *cx, const char *path, void *parms)
{
    JSLImportScriptParms *importParms = (JSLImportScriptParms*)parms;
    ProcessSingleScript(cx, importParms->obj, path, importParms->script);
    LoadScriptDependencies(importParms->dependencies, importParms->script);
}

/* no-case comparison */
static JSBool
EndsWithSuffixNoCase(const char *s1, const char *s2)
{
    int len1, len2;
    len1 = strlen(s1);
    len2 = strlen(s2);

    if (len1 < len2)
        return JS_FALSE;

    return strcasecmp(s1 + len1 - len2, s2) == 0;
}

static JSLFileType
GetFileTypeFromPath(const char *path)
{
    const char *basename;
    int len;

    basename = GetFileName(path);
    len = strlen(basename);

    if (EndsWithSuffixNoCase(basename, ".js"))
        return JSL_FILETYPE_JS;

    if (EndsWithSuffixNoCase(basename, ".htm") ||
        EndsWithSuffixNoCase(basename, ".html")) {
        return JSL_FILETYPE_HTML;
    }

    return JSL_FILETYPE_UNKNOWN;
}

static JSBool
ProcessSingleScript(JSContext *cx, JSObject *obj, const char *relpath, JSLScriptList *parentScript)
{
    JSLImportScriptParms importParms;
    char filename[MAXPATHLEN+1];
    long fileSize;
    char *contents;
    JSLScriptList *scriptInfo;
    JSLObjectList dependencies;
    JSBool tmp_result;
    FILE *file;

    tmp_result = JS_FALSE;

    if (parentScript) {
        /* resolve relative paths */
        char workingDir[MAXPATHLEN+1];
        const char *basename;
        char *folder;

        /* get the folder name */
        basename = GetFileName(parentScript->path);
        folder = JS_smprintf("%s%c", parentScript->path, DEFAULT_DIRECTORY_SEPARATOR);
        folder[basename - parentScript->path] = DEFAULT_DIRECTORY_SEPARATOR;
        folder[basename - parentScript->path + 1] = 0;

        /* change folder to handle relative paths */
        workingDir[0] = 0;
        getcwd(workingDir, sizeof(workingDir));
        chdir(folder);
        JS_smprintf_free(folder);

        tmp_result = (JSL_RealPath(relpath, filename) != NULL);
        chdir(workingDir);
    }
    else {
        tmp_result = (JSL_RealPath(relpath, filename) != NULL);
    }

    if (!tmp_result) {
        OutputErrorMessage(relpath, 0, 0, NULL, NULL, "unable to resolve path");
        SetExitCode(EXITCODE_FILE_ERROR);
        return JS_FALSE;
	}

    /* returns false if already in list */
    tmp_result = AddNewScriptToList(cx, filename, &scriptInfo);
    if (parentScript)
        AddDirectDependency(&parentScript->directDependencies, scriptInfo);
    if (!tmp_result)
        return JS_TRUE;

    fputs(GetFileName(filename), stdout);
    fputc('\n', stdout);

    file = fopen(filename, "r");
    if (!file) {
        OutputErrorMessage(filename, 0, 0, NULL, "can't open file", strerror(errno));
        SetExitCode(EXITCODE_FILE_ERROR);
        return JS_FALSE;
    }

    /* seek to the send to determine file size*/
    if (fseek(file, 0, SEEK_END) != 0 ||
        (fileSize = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {

        fclose(file);
        OutputErrorMessage(filename, 0, 0, NULL, "can't read file", strerror(errno));
        SetExitCode(EXITCODE_FILE_ERROR);
        return JS_FALSE;
    }

    /* alloc memory */
    contents = (char*)JS_malloc(cx, fileSize+1);
    if (contents == NULL) {
        fclose(file);
        OutputErrorMessage(filename, 0, 0, NULL, "can't read file", "out of memory");
        SetExitCode(EXITCODE_FILE_ERROR);
        return JS_FALSE;
    }

    /* read file */
    fileSize = fread(contents, 1, fileSize, file);
    if (ferror(file)) {
        fclose(file);
        JS_free(cx, contents);
        OutputErrorMessage(filename, 0, 0, NULL, "can't read file", strerror(errno));
        SetExitCode(EXITCODE_FILE_ERROR);
        return JS_FALSE;
    }
    contents[fileSize] = 0;
    fclose(file);

    JS_INIT_CLIST(&dependencies.links);
    LoadScriptDependencies(&dependencies, scriptInfo);

    importParms.obj = obj;
    importParms.script = scriptInfo;
    importParms.dependencies = &dependencies;

    if (JS_PushLintIdentifers(cx, scriptInfo->obj, &dependencies,
                              gAlwaysUseOptionExplicit, ImportScript, &importParms)) {
        tmp_result = ProcessScriptContents(cx, obj, GetFileTypeFromPath(filename), filename,
            contents, ImportScript, &importParms);
        JS_PopLintIdentifers(cx);
    }
    else {
        SetExitCode(EXITCODE_JS_ERROR);
        tmp_result = JS_FALSE;
    }

    /* free object list */
    while (!JS_CLIST_IS_EMPTY(&dependencies.links)) {
        JSLObjectList *dependency;
        dependency = (JSLObjectList*)JS_LIST_HEAD(&dependencies.links);
        JS_REMOVE_LINK(&dependency->links);
    }

    JS_free(cx, contents);
    return tmp_result;
}

static JSBool
ProcessScriptContents(JSContext *cx, JSObject *obj, JSLFileType type,
                      const char *path, const char *contents,
                      JSLImportCallback callback, void *callbackParms)
{
    JSScript *script;
    int lineno;
    JSBool isHTMLFile;
    JSBool containsHTMLScript, containsHTMLStartTag, containsHTMLEndTag;
    const char *contentsPos;
    contentsPos = contents;

    lineno = 1;
    isHTMLFile = JS_FALSE;
    containsHTMLScript = containsHTMLStartTag = containsHTMLEndTag = JS_FALSE;

    /* yech... */
    if (type == JSL_FILETYPE_UNKNOWN || type == JSL_FILETYPE_HTML) {
        while (*contentsPos) {
            COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
            if (!*contentsPos)
                break;

            /* see if this is disproved by garbage after the end HTML tag */
            if (isHTMLFile && !containsHTMLScript && containsHTMLStartTag && containsHTMLEndTag) {
                if (!isspace(*contentsPos))
                    isHTMLFile = JS_FALSE;
            }

            if (*contentsPos != '<') {
                contentsPos++;
                continue;
            }
            contentsPos++;

            /* skip whitespace */
            while (*contentsPos) {
                COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                if (!*contentsPos)
                    break;
                if (!isspace(*contentsPos))
                    break;
                contentsPos++;
            }
            if (!*contentsPos)
                break;

            if (containsHTMLStartTag && *contentsPos == '/') {
                contentsPos++;
                COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                if (!*contentsPos)
                    break;

                if (strncasecmp(contentsPos, "html", 4) == 0 && !isalnum(*(contentsPos+4))) {
                    contentsPos += 4;
                    COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                    if (!*contentsPos)
                        break;

                    /* skip whitespace */
                    while (*contentsPos) {
                        COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                        if (!*contentsPos)
                            break;
                        if (!isspace(*contentsPos))
                            break;
                        contentsPos++;
                    }
                    if (!*contentsPos)
                        break;

                    if (*contentsPos == '>') {
                        containsHTMLEndTag = JS_TRUE;
                        /* may be disproven later */
                        isHTMLFile = JS_TRUE;
                    }

                    contentsPos++;
                    COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                }
            }
            else if (strncasecmp(contentsPos, "html", 4) == 0 && !isalnum(*(contentsPos+4))) {
                /* html tag */
                contentsPos += 4;
                containsHTMLStartTag = JS_TRUE;
            }
            else if (strncasecmp(contentsPos, "script", 6) != 0 || isalnum(*(contentsPos+6))) {
                /* not the script tag that we're looking for */
                contentsPos++;
            }
            else {
                /* script tag */
                JSBool selfContainedTag;
                const char *startOfScript, *endOfScript;
                int lineStartOfScript;
                contentsPos += 6;

                selfContainedTag = JS_FALSE;

                /* find start of script */
                lineStartOfScript = 0;
                startOfScript = NULL;
                endOfScript = NULL;
                while (*contentsPos) {
                    JSBool inSrcAttr;
                    inSrcAttr = JS_FALSE;

                    COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                    if (!*contentsPos)
                        break;

                    /* check if previous char was space */
                    if (isspace(*(contentsPos-1)) && strncasecmp(contentsPos, "src", 3) == 0 && !isalnum(*(contentsPos+3))) {
                        contentsPos += 3;
                        COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);

                        /* skip spaces */
                        while (*contentsPos && isspace(*contentsPos)) {
                            *contentsPos++;
                            COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                        }

                        /* check for equals */
                        if (!*contentsPos || *contentsPos != '=') {
                            OutputErrorMessage(path, lineno, 0, NULL, "html error", "expected src attribute");
                            SetExitCode(EXITCODE_JS_ERROR);
                            return JS_FALSE;
                        }

                        /* skip spaces */
                        *contentsPos++;
                        COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);

                        /* force quotes on src attribute */
                        if (!*contentsPos || (*contentsPos != '\"' && *contentsPos != '\'')) {
                            OutputErrorMessage(path, lineno, 0, NULL, "html error", "missing quotes on src attribute");
                            SetExitCode(EXITCODE_JS_ERROR);
                            return JS_FALSE;
                        }

                        inSrcAttr = JS_TRUE;
                    }

                    if (*contentsPos == '\"' || *contentsPos == '\'') {
                        const char *startPos;
                        startPos = contentsPos;
                        contentsPos++;

                        while (*contentsPos) {
                            COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                            if (!*contentsPos)
                                break;
                            if (*contentsPos == *startPos) {
                                contentsPos++;
                                break;
                            }
                            contentsPos++;
                        }

                        if (inSrcAttr) {
                            int attrLen;
                            const char *err;

                            attrLen = (contentsPos-1/*point to quote*/) - (startPos + 1/*quotes*/);
                            err = NULL;

                            if (!*contentsPos) {
                                err = "unexpected end of file when looking for end of src attribute";
                            }
                            else if (attrLen > MAXPATHLEN) {
                                err = "src attribute exceeded maximum length";
                            }
                            else {
                                char srcAttr[MAXPATHLEN+1];
                                strncpy(srcAttr, startPos + 1/*quote*/, attrLen);
                                srcAttr[attrLen] = 0;

                                if (callback)
                                    callback(cx, srcAttr, callbackParms);
                            }

                            if (err) {
                                OutputErrorMessage(path, lineno, 0, NULL, "html error", err);
                                SetExitCode(EXITCODE_JS_ERROR);
                                return JS_FALSE;
                            }
                        }
                        else if (!*contentsPos)
                            break;
                    }
                    else if (*contentsPos == '/' && *(contentsPos+1) == '>') {
                        selfContainedTag = JS_TRUE;
                        contentsPos++;
                        contentsPos++;
                        break;
                    }
                    else if (*contentsPos == '>') {
                        contentsPos++;
                        startOfScript = contentsPos;
                        lineStartOfScript = lineno;
                        break;
                    }
                    else
                        contentsPos++;
                }
                while (startOfScript && *contentsPos) {
                    const char *possibleEndOfScript;
                    possibleEndOfScript = NULL;

                    COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                    if (!*contentsPos)
                        break;

                    /* tag */
                    if (*contentsPos != '<') {
                        contentsPos++;
                        continue;
                    }
                    possibleEndOfScript = contentsPos;
                    contentsPos++;
                    COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                    if (!*contentsPos)
                        break;

                    /* end tag */
                    if (*contentsPos != '/') {
                        contentsPos++;
                        continue;
                    }
                    contentsPos++;
                    COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                    if (!*contentsPos)
                        break;

                    if (strncasecmp(contentsPos, "script", 6) == 0 && !isalnum(*(contentsPos+6))) {
                        /* script end tag! */
                        contentsPos += 6;

                        while (*contentsPos) {
                            COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                            if (*contentsPos == '>') {
                                endOfScript = possibleEndOfScript;
                                break;
                            }
                            contentsPos++;
                        }
                    }
                    if (endOfScript)
                        break;
                }

                if (!selfContainedTag && (!startOfScript || !endOfScript)) {
                    OutputErrorMessage(path, lineno, 0, NULL, "html error", "unable to find end of script tag");
                    SetExitCode(EXITCODE_JS_ERROR);
                    return JS_FALSE;
                }

                isHTMLFile = JS_TRUE;
                containsHTMLScript = JS_TRUE;
                if (startOfScript != endOfScript) {
                    script = JS_CompileScript(cx, obj, startOfScript, endOfScript - startOfScript, path, lineStartOfScript);
                    if (script)
                        JS_DestroyScript(cx, script);
                    else {
                        SetExitCode(EXITCODE_JS_ERROR);
                        return JS_FALSE;
                    }
                }
            }
        }
    }

    /* if the type wasn't known, treat as JS if no hardcoded HTML tags were found */
    if ((type == JSL_FILETYPE_UNKNOWN && !isHTMLFile) ||
        type == JSL_FILETYPE_JS) {
        contentsPos = contents;

        /*
         * It's not interactive - just execute it.
         *
         * Support the UNIX #! shell hack; gobble the first line if it starts
         * with '#'.  TODO - this isn't quite compatible with sharp variables,
         * as a legal js program (using sharp variables) might start with '#'.
         * But that would require multi-character lookahead.
         */
        if (*contentsPos == '#') {
            while(contentsPos[1]) {
                if (contentsPos[1] == '\n' || contentsPos[1] == '\r')
                    break;
                contentsPos++;
            }
        }

        script = JS_CompileScript(cx, obj, contentsPos, strlen(contentsPos), path, 1);

        if (script) {
            JS_DestroyScript(cx, script);
            return JS_TRUE;
        }
        SetExitCode(EXITCODE_JS_ERROR);
        return JS_FALSE;
    }
    else {
        return JS_TRUE;
    }
}

static JSBool
ProcessScripts(JSContext *cx, JSObject *obj, char *relpath)
{
    DIR *search_dir;
    char path[MAXPATHLEN+1];
    char *folder;
    const char *file;

    struct dirent *cur;

    /* get the folder name */
    file = GetFileName(relpath);
    folder = JS_smprintf("%s%c", relpath, DEFAULT_DIRECTORY_SEPARATOR);
    folder[file - relpath] = 0;

    /* resolve relative paths */
    if (!JSL_RealPath(relpath, path)) {
        OutputErrorMessage(relpath, 0, 0, NULL, NULL, "unable to resolve path");
        SetExitCode(EXITCODE_FILE_ERROR);
        return JS_FALSE;
	}

    /* get the full folder name */
    file = GetFileName(path);
    JS_smprintf_free(folder);
    folder = JS_smprintf("%s%c", path, DEFAULT_DIRECTORY_SEPARATOR);
    folder[file - path] = 0;

    if (strchr(file, '?') != NULL || strchr(file, '*') != NULL) {
        /* this has wildcards, so do a search on this path */
        search_dir = opendir(folder);
        if (!search_dir) {
            OutputErrorMessage(relpath, 0, 0, NULL, NULL, "unable to search directory");
            SetExitCode(EXITCODE_FILE_ERROR);
            return JS_FALSE;
        }
    }
    else {
        /* see if it's a folder */
        search_dir = opendir(path);
        if (!search_dir) {
            /* if not, was this intended as a folder? */
            if (*path && (path[strlen(path)-1] == '/' || path[strlen(path)-1] == '\\')) {
                OutputErrorMessage(path, 0, 0, NULL, "can't open file", "path does not exist");
                closedir(search_dir);
                JS_free(cx, folder);
                SetExitCode(EXITCODE_FILE_ERROR);
                return JS_FALSE;
            }
            else {
                /* treat as a file */
                closedir(search_dir);
                JS_free(cx, folder);
                return ProcessSingleScript(cx, obj, path, NULL);
            }
        }
    }

    while ((cur = readdir(search_dir)) != NULL) {
        char curPath[MAXPATHLEN+1];
        char *tmp;

        curPath[0] = 0;

        if (cur->d_name[0] == '.' && (cur->d_name[1] == 0 ||
            (cur->d_name[1] == '.' && cur->d_name[2] == 0))) {
            /*single/double dot*/
            continue;
        }

        tmp = JS_smprintf("%s%s", folder, cur->d_name);
        if (!JSL_RealPath(tmp, curPath)) {
            JS_free(cx, tmp);
            closedir(search_dir);
            OutputErrorMessage(relpath, 0, 0, NULL, NULL, "unable to resolve path");
            SetExitCode(EXITCODE_FILE_ERROR);
            return JS_FALSE;
        }
        JS_free(cx, tmp);

        /* test for directory */
        if (IsDir(curPath)) {
            if (gRecurse) {
                tmp = JS_smprintf("%s%c%s", curPath, DEFAULT_DIRECTORY_SEPARATOR, file);
                ProcessScripts(cx, obj, tmp);
                JS_free(cx, tmp);
            }
        }
        else if (PathMatchesWildcards(file, cur->d_name)) {
            /* process script */
            ProcessSingleScript(cx, obj, curPath, NULL);
        }
    }

    closedir(search_dir);
    JS_free(cx, folder);
    return JS_TRUE;
}

static void
PrintConfErrName(const uintN number, const char *format)
{
    int chars;

    fputc(showErrMsgs[number] ? '+' : '-', stdout);
    fputs(errorNames[number], stdout);
    chars = 1 + strlen(errorNames[number]);

    while (chars < 25) {
        fputc(' ', stdout);
        chars++;
    }
    fputs("# ", stdout);
    fputs(format, stdout);
    fputs("\n", stdout);
}

static void
PrintDefaultConf(void)
{
    fputs(
        "#\n"
        "# JavaScript Lint " JSL_VERSION " Configuration File\n"
        "#\n"
        "# This file can be used to lint a collection of scripts, or to enable\n"
        "# or disable warnings for scripts that are linted via the command line.\n"
        "#\n"
        "\n"
        "### Warnings\n"
        "# Enable or disable warnings based on requirements.\n"
        "# Use \"+WarningName\" to display or \"-WarningName\" to suppress.\n"
        "#\n"
        , stdout);

    // keep in sync with ProcessConf
    #define MSG_DEF(name, number, count, exception, format) \
    { if (CAN_DISABLE_WARNING(number)) PrintConfErrName(number, format); }
    #include "js.msg"
    #undef MSG_DEF

    fputs(
        "\n\n### Output format\n"
        "# Customize the format of the error message.\n"
        "#    __FILE__ indicates current file\n"
        "#    __LINE__ indicates current line\n"
        "#    __ERROR__ indicates error message\n"
        "#\n"
        "# Visual Studio syntax (default):\n"
        "+output-format __FILE__(__LINE__): __ERROR__\n"
        "# Alternative syntax:\n"
        "#+output-format __FILE__:__LINE__: __ERROR__\n"
        , stdout);

    fputs(
        "\n\n### Context\n"
        "# Show the in-line position of the error.\n"
        "# Use \"+context\" to display or \"-context\" to suppress.\n"
        "#\n"
        "+context\n"
        , stdout);

    fputs(
        "\n\n### Defining identifiers\n"
        "# By default, \"option explicit\" is enabled on a per-file basis.\n"
        "# To enable this for all files, use \"+always_use_option_explicit\"\n"
        "-always_use_option_explicit\n"
        "\n"
        "# Define certain identifiers of which the lint is not aware.\n"
        "# (Use this in conjunction with the \"undeclared identifier\" warning.)\n"
        "#\n"
        "# Common uses for webpages might be:\n"
        "#+define window\n"
        "#+define document\n"
        , stdout);

#ifdef WIN32
    fputs(
        "\n\n### Interactive\n"
        "# Prompt for a keystroke before exiting.\n"
        "#+pauseatend\n"
        , stdout);
#endif

    fputs(
        "\n\n### Files\n"
        "# Specify which files to lint\n"
        "# Use \"+recurse\" to enable recursion (disabled by default).\n"
        "# To add a set of files, use \"+process FileName\", \"+process Folder\\Path\\*.js\",\n"
        "# or \"+process Folder\\Path\\*.htm\".\n"
        "#\n"
        "+process jsl-test.js\n"
        , stdout);
}

static int
usage(void)
{
    fprintf(stdout, "\nJavaScript Lint %s (%s)\n", JSL_VERSION, JS_GetImplementationVersion());
    fprintf(stdout, "usage: jsl [help:conf] [conf filename] [+recurse|-recurse] [process filename] [+context|-context]");
#ifdef WIN32
    fprintf(stdout, " [pauseatend]");
#endif
    fprintf(stdout, "\n");
    fputs(
        "\nError levels:\n"
        "  0 - success\n"
        "  1 - JavaScript warnings\n"
        "  2 - usage or configuration error\n"
        "  3 - JavaScript error\n"
        "  4 - file error\n",
        stdout);
    SetExitCode(EXITCODE_USAGE_OR_CONFIGERR);
    return EXITCODE_USAGE_OR_CONFIGERR;
}

static int
LintConfError(JSContext *cx, const char *filename, int lineno, const char *err)
{
    OutputErrorMessage(filename, lineno, 0, NULL, "configuration error", err);
    SetExitCode(EXITCODE_USAGE_OR_CONFIGERR);
    return EXITCODE_USAGE_OR_CONFIGERR;
}

static JSBool
IsValidIdentifier(const char *identifier)
{
    const char *identifierPos;

    if (!*identifier || !JS_ISIDENT_START(*identifier))
        return JS_FALSE;

    identifierPos = identifier+1;
    while (*identifierPos) {
        if (!JS_ISIDENT(*identifierPos))
            return JS_FALSE;
        identifierPos++;
    }

    return JS_TRUE;
}

static int
ProcessConf(JSContext *cx, JSObject *obj, const char *relpath, JSLPathList *processPaths)
{
    char filename[MAXPATHLEN+1];
    char line[MAX_CONF_LINE+1];
    int linelen, lineno;
    int ch;

    FILE *file;

    /* resolve relative paths */
    if (!JSL_RealPath(relpath, filename)) {
        OutputErrorMessage(relpath, 0, 0, NULL, NULL, "unable to resolve path");
        SetExitCode(EXITCODE_FILE_ERROR);
        return EXITCODE_FILE_ERROR;
	}

    // open file
    file = fopen(filename, "r");
    if (!file) {
        OutputErrorMessage(filename, 0, 0, NULL, "can't open file", strerror(errno));
        return EXITCODE_FILE_ERROR;
    }

    fprintf(stdout, "JavaScript Lint %s (%s)\n\n", JSL_VERSION, JS_GetImplementationVersion());

    ch = 0;
    lineno = 1;
    while(ch != EOF) {
        JSBool incomment;
        char *linepos;
        int i;
        incomment = JS_FALSE;
        linelen = 0;

        /* read line */
        while((ch = fgetc(file)) != EOF && ch != '\n' && ch != '\r') {
            if (incomment) {
                /*ignore*/
            }
            else if (ch == '#') {
                incomment = JS_TRUE;
            }
            else if (linelen == MAX_CONF_LINE) {
                fclose(file);
                return LintConfError(cx, filename, lineno, "exceeded maximum line length");
            }
            else
                line[linelen++] = ch;
        }

        /* remove trailing whitespace */
        while (linelen > 0 && isspace(line[linelen-1]))
            linelen--;
        /* null-terminate */
        line[linelen] = 0;
        linepos = line;

        if (!*linepos) {
            /* ignore blank line */
        }
        else if (*linepos == '-' || *linepos == '+') {
            JSBool enable;
            enable = (*linepos == '+');
            linepos++;

            if (strcasecmp(linepos, "recurse") == 0) {
                gRecurse = enable;
            }
            else if (strcasecmp(linepos, "context") == 0) {
                gShowContext = enable;
            }
            else if (strncasecmp(linepos, "process", strlen("process")) == 0) {
                char delimiter;
                char *path;

                if (!enable) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "-process is an invalid setting");
                }

                linepos += strlen("process");

                /* require (but skip) whitespace */
                if (!*linepos || !isspace(*linepos)) goto ProcessSettingErr_MissingPath;
                while (*linepos && isspace(*linepos))
                    linepos++;
                if (!*linepos) goto ProcessSettingErr_MissingPath;

                /* allow quote */
                if (*linepos == '\'') {
                    delimiter = *linepos;
                    linepos++;
                }
                else if (*linepos == '"') {
                    delimiter = *linepos;
                    linepos++;
                }
                else
                    delimiter = 0;

                /* read path */
                if (!*linepos) goto ProcessSettingErr_MissingQuote;
                path = linepos;
                while (*linepos && *linepos != delimiter)
                    linepos++;
                if (delimiter && !*linepos) goto ProcessSettingErr_MissingQuote;

                /* yank ending quote */
                if (linepos[0] && linepos[1]) goto ProcessSettingErr_Garbage;
                *linepos = 0;

                AddPathToList(processPaths, path);

                if (JS_FALSE) {
ProcessSettingErr_MissingPath:
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "invalid process setting: missing path");
ProcessSettingErr_MissingQuote:
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "invalid process setting: missing or mismatched quote");
ProcessSettingErr_Garbage:
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "invalid process setting: garbage after path");
                }
            }
            else if (strncasecmp(linepos, "output-format", strlen("output-format")) == 0) {
                linepos += strlen("output-format");

                /* skip whitespace */
                if (!*linepos || !isspace(*linepos)) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "expected whitespace after \"output-format\"");
                }
                while (*linepos && isspace(*linepos))
                    linepos++;

                if (!*linepos) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "expected format string after \"output-format\"");
                }

                if (!enable) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "-output-format is an invalid setting");
                }
                strncpy(gOutputFormat, linepos, sizeof(gOutputFormat)-1);
            }
            else if (strcasecmp(linepos, "always_use_option_explicit") == 0) {
               gAlwaysUseOptionExplicit = enable;
            }
            else if (strncasecmp(linepos, "define", strlen("define")) == 0) {
                jsval val;
                val = JSVAL_VOID;

                linepos += strlen("define");

                /* skip whitespace */
                if (!*linepos || !isspace(*linepos)) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "expected whitespace after \"define\"");
                }
                while (*linepos && isspace(*linepos))
                    linepos++;

                if (!*linepos) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "expected identifier after \"define\"");
                }

                if (!enable) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "Identifiers cannot be undefined");
                }

                /* validate identifier */
                if (!IsValidIdentifier(linepos)) {
                    char *tmp;
                    int result;

                    tmp = JS_smprintf("invalid identifier: \"%s\"", linepos);

                    fclose(file);
                    result = LintConfError(cx, filename, lineno, tmp);
                    JS_free(cx, tmp);
                    return result;
                }
                else if (JS_GetProperty(cx, obj, linepos, &val) && val != JSVAL_VOID) {
                    char *tmp;
                    tmp = JS_smprintf("identifier already defined: \"%s\"", linepos);
                    OutputErrorMessage(filename, lineno, 0, NULL, "configuration warning", tmp);
                    JS_free(cx, tmp);
                }
                else if (!JS_SetProperty(cx, obj, linepos, &val)) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "unable to define identifier");
                }
            }
#ifdef WIN32
            else if (strcasecmp(linepos, "pauseatend") == 0) {
                if (!enable) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "pauseatend cannot be disabled");
                }

                gPauseAtEnd = JS_TRUE;
            }
#endif
            else {
                // keep in sync with PrintDefaultConf
                for (i = 1; i < JSErr_Limit; i++) {
                    if (CAN_DISABLE_WARNING(i)) {
                        if (strcasecmp(linepos, errorNames[i]) == 0) {
                            showErrMsgs[i] = enable;
                            break;
                        }
                    }
                }
                if (i == JSErr_Limit) {
                    fclose(file);
                    return LintConfError(cx, filename, lineno, "unrecognized config setting");
                }
            }
        }
        else {
            fclose(file);
            return LintConfError(cx, filename, lineno, "unrecognized line format");
        }

        lineno++;
    }

    return 0;
}

static int
ProcessArgs(JSContext *cx, JSObject *obj, char **argv, int argc)
{
    JSBool hadConfig;
    int i;
    JSLPathList processPaths;
    int result;
    JS_INIT_CLIST(&processPaths.links);

    result = 0;

    if (!argc)
        return usage();

    hadConfig = JS_FALSE;
    for (i = 0; i < argc; i++) {
        char *parm;
        parm = argv[i];

        if (strcasecmp(parm, "+recurse") == 0) gRecurse = JS_TRUE;
        else if (strcasecmp(parm, "-recurse") == 0) gRecurse = JS_FALSE;
        else if (strcasecmp(parm, "+context") == 0) gShowContext = JS_TRUE;
        else if (strcasecmp(parm, "-context") == 0) gShowContext = JS_FALSE;
        else {
            /* skip - and / */
            if (*parm == '-' || *parm == '/')
                parm++;

            if (strcasecmp(parm, "help:conf") == 0) {
                PrintDefaultConf();
                result = 0;
                goto cleanup;
            }
            else if (strcasecmp(parm, "conf") == 0 ||
                strcasecmp(parm, "+conf") == 0) {
                /* only allow one config */
                if (hadConfig) {
                    fputs("Error: multiple configuration files.\n", stdout);
                    result = usage();
                    goto cleanup;
                }
                hadConfig = JS_TRUE;

                if (++i < argc) {
                    result = ProcessConf(cx, obj, argv[i], &processPaths);
                    if (result)
                        goto cleanup;
                }
                else {
                    fprintf(stdout, "Error: missing configuration path\n");
                    result = usage();
                    goto cleanup;
                }
            }
            else if (strcasecmp(parm, "process") == 0 ||
                strcasecmp(parm, "+process") == 0) {
                if (++i < argc)
                    AddPathToList(&processPaths, argv[i]);
                else {
                    fprintf(stdout, "Error: missing file path to process\n");
                    result = usage();
                    goto cleanup;
                }
            }
#ifdef WIN32
            else if (strcasecmp(parm, "pauseatend") == 0) {
                gPauseAtEnd = JS_TRUE;
            }
#endif
            else {
                fprintf(stdout, "Error: unrecognized parameter: %s\n", argv[i]);
                result = usage();
                goto cleanup;
            }
        }
    }

    /* delete items from the array as they're processed */
    while (!JS_CLIST_IS_EMPTY(&processPaths.links)) {
        JSLPathList *curFileItem = (JSLPathList*)JS_LIST_HEAD(&processPaths.links);
        ProcessScripts(cx, obj, curFileItem->path);
        JS_REMOVE_LINK(&curFileItem->links);
        JS_free(cx, curFileItem);
    }

    fprintf(stdout, "\n%i error(s), %i warning(s)\n", gNumErrors, gNumWarnings);
    return gExitCode;

cleanup:
    /* delete items */
    while (!JS_CLIST_IS_EMPTY(&processPaths.links)) {
        JSLPathList *curFileItem = (JSLPathList*)JS_LIST_HEAD(&processPaths.links);
        JS_REMOVE_LINK(&curFileItem->links);
        JS_free(cx, curFileItem);
    }

    return result;
}

#define LAZY_STANDARD_CLASSES

static JSBool
global_enumerate(JSContext *cx, JSObject *obj)
{
#ifdef LAZY_STANDARD_CLASSES
    return JS_EnumerateStandardClasses(cx, obj);
#else
    return JS_TRUE;
#endif
}

static JSBool
global_resolve(JSContext *cx, JSObject *obj, jsval id, uintN flags,
               JSObject **objp)
{
#ifdef LAZY_STANDARD_CLASSES
    if ((flags & JSRESOLVE_ASSIGNING) == 0) {
        JSBool resolved;

        if (!JS_ResolveStandardClass(cx, obj, id, &resolved))
            return JS_FALSE;
        if (resolved) {
            *objp = obj;
            return JS_TRUE;
        }
    }
#endif

    return JS_TRUE;

}

JSClass global_class = {
    "global", JSCLASS_NEW_RESOLVE,
    JS_PropertyStub,  JS_PropertyStub,
    JS_PropertyStub,  JS_PropertyStub,
    global_enumerate, (JSResolveOp) global_resolve,
    JS_ConvertStub,   JS_FinalizeStub
};

static void
my_ErrorReporter(JSContext *cx, const char *message, JSErrorReport *report)
{
    int i, j, k, n, colno;
    const char *prefix;

    if (!report) {
        OutputErrorMessage(NULL, 0, 0, NULL, NULL, message);
        return;
    }

    /* Conditionally ignore reported warnings. */
    if (!showErrMsgs[report->errorNumber]) {
        return;
    }

    if (CAN_DISABLE_WARNING(report->errorNumber) && SHOULD_IGNORE_LINT_WARNINGS(cx)) {
        return;
    }

    prefix = NULL;
    if (JSREPORT_IS_WARNING(report->flags)) {
        if (IS_JSL_WARNING_MSG(report->errorNumber)) {
            prefix = LINT_WARNING_PREFIX;
        }
        else if (JSREPORT_IS_STRICT(report->flags)) {
            prefix = STRICT_WARNING_PREFIX;
        }
        else
            prefix = WARNING_PREFIX;
    }
    else {
        prefix = NULL;
    }

    /* oolno is 1-based */
    colno = 0;
    if (report->linebuf)
        colno = PTRDIFF(report->tokenptr, report->linebuf, char)+1;

    OutputErrorMessage(report->filename, report->lineno, colno,
        errorNames[report->errorNumber], prefix, message);

    if (report->linebuf && gShowContext) {
        /* report->linebuf usually ends with a newline. */
        n = strlen(report->linebuf);
        fprintf(stdout, "%s%s%s%s",
                ""/*prefix*/,
                report->linebuf,
                (n > 0 && report->linebuf[n-1] == '\n') ? "" : "\n",
                ""/*prefix*/);
        n = PTRDIFF(report->tokenptr, report->linebuf, char);
        for (i = j = 0; i < n; i++) {
            if (report->linebuf[i] == '\t') {
                for (k = (j + 8) & ~7; j < k; j++) {
                    fputc('.', stdout);
                }
                continue;
            }
            fputc('.', stdout);
            j++;
        }
        fputs("^\n\n", stdout);
    }

    if (!JSREPORT_IS_WARNING(report->flags)) {
        SetExitCode(EXITCODE_JS_ERROR);
        gNumErrors++;
    }
    else {
        SetExitCode(EXITCODE_JS_WARNING);
        gNumWarnings++;
    }
}

static JSBool
LoadErrNames(JSContext *cx)
{
    int i;
    for (i = 0; i < JSErr_Limit; i++) {
        char *tmp;

        /* remove prefix */
        JS_ASSERT(strncasecmp(errorNames[i], "JSMSG_", 6) == 0);
        tmp = JS_strdup(cx, errorNames[i] + 6);
        if (!tmp)
            return JS_FALSE;
        errorNames[i] = tmp;

        /* to lowercase */
        while (*tmp) {
            *tmp = tolower(*tmp);
            tmp++;
        }
    }

    return JS_TRUE;
}

static void
FreeErrNames(JSContext *cx)
{
    int i;
    for (i = 0; i < JSErr_Limit; i++) {
        JS_free(cx, errorNames[i]);
        errorNames[i] = NULL;
    }
}

int
main(int argc, char **argv, char **envp)
{
    JSVersion version;
    JSRuntime *rt;
    JSContext *cx;
    JSObject *glob;
    int result;

    version = JSVERSION_DEFAULT;

    argc--;
    argv++;

    JS_INIT_CLIST(&gScriptList.links);
    JS_ASSERT(sizeof(placeholders) / sizeof(placeholders[0]) == JSLPlaceholder_Limit);

    rt = JS_NewRuntime(64L * 1024L * 1024L);
    if (!rt)
        return 1;

    cx = JS_NewContext(rt, 8192);
    if (!cx)
        return 1;
    JS_SetErrorReporter(cx, my_ErrorReporter);

    glob = JS_NewObject(cx, &global_class, NULL, NULL);
    if (!glob)
        return 1;
#ifdef LAZY_STANDARD_CLASSES
    JS_SetGlobalObject(cx, glob);
#else
    if (!JS_InitStandardClasses(cx, glob))
        return 1;
#endif

    /* switch over error names to lower-case values */
    if (!LoadErrNames(cx))
        return 1;

    /* Set version only after there is a global object. */
    if (version != JSVERSION_DEFAULT)
        JS_SetVersion(cx, version);

    JS_ToggleOptions(cx, JSOPTION_STRICT);

    if (getenv("SERVER_SOFTWARE")) {
        int len;
        char *contentsPos, *contents;

        /* tweak global settings */
        gShowContext = JS_FALSE;

        #define MSG_DEF(name, number, count, exception, format) showErrMsgs[number] = JS_TRUE;
        #include "js.msg"
        #undef MSG_DEF

        showErrMsgs[JSMSG_MISSING_OPTION_EXPLICIT] = JS_FALSE;

        strcpy(gOutputFormat, "__LINE__,__COL__,__ERROR_NAME__,__ERROR_PREFIX__,__ERROR_MSGENC__");

        result = 0;
        fputs("Content-Type: text\r\n\r\n", stdout);

        fputs("Start\r\n", stdout);
        if (!getenv("CONTENT_LENGTH") ||
            !(len = atoi(getenv("CONTENT_LENGTH")))) {
            fputs("Error", stdout);
            result = 1;
        }
        else if (JS_PushLintIdentifers(cx, NULL, NULL, JS_FALSE, NULL, NULL)) {
            /* read */
            contents = (char*)JS_malloc(cx, len+1);
            contentsPos = contents;
            while ((*contentsPos = fgetc(stdin)) != EOF)
                contentsPos++;
            *contentsPos = 0;

            /* lint */
            if (!ProcessScriptContents(cx, glob, JSL_FILETYPE_UNKNOWN, NULL, contents, NULL, NULL))
                result = 1;
            JS_PopLintIdentifers(cx);

            JS_free(cx, contents);
            fputs("Done", stdout);
        }
        else {
            fputs("Error", stdout);
        }
    }
    else {
        result = ProcessArgs(cx, glob, argv, argc);
    }

    FreeErrNames(cx);
    JS_DestroyContext(cx);
    JS_DestroyRuntime(rt);
    JS_ShutDown();

    /* clean up list of files */
    while (!JS_CLIST_IS_EMPTY(&gScriptList.links)) {
        JSLScriptList *scriptItem;
        scriptItem = (JSLScriptList*)JS_LIST_HEAD(&gScriptList.links);
        JS_REMOVE_LINK(&scriptItem->links);

        /* clean up dependencies */
        while (!JS_CLIST_IS_EMPTY(&scriptItem->directDependencies.links)) {
            JSLScriptDependencyList *dependency;
            dependency = (JSLScriptDependencyList*)JS_LIST_HEAD(&scriptItem->directDependencies.links);
            JS_REMOVE_LINK(&dependency->links);
        }

        JS_free(cx, scriptItem);
    }

#ifdef WIN32
    if (gPauseAtEnd) {
        fputs("Press any key to continue...", stdout);
        getch();
        fputc('\n', stdout);
    }
#endif

    return result;
}
