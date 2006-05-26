/* -*- Mode: C; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 4 -*-
 *
 * ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http:
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
#include "..\src\jsstddef.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h> /*to find files*/
#include "..\src\jstypes.h"
#include "..\src\jsarena.h"
#include "..\src\jsutil.h"
#include "..\src\jsprf.h"
#include "..\src\jsapi.h"
#include "..\src\jsatom.h"
#include "..\src\jscntxt.h"
#include "..\src\jsdbgapi.h"
#include "..\src\jsemit.h"
#include "..\src\jsfun.h"
#include "..\src\jsgc.h"
#include "..\src\jslock.h"
#include "..\src\jsobj.h"
#include "..\src\jsparse.h"
#include "..\src\jsscope.h"
#include "..\src\jsscript.h"

#if defined(XP_WIN) || defined(XP_OS2)
#include <io.h>     /* for isatty() */
#endif

#define EXITCODE_WARNING 1
#define EXITCODE_ERROR 3
#define EXITCODE_FILE_NOT_FOUND 4

int gExitCode = 0;
JSBool gQuitting = JS_FALSE;
FILE *gErrFile = NULL;
FILE *gOutFile = NULL;

typedef enum JSLErrNum {
#define MSG_DEF(name, number, count, exception, format) \
    name = number,
#include "jsl.msg"
#undef MSG_DEF
    JSLErr_Limit
#undef MSGDEF
} JSLErrNum;

JSBool showErrMsgs[JSErr_Limit] = {
#define MSG_DEF(name, number, count, exception, format) \
    (number != JSMSG_BLOCK_WITHOUT_BRACES) ,
#include "..\src\js.msg"
#undef MSG_DEF
};

const char *errorNames[JSErr_Limit] = {
#define MSG_DEF(name, number, count, exception, format) #name,
#include "..\src\js.msg"
#undef MSG_DEF
};

JSBool gRecurse = JS_FALSE;
JSBool gShowContext = JS_TRUE;
int gNumWarnings = 0, gNumErrors = 0;

static void
SetExitCode(int level)
{
    if (level > gExitCode)
        gExitCode = level;
}

static const JSErrorFormatString *
my_GetErrorMessage(void *userRef, const char *locale, const uintN errorNumber);

