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
#include "JavaScriptLintAPI.h"

#include "JavaScriptLintExec.h"

#include <assert.h>
#include <iostream>
#include <sstream>

// see header
#pragma warning(push, 4)
#pragma warning(disable: 4786)

using namespace std;

namespace JSLStrings
{
   void ReplaceString(string& str, const char *lookfor, const char *replacewith)
   {
      // get the length of the old and new items
      int oldTextLen = strlen(lookfor);
      int newTextLen = strlen(replacewith);

      // find each occurrence of the old text
      string::size_type pos = 0;
      while ((pos = str.find(lookfor, pos)) != string::npos)
      {
         // replace the old text with the new
         str.replace(pos, oldTextLen, replacewith);
         // jump past the newly inserted text
         pos += newTextLen;
      }
   }

   string EscapeAndQuoteParameter(string parameter)
   {
      string escapedParameter = parameter;
      ReplaceString(escapedParameter, "\\", "\\\\");
      ReplaceString(escapedParameter, "\"", "\\\"");
      escapedParameter.insert(0, '"');
      escapedParameter += '"';
      return escapedParameter;
   }

   void SplitString(string source, string delimiter, vector<string>& results)
   {
      assert(delimiter.length() > 0);

      string::size_type lastpos = 0, curpos = 0;
      while ((curpos = source.find(delimiter, lastpos)) != string::npos)
      {
         results.push_back(source.substr(lastpos, curpos-lastpos));
         lastpos = curpos + delimiter.length();
      }

      if (lastpos)
         results.push_back(source.substr(lastpos));
   }

   bool GetIntFromString(int& i, const string& s)
   {
      istringstream stream(s);
      return !(stream >> std::dec >> i).fail();
   }

   string StripCSlashes(const string& encoded)
   {
      string decoded = encoded;
      ReplaceString(decoded, "\\n", "\n");
      ReplaceString(decoded, "\\r", "\r");
      ReplaceString(decoded, "\\t", "\t");
      ReplaceString(decoded, "\\\'", "\'");
      ReplaceString(decoded, "\\\"", "\"");
      ReplaceString(decoded, "\\\\", "\\");
      return decoded;
   }
}



JavaScriptLint::JavaScriptLint(string binaryPath, string configPath)
{
   m_binaryPath = binaryPath;
   m_configPath = configPath;
}

bool JavaScriptLint::LintString(string code, JSL_OUT vector<JSLMessage>& messages, JSL_OUT string& error)
{
   return RunLint(vector<string>(), true, code, messages, error);
}

bool JavaScriptLint::LintFile(string file, JSL_OUT vector<JSLMessage>& messages, JSL_OUT string& error)
{
   vector<string> files;
   files.push_back(file);
   return LintFiles(files, messages, error);
}

bool JavaScriptLint::LintFiles(vector<string> files, JSL_OUT vector<JSLMessage>& messages, JSL_OUT string& error)
{
   return RunLint(files, false, "", messages, error);
}

bool JavaScriptLint::RunLint(const vector<string>& files, bool useStdin, string code,
                             JSL_OUT vector<JSLMessage>& messages, string& error)
{
   assert(useStdin || !code.length());

   // Construct the command line
   string commandline;
   commandline += JSLStrings::EscapeAndQuoteParameter(m_binaryPath);
   if (m_configPath.length())
   {
      commandline += " -conf ";
      commandline += JSLStrings::EscapeAndQuoteParameter(m_configPath);
   }
   for (vector<string>::const_iterator file_iter = files.begin(); file_iter != files.end(); file_iter++)
   {
      commandline += " -process ";
      commandline += JSLStrings::EscapeAndQuoteParameter(*file_iter);
   }
   if (useStdin)
      commandline += " -stdin";
   commandline += " -context -nologo -nofilelisting -nosummary";
   commandline += " -output-format \"encode:__FILE__\t__LINE__\t__COL__\t__ERROR_NAME__\t__ERROR_PREFIX__\t__ERROR_MSG__\"";

   // Run the Lint
   string results;
   if (!JavaScriptLintAPI::ExecuteProcess(commandline, code, results, error))
   {
      error = "Unable to run JavaScript Lint. " + error;
      return false;
   }

   JSLStrings::ReplaceString(results, "\r\n", "\n");

   // Parse the messages
   vector<string> lines;
   JSLStrings::SplitString(results, "\n", lines);
   for (vector<string>::const_iterator line_iter = lines.begin(); line_iter != lines.end(); line_iter++)
   {
      // Skip blank lines
      if (!line_iter->length())
         continue;

      // The fields are tab delimited
      vector<string> fields;
      JSLStrings::SplitString(*line_iter, "\t", fields);
      if (fields.size() != 6)
      {
         error = "JavaScript Lint returned unreadable information.";
         return false;
      }

      // Decode fields
      for (vector<string>::iterator field_iter = fields.begin(); field_iter != fields.end(); field_iter++)
         *field_iter = JSLStrings::StripCSlashes(*field_iter);

      JSLMessage msg;
      msg.filename = fields.at(0);
      if (!JSLStrings::GetIntFromString(msg.line, fields.at(1)))
         msg.line = 0;
      if (!JSLStrings::GetIntFromString(msg.col, fields.at(2)))
         msg.col = 0;
      msg.errName = fields.at(3);
      msg.errType = fields.at(4);
      msg.errMessage = fields.at(5);

      // convert line and col number to 0-based
      msg.line--;
      msg.col--;
      messages.push_back(msg);
   }

   return true;
}
