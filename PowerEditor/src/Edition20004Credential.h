#pragma once
// 20004 Edition secure API key storage.
// Windows Credential Manager encrypts the secret under the current Windows user.
// No API key is written to config.xml, logs or the Git repository.
#include <windows.h>
#include <wincred.h>
#include <string>
#include <stdexcept>
#include <vector>

namespace Edition20004 {
inline constexpr wchar_t CredentialTarget[] = L"NotepadPP-20004-Edition/OpenCode-Go";

inline void storeApiKey(const std::wstring& apiKey) {
    if (apiKey.empty()) throw std::invalid_argument("Empty API key");
    if (apiKey.size() * sizeof(wchar_t) > CRED_MAX_CREDENTIAL_BLOB_SIZE)
        throw std::invalid_argument("API key too long");
    CREDENTIALW entry{};
    entry.Type = CRED_TYPE_GENERIC;
    entry.TargetName = const_cast<wchar_t*>(CredentialTarget);
    entry.CredentialBlobSize = static_cast<DWORD>(apiKey.size() * sizeof(wchar_t));
    entry.CredentialBlob = reinterpret_cast<LPBYTE>(const_cast<wchar_t*>(apiKey.data()));
    entry.Persist = CRED_PERSIST_LOCAL_MACHINE;
    entry.UserName = const_cast<wchar_t*>(L"20004 Edition");
    if (!::CredWriteW(&entry, 0)) throw std::runtime_error("CredWriteW failed");
}

inline std::wstring loadApiKey() {
    PCREDENTIALW entry = nullptr;
    if (!::CredReadW(CredentialTarget, CRED_TYPE_GENERIC, 0, &entry))
        return {};
    std::wstring result;
    if (entry && entry->CredentialBlob && entry->CredentialBlobSize % sizeof(wchar_t) == 0)
        result.assign(reinterpret_cast<const wchar_t*>(entry->CredentialBlob),
                      entry->CredentialBlobSize / sizeof(wchar_t));
    if (entry) ::CredFree(entry);
    return result;
}

inline void deleteApiKey() {
    ::CredDeleteW(CredentialTarget, CRED_TYPE_GENERIC, 0);
}
}
