#pragma once
// Notepad++ 20004 Edition — in-process docked AI chat. Windows / WinHTTP.
#include <windows.h>
#include <winhttp.h>
#include <string>
#include <thread>
#include <vector>
#include <memory>
#include <stdexcept>
#include "DockingManager.h"
#include "Edition20004Credential.h"
#include "json/json.hpp"
#pragma comment(lib, "winhttp.lib")
#pragma comment(lib, "advapi32.lib")

namespace Edition20004 {
inline std::string toUtf8(const std::wstring& text) {
    if (text.empty()) return {};
    const int n=WideCharToMultiByte(CP_UTF8,0,text.data(),static_cast<int>(text.size()),nullptr,0,nullptr,nullptr);
    std::string out(n,'\0');
    WideCharToMultiByte(CP_UTF8,0,text.data(),static_cast<int>(text.size()),out.data(),n,nullptr,nullptr);
    return out;
}
inline std::wstring fromUtf8(const std::string& text) {
    if (text.empty()) return {};
    const int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),nullptr,0);
    if(!n) throw std::runtime_error("Invalid response UTF-8");
    std::wstring out(n,L'\0');
    MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text.data(),static_cast<int>(text.size()),out.data(),n);
    return out;
}
inline std::wstring getText(HWND control) {
    int n=GetWindowTextLengthW(control);
    std::wstring text(n+1,L'\0');
    GetWindowTextW(control,text.data(),n+1);
    text.resize(n);
    return text;
}
inline void appendText(HWND control,const std::wstring& s) {
    SendMessageW(control,EM_SETSEL,(WPARAM)-1,(LPARAM)-1);
    SendMessageW(control,EM_REPLACESEL,FALSE,(LPARAM)s.c_str());
}
class HttpHandle {
    HINTERNET h_{};
public:
    explicit HttpHandle(HINTERNET h=nullptr):h_(h){}
    ~HttpHandle(){if(h_) WinHttpCloseHandle(h_);}
    operator HINTERNET() const {return h_;}
    HttpHandle(const HttpHandle&)=delete;
    HttpHandle& operator=(const HttpHandle&)=delete;
};
inline std::string chatRequest(const std::wstring& url,const std::wstring& model,const std::wstring& key,
                               const nlohmann::json& messages) {
    URL_COMPONENTS c{}; c.dwStructSize=sizeof(c);
    wchar_t host[512]{},path[2048]{},extra[1024]{};
    c.lpszHostName=host;c.dwHostNameLength=511;
    c.lpszUrlPath=path;c.dwUrlPathLength=2047;
    c.lpszExtraInfo=extra;c.dwExtraInfoLength=1023;
    if(!WinHttpCrackUrl(url.c_str(),0,0,&c) || c.nScheme!=INTERNET_SCHEME_HTTPS)
        throw std::runtime_error("API URL must use HTTPS");
    const std::wstring target=std::wstring(path)+extra;
    HttpHandle session(WinHttpOpen(L"NotepadPP-20004-Edition/0.1",WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                  WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0));
    if(!session) throw std::runtime_error("WinHttpOpen failed");
    WinHttpSetTimeouts(session,12000,12000,60000,60000);
    HttpHandle connect(WinHttpConnect(session,host,c.nPort,0));
    if(!connect) throw std::runtime_error("WinHttpConnect failed");
    HttpHandle req(WinHttpOpenRequest(connect,L"POST",target.c_str(),nullptr,WINHTTP_NO_REFERER,
                                     WINHTTP_DEFAULT_ACCEPT_TYPES,WINHTTP_FLAG_SECURE));
    if(!req) throw std::runtime_error("WinHttpOpenRequest failed");
    nlohmann::json body={{"model",toUtf8(model)},{"messages",messages},{"stream",false}};
    std::string payload=body.dump();
    std::wstring auth=L"Authorization: Bearer "+key+L"\r\nContent-Type: application/json\r\n";
    if(!WinHttpSendRequest(req,auth.c_str(),static_cast<DWORD>(auth.length()),
        payload.data(),static_cast<DWORD>(payload.size()),static_cast<DWORD>(payload.size()),0)
        || !WinHttpReceiveResponse(req,nullptr)) throw std::runtime_error("HTTPS request failed");
    DWORD status=0,size=sizeof(status);
    WinHttpQueryHeaders(req,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,
                        WINHTTP_HEADER_NAME_BY_INDEX,&status,&size,WINHTTP_NO_HEADER_INDEX);
    if(status!=200) throw std::runtime_error("Provider returned HTTP "+std::to_string(status));
    std::string answer;DWORD available=0;
    do {
        if(!WinHttpQueryDataAvailable(req,&available)) throw std::runtime_error("Response read failed");
        if(answer.size()+available>4*1024*1024) throw std::runtime_error("Response too large");
        if(!available) break;
        std::string part(available,'\0');DWORD read=0;
        if(!WinHttpReadData(req,part.data(),available,&read)) throw std::runtime_error("Response read failed");
        part.resize(read);answer+=part;
    }while(available);
    const auto data=nlohmann::json::parse(answer);
    return data.at("choices").at(0).at("message").at("content").get<std::string>();
}