static char *
GetFileName(char *path)
{
    char *file, *tmp;
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

static JSBool
ProcessSingleScript(JSContext *cx, JSObject *obj, char *relpath)
{
    JSScript *script;
    char filename[_MAX_PATH+1];
    long fileSize;
    int lineno;
    char *contents, *contentsPos;
    JSBool runFullScript;

    FILE *file;

    /* resolve relative paths */
	int ret = GetFullPathName(relpath, _MAX_PATH, filename, NULL);
	if(!ret || ret > _MAX_PATH) {
        JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                             JSLMSG_CANT_OPEN, relpath, "unable to resolve path");
        SetExitCode(EXITCODE_FILE_NOT_FOUND);
        return JS_FALSE;
	}

    fflush(gErrFile);
    fputs(GetFileName(filename), gOutFile);
    fputc('\n', gOutFile);

    file = fopen(filename, "r");
    if (!file) {
        JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                             JSLMSG_CANT_OPEN, filename, strerror(errno));
        SetExitCode(EXITCODE_FILE_NOT_FOUND);
        return JS_FALSE;
    }

    /* seek to the send to determine file size*/
    if (fseek(file, 0, SEEK_END) != 0 ||
        (fileSize = ftell(file)) < 0 ||
        fseek(file, 0, SEEK_SET) != 0) {

        fclose(file);
        JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                             JSLMSG_CANT_READ, filename, strerror(errno));
        SetExitCode(EXITCODE_FILE_NOT_FOUND);
        return JS_FALSE;
    }

    /* alloc memory */
    contents = (char *)JS_malloc(cx, fileSize+1);
    if (contents == NULL) {
        fclose(file);
        JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                             JSLMSG_CANT_READ, filename, "out of memory");
        SetExitCode(EXITCODE_FILE_NOT_FOUND);
        return JS_FALSE;
    }

    /* read file */
    fileSize = fread(contents, 1, fileSize, file);
    if (ferror(file)) {
        fclose(file);
        JS_free(cx, contents);
        JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                         JSLMSG_CANT_READ, filename, strerror(errno));
        SetExitCode(EXITCODE_FILE_NOT_FOUND);
        return JS_FALSE;
    }
    contents[fileSize] = 0;
    contentsPos = contents;

    lineno = 1;    
    runFullScript = JS_TRUE;

    /* yech... */
    while (*contentsPos) {
        COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
        if (!*contentsPos)
            break;

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

        if (strnicmp(contentsPos, "html", 4) == 0 && !isalnum(*(contentsPos+4))) {
            /* html tag, so it must be an HTML file */
            contentsPos += 4;
            runFullScript = JS_FALSE;
        }
        else if (strnicmp(contentsPos, "script", 6) != 0 || isalnum(*(contentsPos+6))) {
            /* not the script tag that we're looking for */
            contentsPos++;
        }
        else {
            /* script tag */
            char *startOfScript, *endOfScript;
            int lineStartOfScript;
            contentsPos += 6;

            /* find start of script */
            lineStartOfScript = 0;
            startOfScript = NULL;
            endOfScript = NULL;
            while (*contentsPos) {
                COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                if (!*contentsPos)
                    break;

                if (*contentsPos == '\"' || *contentsPos == '\'') {
                    jschar startChar;
                    startChar = *contentsPos;
                    contentsPos++;

                    while (*contentsPos) {
                        COUNT_AND_SKIP_NEWLINES(contentsPos, lineno);
                        if (!*contentsPos)
                            break;
                        if (*contentsPos == startChar) {
                            contentsPos++;
                            break;
                        }
                        contentsPos++;
                    }
                    if (!*contentsPos)
                        break;
                }
                else if (*contentsPos == '/' && *(contentsPos+1) == '>') {
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
                char *possibleEndOfScript;
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

                if (strnicmp(contentsPos, "script", 6) == 0 && !isalnum(*(contentsPos+6))) {
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

            if (!startOfScript || !endOfScript) {
                JS_free(cx, contents);
                JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                                     JSLMSG_CANT_READ, filename, "unable to find end of script tag");
                SetExitCode(EXITCODE_ERROR);
                return JS_FALSE;
            }

            runFullScript = JS_FALSE;
            if (startOfScript != endOfScript) {
                script = JS_CompileScript(cx, obj, startOfScript, endOfScript - startOfScript, filename, lineStartOfScript);
                if (script)
                    JS_DestroyScript(cx, script);
                else {
                    JS_free(cx, contents);
                    SetExitCode(EXITCODE_ERROR);
                    return JS_FALSE;
                }
            }
        }
    }

    if (runFullScript) {
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

        script = JS_CompileScript(cx, obj, contents, fileSize, filename, 1);
        JS_free(cx, contents);

        if (script) {
            JS_DestroyScript(cx, script);
            return JS_TRUE;
        }
        SetExitCode(EXITCODE_ERROR);
        return JS_FALSE;
    }
    else {
        JS_free(cx, contents);
        return JS_TRUE;
    }
}

static JSBool
ProcessScripts(JSContext *cx, JSObject *obj, char *relpath)
{
    WIN32_FIND_DATA finddata;
    HANDLE search;
    char path[_MAX_PATH+1];
    char *folder, *file, *recursepath, *searchIfFolder;

    /* resolve relative paths */
	int ret = GetFullPathName(relpath, _MAX_PATH, path, NULL);
	if(!ret || ret > _MAX_PATH) {
        JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                             JSLMSG_CANT_OPEN, relpath, "unable to resolve path");
        SetExitCode(EXITCODE_FILE_NOT_FOUND);
        return JS_FALSE;
	}

    /* get the folder name */
    file = GetFileName(path);
    folder = JS_smprintf("%s\\", path);
    folder[file - path] = '\\';
    folder[file - path] = 0;

    if (strchr(file, '?') != NULL || strchr(file, '*') != NULL) {
        /* this has wildcards, so do a search on this path */
        search = FindFirstFile(relpath, &finddata);
        if (search == INVALID_HANDLE_VALUE)
            goto try_recurse;
    }
    else {
        /* see if it's a folder */
        searchIfFolder = JS_smprintf("%s\\*.*", path);
        search = FindFirstFile(searchIfFolder, &finddata);
        JS_free(cx, searchIfFolder);

        if (search == INVALID_HANDLE_VALUE) {
            /* if not, was this intended as a folder? */
            if (*path && (path[strlen(path)-1] == '/' && path[strlen(path)-1] == '\\')) {
                JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                                     JSLMSG_CANT_OPEN, relpath, "path does not exist");
                SetExitCode(EXITCODE_FILE_NOT_FOUND);
                FindClose(search);
                JS_free(cx, folder);
                SetExitCode(EXITCODE_FILE_NOT_FOUND);
                return JS_FALSE;
            }
            else {
                /* treat as a file */
                FindClose(search);
                JS_free(cx, folder);
                return ProcessSingleScript(cx, obj, path);
            }
        }
    }

    do {
        if ((finddata.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0) {
            /* process script */
            char *script;
            script = JS_smprintf("%s%s", folder, finddata.cFileName);
            ProcessSingleScript(cx, obj, script);
            JS_free(cx, script);
        }
    } while(FindNextFile(search, &finddata));
    FindClose(search);

try_recurse:
    /* subfolders */
    if (gRecurse) {
        recursepath = JS_smprintf("%s*.*", folder);
        search = FindFirstFile(recursepath, &finddata);
        JS_free(cx, recursepath);
        if (search == INVALID_HANDLE_VALUE) {
            JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                                 JSLMSG_CANT_OPEN, folder, "unable to list subfolders");
            SetExitCode(EXITCODE_FILE_NOT_FOUND);
            return JS_FALSE;
        }

        do {
            if ((finddata.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0) {
                /* ignore */
            }
            else if (finddata.cFileName[0] == '.' && (finddata.cFileName[1] == 0 ||
                finddata.cFileName[1] == '.' && finddata.cFileName[2] == 0)) {
                /*single/double dot*/
            }
            else {
                /* recurse */
                char *path;
                path = JS_smprintf("%s%s\\%s", folder, finddata.cFileName, file);
                ProcessScripts(cx, obj, path);
                JS_free(cx, path);
            }
        } while(FindNextFile(search, &finddata));
    }

    JS_free(cx, folder);
    return JS_TRUE;
}

