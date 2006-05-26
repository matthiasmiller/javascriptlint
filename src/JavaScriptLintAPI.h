#ifndef _JAVASCRIPTLINTAPI_H__
#define _JAVASCRIPTLINTAPI_H__

#define JSL_IN
#define JSL_OUT

#include <xstring>

bool ExecuteProcess(std::string commandline, std::string input,
                    JSL_OUT std::string& output, JSL_OUT std::string& error);

// The Visual C++ compiler gives a warning when including <vector> because of debug symbols.
#pragma warning(push)
#pragma warning(disable: 4786)
#include <vector>
#pragma warning(pop)

// The return line and column is 0-based and may be -1 if the message does not apply to a specific
// line/column. The caller is responsible to do bounds-checking on the line/column.
struct JSLMessage
{
   std::string filename;
   int line, col;
   std::string errName, errType, errMessage;
};

class JavaScriptLint
{
public:
   // The path to the configuration file may be blank. 
   JavaScriptLint(std::string sBinaryPath, std::string sConfigPath);

   bool LintString(std::string code, JSL_OUT std::vector<JSLMessage>& messages,
      JSL_OUT std::string& error);
   bool LintFile(std::string file, JSL_OUT std::vector<JSLMessage>& messages,
      JSL_OUT std::string& error);
   bool LintFiles(std::vector<std::string> files, JSL_OUT std::vector<JSLMessage>& messages,
      JSL_OUT std::string& error);

private:
   bool RunLint(const std::vector<std::string>& files, bool useStdin, std::string code,
      JSL_OUT std::vector<JSLMessage>& messages, JSL_OUT std::string& error);

   std::string m_binaryPath, m_configPath;
};


#endif