class NativeAiPanel {
    HWND hwnd_{},output_{},input_{},model_{},endpoint_{},key_{},send_{},save_{},selected_{},reset_{};
    DockingManager* docking_{};
    bool busy_=false;
    nlohmann::json history_=nlohmann::json::array();
    static constexpr UINT finishedMessage_=WM_APP+220;
    struct Result {std::wstring response;std::wstring error; nlohmann::json history;};
    static constexpr int sendId_=2101,saveId_=2102,selectedId_=2103,resetId_=2104;
    static LRESULT CALLBACK proc(HWND w,UINT msg,WPARAM wp,LPARAM lp) {
        auto* self=reinterpret_cast<NativeAiPanel*>(GetWindowLongPtrW(w,GWLP_USERDATA));
        if(msg==WM_NCCREATE) {
            self=static_cast<NativeAiPanel*>(reinterpret_cast<CREATESTRUCTW*>(lp)->lpCreateParams);
            SetWindowLongPtrW(w,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(self));
        }
        if(!self) return DefWindowProcW(w,msg,wp,lp);
        if(msg==WM_SIZE){self->layout(LOWORD(lp),HIWORD(lp));return 0;}
        if(msg==WM_COMMAND) {
            switch(LOWORD(wp)) {
                case sendId_:self->send();return 0;
                case saveId_:self->saveKey();return 0;
                case resetId_:self->history_=nlohmann::json::array();SetWindowTextW(self->output_,L"");return 0;
                case selectedId_: /* This command is also available in editor menu. */ return 0;
            }
        }
        if(msg==finishedMessage_) {
            std::unique_ptr<Result> result(reinterpret_cast<Result*>(lp));
            self->busy_=false;
            EnableWindow(self->send_,TRUE);
            if(!result->error.empty()) appendText(self->output_,L"\r\n[Error] "+result->error+L"\r\n");
            else {
                self->history_=std::move(result->history);
                appendText(self->output_,L"\r\nAI: "+result->response+L"\r\n");
            }
            return 0;
        }
        return DefWindowProcW(w,msg,wp,lp);
    }
    void layout(int width,int height){
        if(!output_)return;
        const int gap=8,w=width-16;
        MoveWindow(model_,8,8,w/2-4,25,TRUE);
        MoveWindow(endpoint_,8+w/2,8,w/2,25,TRUE);
        MoveWindow(key_,8,41,w-110,25,TRUE);MoveWindow(save_,width-98,41,90,25,TRUE);
        int mid=(height-125)*2/3;
        MoveWindow(output_,8,74,w,mid,TRUE);
        MoveWindow(input_,8,82+mid,w-98,height-90-mid,TRUE);
        MoveWindow(send_,width-98,82+mid,90,32,TRUE);
        MoveWindow(reset_,width-98,122+mid,90,30,TRUE);
    }
    HWND edit(DWORD style,const wchar_t* text){
        return CreateWindowExW(WS_EX_CLIENTEDGE,L"EDIT",text,
            WS_CHILD|WS_VISIBLE|WS_TABSTOP|style,0,0,10,10,hwnd_,nullptr,
            GetModuleHandleW(nullptr),nullptr);
    }
    HWND button(const wchar_t* text,int id){
        return CreateWindowExW(0,L"BUTTON",text,WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_PUSHBUTTON,
            0,0,10,10,hwnd_,reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)),GetModuleHandleW(nullptr),nullptr);
    }
    void saveKey(){
        auto key=getText(key_);
        try {
            storeApiKey(key);
            SetWindowTextW(key_,L"");
            appendText(output_,L"[API Key saved to Windows Credential Manager]\r\n");
        }catch(const std::exception&){appendText(output_,L"[Unable to save API key]\r\n");}
    }
    void send(){
        if(busy_)return;
        const auto prompt=getText(input_);
        const auto model=getText(model_);
        const auto url=getText(endpoint_);
        const auto key=loadApiKey();
        if(prompt.empty()||key.empty()||model.empty()) {
            appendText(output_,L"[Enter message, model and save your API Key first]\r\n");return;
        }
        if(prompt.size()>100000){appendText(output_,L"[Message too long]\r\n");return;}
        nlohmann::json messages=history_;
        messages.push_back({{"role","user"},{"content",toUtf8(prompt)}});
        busy_=true;EnableWindow(send_,FALSE);SetWindowTextW(input_,L"");
        appendText(output_,L"\r\nYou: "+prompt+L"\r\n");
        const HWND target=hwnd_;
        std::thread([target,url,model,key,messages=std::move(messages)]() mutable {
            auto result=std::make_unique<Result>();
            try {
                const std::string reply=chatRequest(url,model,key,messages);
                result->response=fromUtf8(reply);
                messages.push_back({{"role","assistant"},{"content",reply}});
                result->history=std::move(messages);
            } catch(const std::exception& ex) {
                result->error=fromUtf8(ex.what());
            }
            if(IsWindow(target) && PostMessageW(target,finishedMessage_,0,
               reinterpret_cast<LPARAM>(result.get()))) result.release();
        }).detach();
    }
