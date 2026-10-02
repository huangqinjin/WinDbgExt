#include <windows.h>
#include <cstdio>

int main(int argc, char* argv[])
{
    if (IsDebuggerPresent())
    {
        OutputDebugStringA("Hello Debugger!\n");
        DebugBreak();
    }

    std::printf("%s", "Hello World!\n");
}
