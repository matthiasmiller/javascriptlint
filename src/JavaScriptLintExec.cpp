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
 * The Original Code is JavaScript Lint code.
 *
 * The Initial Developer of the Original Code is Matthias Miller.
 * Portions created by the Initial Developer are Copyright (C) 2006
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
 * JavaScript Lint API
 * Developed by Matthias Miller (http://www.JavaScriptLint.com/)
 *
 * Suggestions or revisions can be sent to Info@JavaScriptLint.com
 */
#include "JavaScriptLintExec.h"

#include <windows.h>

using namespace std;

namespace
{
   string GetLastErrorString()
   {
      if (GetLastError() == ERROR_SUCCESS)
         return "";

      LPVOID lpMsgBuf;
      FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM, NULL,
                    GetLastError(), MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
                    (LPTSTR) &lpMsgBuf, 0, NULL);
      string error = (char *)lpMsgBuf;
      LocalFree(lpMsgBuf);
      return error;
   }
}

bool JavaScriptLintAPI::ExecuteProcess(string commandline, string input, string& output, string& error)
{
   // SEE http://msdn.microsoft.com/library/en-us/dllproc/base/creating_a_child_process_with_redirected_input_and_output.asp?frame=true
   output.empty();

   // Set the bInheritHandle flag so pipe handles are inherited. 
   SECURITY_ATTRIBUTES saAttr;
   saAttr.nLength = sizeof(SECURITY_ATTRIBUTES); 
   saAttr.bInheritHandle = TRUE; 
   saAttr.lpSecurityDescriptor = NULL; 

   // Create a pipe for the child process's STDOUT that is not inherited
   HANDLE hChildStdoutRd, hChildStdoutWr;
   if (!CreatePipe(&hChildStdoutRd, &hChildStdoutWr, &saAttr, 0)) 
   {
      error = GetLastErrorString();
      return false;
   }
   SetHandleInformation(hChildStdoutRd, HANDLE_FLAG_INHERIT, 0);

   // Create a pipe for the child process's STDIN that is not inherited
   HANDLE hChildStdinRd, hChildStdinWr;
   if (!CreatePipe(&hChildStdinRd, &hChildStdinWr, &saAttr, 0))
   {
      error = GetLastErrorString();
      return false;
   }
   SetHandleInformation(hChildStdinWr, HANDLE_FLAG_INHERIT, 0);

   // Create the child process
   PROCESS_INFORMATION piProcInfo;
   ZeroMemory(&piProcInfo, sizeof(PROCESS_INFORMATION));

   STARTUPINFO siStartInfo;
   ZeroMemory(&siStartInfo, sizeof(STARTUPINFO));
   siStartInfo.cb = sizeof(STARTUPINFO); 
   siStartInfo.hStdError = hChildStdoutWr;
   siStartInfo.hStdOutput = hChildStdoutWr;
   siStartInfo.hStdInput = hChildStdinRd;
   siStartInfo.dwFlags |= STARTF_USESTDHANDLES;
   siStartInfo.dwFlags |= STARTF_USESHOWWINDOW;

   if (!CreateProcess(NULL,
      (char*)commandline.c_str(), // command line 
      NULL,          // process security attributes 
      NULL,          // primary thread security attributes 
      TRUE,          // handles are inherited 
      0,             // creation flags 
      NULL,          // use parent's environment 
      NULL,          // use parent's current directory 
      &siStartInfo,  // STARTUPINFO pointer 
      &piProcInfo))  // receives PROCESS_INFORMATION 
   {
      error = GetLastErrorString();
      return false;
   }
   CloseHandle(piProcInfo.hProcess);
   CloseHandle(piProcInfo.hThread);

   // write the result and close the file so the client stops reading
   DWORD dwBytesWritten = 0;
   if (!WriteFile(hChildStdinWr, input.c_str(), input.length(), &dwBytesWritten, NULL))
   {
      error = GetLastErrorString();
      return false;
   }
   if (!CloseHandle(hChildStdinWr))
   {
      error = GetLastErrorString();
      return false;
   }

   // Close the write end of the pipe before reading from the read end of the pipe. 
   if (!CloseHandle(hChildStdoutWr)) 
   {
      error = GetLastErrorString();
      return false;
   }
 
   // Read output from the child process, and write to parent's STDOUT. 
   DWORD dwBytesRead;
   CHAR chBuf[415];
   for (;;)
   {
      if (!ReadFile(hChildStdoutRd, chBuf, sizeof(chBuf), &dwBytesRead, NULL))
      {
         if (GetLastError() == ERROR_BROKEN_PIPE)
            break;

         error = "The output pipe could not be read. ";
         error += GetLastErrorString();
         return false;
      }
      if (!dwBytesRead)
         break;
      output.append(chBuf, dwBytesRead);
   }
   return true;
}