public:
    void open(HINSTANCE instance,HWND parent,DockingManager& docking) {
        if(hwnd_){docking.showDockableDlg(hwnd_,TRUE);return;}
        docking_=&docking;
        WNDCLASSW wc{};wc.lpfnWndProc=proc;wc.hInstance=instance;
        wc.lpszClassName=L"Npp20004NativeAiPanel";wc.hCursor=LoadCursor(nullptr,IDC_ARROW);
        wc.hbrBackground=reinterpret_cast<HBRUSH>(COLOR_BTNFACE+1);
        RegisterClassW(&wc);
        hwnd_=CreateWindowExW(0,wc.lpszClassName,L"20004 AI",WS_CHILD|WS_CLIPCHILDREN,
            0,0,420,600,parent,nullptr,instance,this);
        if(!hwnd_)return;
        model_=edit(ES_AUTOHSCROLL,L"deepseek-v4-pro");
        endpoint_=edit(ES_AUTOHSCROLL,L"https://opencode.ai/inference/go/openai/v1/chat/completions");
        key_=edit(ES_PASSWORD|ES_AUTOHSCROLL,L"");
        save_=button(L"Save API Key",saveId_);
        output_=edit(ES_MULTILINE|ES_AUTOVSCROLL|ES_READONLY|WS_VSCROLL,L"20004 AI (native panel)\r\n");
        input_=edit(ES_MULTILINE|ES_AUTOVSCROLL|WS_VSCROLL,L"");
        send_=button(L"Send",sendId_);
        reset_=button(L"New chat",resetId_);
        layout(420,600);
        DockedWidgetData data{};
        data.hClient=hwnd_;
        data.pszName=L"20004 AI - DeepSeek";
        data.dlgID=2100;
        data.uMask=DWS_DF_CONT_RIGHT;
        data.pszModuleName=L"Notepad++20004Internal";
        docking.createDockableDlg(data,CONT_RIGHT,true);
        docking.showDockableDlg(hwnd_,TRUE);
    }
    void askSelection(const std::wstring& selected){
        if(!hwnd_)return;
        SetWindowTextW(input_,(L"请分析下面选中的文本：\r\n"+selected).c_str());
    }
};
inline NativeAiPanel& panel(){static NativeAiPanel instance;return instance;}
}
