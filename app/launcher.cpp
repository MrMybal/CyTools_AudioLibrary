// Windows launcher: opens the Dear ImGui interface with the private runtime, without a console.
// The working directory is always the tool root, so the executable behaves the same from any folder.
// Paths use forward slashes on purpose: Win32 accepts them and no escape sequence can be mangled.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <string>

static void fail(const wchar_t* message) { MessageBoxW(nullptr, message, L"CyTools AudioLibrary", MB_ICONERROR); }

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR arguments, int) {
    wchar_t buffer[32768];
    const DWORD length = GetModuleFileNameW(nullptr, buffer, 32768);
    if (length == 0 || length >= 32768) { fail(L"Cannot read the path of the executable."); return 1; }
    std::wstring root(buffer, length);
    const wchar_t separators[] = { L'/', static_cast<wchar_t>(92), 0 };      // '/' and the backslash (code 92)
    const size_t separator = root.find_last_of(separators);
    if (separator == std::wstring::npos) { fail(L"Unexpected executable path."); return 1; }
    root.resize(separator);
    const std::wstring python = root + L"/runtime/python/Scripts/pythonw.exe";
    if (GetFileAttributesW(python.c_str()) == INVALID_FILE_ATTRIBUTES) {
        fail(L"The private runtime is missing. Open LISEZ-MOI.md, then run app/Install.ps1 in PowerShell to create runtime/python.");
        return 2;
    }
    const std::wstring bootstrap = root + L"/runtime/bootstrap.py";
    if (GetFileAttributesW(bootstrap.c_str()) == INVALID_FILE_ATTRIBUTES) { fail(L"runtime/bootstrap.py is missing: incomplete installation."); return 3; }
    const std::wstring quote(1, static_cast<wchar_t>(34));                  // the double quote (code 34)
    std::wstring command = quote + python + quote + L" " + quote + bootstrap + quote;
    if (arguments && *arguments) { command += L" "; command += arguments; }
    command.push_back(static_cast<wchar_t>(0));
    STARTUPINFOW startup{}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(python.c_str(), command.data(), nullptr, nullptr, FALSE, 0, nullptr, root.c_str(), &startup, &process)) {
        fail(L"Cannot start the private runtime."); return 4;
    }
    CloseHandle(process.hThread); CloseHandle(process.hProcess);
    return 0;
}