extern JSClass global_class;

static void
PrintConfErrName(const uintN number, const char *name, const char *format)
{
    int chars;

    JS_ASSERT(strnicmp(name, "JSMSG_", 6) == 0);
    name += 6;

    fputc(showErrMsgs[number] ? '+' : '-', gOutFile);
    chars = 0;
    while (*name) {
        fputc(tolower(*name++), gOutFile);
        chars++;
    }
    while (chars < 25) {
        fputc(' ', gOutFile);
        chars++;
    }
    fputs("# ", gOutFile);
    fputs(format, gOutFile);
    fputs("\n", gOutFile);
}

static void
PrintDefaultConf(void)
{
    fputs(
        "#\n"
        "# JavaScript Lint Configuration File\n"
        "#\n"
        "# This file can be used to lint a collection of scripts, or to enable\n"
        "# or disable warnings for scripts that are linted via the command line.\n"
        "#\n"
        "\n"
        "### Warnings\n"
        "# Enable or disable warnings based on requirements.\n"
        "# Use \"+WarningName\" to display or \"-WarningName\" to suppress.\n"
        "#\n"
        , gOutFile);

    // keep in sync with RunConf
    #define MSG_DEF(name, number, count, exception, format) \
    { if ((number) > JSMSG_START_LINT_MESSAGES) PrintConfErrName(number, #name, format); }
    #include "..\src\js.msg"
    #undef MSG_DEF

    fputs(
        "\n### Context\n"
        "# Show the in-line position of the error.\n"
        "# Use \"+context\" to display or \"-context\" to suppress.\n"
        "#\n"
        "+context\n"
        , gOutFile);

    fputs(
        "\n### Files\n"
        "# Specify which files to lint\n"
        "# Use \"+recurse\" to enable recursion and \"-recurse\" to disable.\n"
        "# To add a set of files, use \"+process FileName\", \"+process Folder\\Path\\*.js\",\n"
        "# or \"+process Folder\\Path\\*.htm\".\n"
        "#\n"
        "+process jsl-test.js\n"
        , gOutFile);
}

static int
usage(void)
{
    fprintf(gErrFile, "\nJavaScript Lint (%s)\n", JS_GetImplementationVersion());
    fprintf(gErrFile, "usage: jsl [help:conf] [conf filename] [+recurse|-recurse] [process filename] [+context|-context]\n");
    SetExitCode(2);
    return 2;
}

static int
LintConfError(JSContext *cx, const char *filename, int lineno, const char *err)
{
    char *errline = JS_smprintf("%i", lineno);
    JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                         JSLMSG_LINT_CONF_ERROR, errline, err);
    JS_free(cx, errline);
    SetExitCode(2);
    return 2;
}

static int
RunConf(JSContext *cx, JSObject *obj, const char *filename)
{
#define MAX_LINE 500
    char line[MAX_LINE+1];
    int linelen, lineno;
    int ch;

    FILE *file;

    // open file
    file = fopen(filename, "r");
    if (!file) {
        JS_ReportErrorNumber(cx, my_GetErrorMessage, NULL,
                             JSLMSG_CANT_OPEN, filename, strerror(errno));
        return EXITCODE_FILE_NOT_FOUND;
    }

    fprintf(gOutFile, "JavaScript Lint (%s)\n\n", JS_GetImplementationVersion());

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
            else if (linelen == MAX_LINE) {
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

            if (stricmp(linepos, "recurse") == 0) {
                gRecurse = enable;
            }
            else if (stricmp(linepos, "context") == 0) {
                gShowContext = enable;
            }
            else if (strnicmp(linepos, "process", strlen("process")) == 0) {
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

                (JSBool)ProcessScripts(cx, obj, path);

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
            else {
                // keep in sync with PrintDefaultConf
                for (i = JSMSG_START_LINT_MESSAGES+1; i < JSErr_Limit; i++) {
                    const char *name;
                    name = errorNames[i];
                    JS_ASSERT(strnicmp(name, "JSMSG_", 6) == 0);
                    name += 6;

                    if (stricmp(linepos, name) == 0) {
                        showErrMsgs[i] = enable;
                        break;
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
    int i;

    if (!argc)
        return usage();

    for (i = 0; i < argc; i++) {
        char *parm;
        parm = argv[i];

        if (stricmp(parm, "+recurse") == 0) gRecurse = JS_TRUE;
        else if (stricmp(parm, "-recurse") == 0) gRecurse = JS_FALSE;
        else if (stricmp(parm, "+context") == 0) gShowContext = JS_TRUE;
        else if (stricmp(parm, "+context") == 0) gShowContext = JS_FALSE;
        else {
            /* skip - and / */
            if (*parm == '-' || *parm == '/')
                parm++;

            if (stricmp(parm, "help:conf") == 0) {
                PrintDefaultConf();
                return 0;
            }
            else if (stricmp(parm, "conf") == 0 ||
                stricmp(parm, "+conf") == 0) {
                if (++i < argc) {
                    int result;
                    result = RunConf(cx, obj, argv[i]);
                    if (result)
                        return result;
                }
                else {
                    fflush(gOutFile);
                    fprintf(gErrFile, "Missing configuration path\n");
                    return usage();
                }
            }
            else if (stricmp(parm, "process") == 0 ||
                stricmp(parm, "+process") == 0) {
                if (++i < argc)
                    ProcessScripts(cx, obj, argv[i]);
                else {
                    fflush(gOutFile);
                    fprintf(gErrFile, "Missing file path to process\n");
                    return usage();
                }
            }
            else {
                fflush(gOutFile);
                fprintf(gErrFile, "Unrecognized parameter: %s\n", argv[i]);
                return usage();
            }
        }
    }

    fflush(gErrFile);
    fprintf(gOutFile, "\n%i error(s), %i warning(s)\n", gNumErrors, gNumWarnings);
    return gExitCode;
}

static void
my_ErrorReporter(JSContext *cx, const char *message, JSErrorReport *report);

JSErrorFormatString jsl_ErrorFormatString[JSErr_Limit] = {
#if JS_HAS_DFLT_MSG_STRINGS
#define MSG_DEF(name, number, count, exception, format) \
    { format, count } ,
#else
#define MSG_DEF(name, number, count, exception, format) \
    { NULL, count } ,
#endif
#include "jsl.msg"
#undef MSG_DEF
};

static const JSErrorFormatString *
my_GetErrorMessage(void *userRef, const char *locale, const uintN errorNumber)
{
    if ((errorNumber > 0) && (errorNumber < JSLErr_Limit))
        return &jsl_ErrorFormatString[errorNumber];
    return NULL;
}

static void
my_ErrorReporter(JSContext *cx, const char *message, JSErrorReport *report)
{
    int i, j, k, n;
    char *prefix, *tmp;
    const char *ctmp;

    /* flush any other output */
    fflush(gOutFile);

    if (!report) {
        fprintf(gErrFile, "%s\n", message);
        return;
    }

    /* Conditionally ignore reported warnings. */
    if (!showErrMsgs[report->errorNumber]) {
        return;
    }

    prefix = NULL;
    if (report->filename)
        prefix = JS_smprintf("%s", report->filename);
    if (report->lineno) {
        tmp = prefix;
        prefix = JS_smprintf("%s(%u): ", tmp ? tmp : "", report->lineno);
        JS_free(cx, tmp);
    }
    if (JSREPORT_IS_WARNING(report->flags)) {
        tmp = prefix;
        prefix = JS_smprintf("%s%swarning: ",
                             tmp ? tmp : "",
                             report->errorNumber > JSMSG_START_LINT_MESSAGES ? "lint " :
                             (JSREPORT_IS_STRICT(report->flags) ? "strict " : ""));
        JS_free(cx, tmp);
    }

    /* embedded newlines -- argh! */
    while ((ctmp = strchr(message, '\n')) != 0) {
        ctmp++;
        if (prefix) {
            char *pos;
            pos = prefix;
            while (*pos) {
               fputc(' ', gOutFile);
            }
        }
        fwrite(message, 1, ctmp - message, gErrFile);
        message = ctmp;
    }

    /* If there were no filename or lineno, the prefix might be empty */
    if (prefix)
        fputs(prefix, gErrFile);
    fputs(message, gErrFile);

    if (!report->linebuf) {
        fputc('\n', gErrFile);
        goto out;
    }

    if (gShowContext) {
        /* report->linebuf usually ends with a newline. */
        n = strlen(report->linebuf);
        fprintf(gErrFile, ":\n%s%s%s%s",
                ""/*prefix*/,
                report->linebuf,
                (n > 0 && report->linebuf[n-1] == '\n') ? "" : "\n",
                ""/*prefix*/);
        n = PTRDIFF(report->tokenptr, report->linebuf, char);
        for (i = j = 0; i < n; i++) {
            if (report->linebuf[i] == '\t') {
                for (k = (j + 8) & ~7; j < k; j++) {
                    fputc('.', gErrFile);
                }
                continue;
            }
            fputc('.', gErrFile);
            j++;
        }
        fputs("^\n", gErrFile);
    }
    fputs("\n", gErrFile);
 out:
    if (!JSREPORT_IS_WARNING(report->flags)) {
        SetExitCode(EXITCODE_ERROR);
        gNumErrors++;
    }
    else {
        SetExitCode(EXITCODE_WARNING);
        gNumWarnings++;
    }
    JS_free(cx, prefix);
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

int
main(int argc, char **argv, char **envp)
{
    JSVersion version;
    JSRuntime *rt;
    JSContext *cx;
    JSObject *glob;
    int result;

    gErrFile = stderr;
    gOutFile = stdout;

    version = JSVERSION_DEFAULT;

    argc--;
    argv++;

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

    /* Set version only after there is a global object. */
    if (version != JSVERSION_DEFAULT)
        JS_SetVersion(cx, version);

    JS_ToggleOptions(cx, JSOPTION_STRICT);
    result = ProcessArgs(cx, glob, argv, argc);

    JS_DestroyContext(cx);
    JS_DestroyRuntime(rt);
    JS_ShutDown();

    return result;
}
