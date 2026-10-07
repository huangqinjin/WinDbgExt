#ifdef _DLL
#define _AFXDLL
#endif
#define NO_WARN_MBCS_MFC_DEPRECATION
#include <afxcoll.h>
#include <windows.h>
#include <cstdio>

CStringA NarrowStringInstance;
CStringW WideStringInstance;
CStringArray StringArrayInstance;

int main(int argc, char* argv[])
{
    NarrowStringInstance.Append("A Narrow String Instance");
    WideStringInstance.Append(L"A Wide String Instance");
    StringArrayInstance.Add(_T("A"));
    StringArrayInstance.Add(_T("String"));
    StringArrayInstance.Add(_T("Array"));
    StringArrayInstance.Add(_T("Instance"));

    if (IsDebuggerPresent())
    {
        DebugBreak();
    }

    std::printf("%s\n", "Hello World!");
}
