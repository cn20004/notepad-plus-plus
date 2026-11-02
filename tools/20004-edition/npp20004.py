#!/usr/bin/env python3
# Notepad++ 20004 Edition companion tools. Python 3.10+, standard library only.
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

PHONE = re.compile(r'(?<!\d)1[3-9]\d{9}(?!\d)')
EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
URL = re.compile(r'https?://[^\s<>"\']+')
DEFAULT_DIR = Path(os.environ.get("NPP20004_HOME", str(Path.home() / "Documents" / "NPP20004")))

def clean(text, dedup=False):
    lines = [re.sub(r'[ \t]+$', '', x).strip('\ufeff') for x in text.replace('\r\n','\n').replace('\r','\n').split('\n')]
    result, seen, empty = [], set(), False
    for line in lines:
        if not line.strip():
            if result and not empty: result.append('')
            empty = True
            continue
        empty = False
        if dedup and line in seen: continue
        seen.add(line)
        result.append(line)
    return '\n'.join(result).strip() + '\n' if result else ''

def extract(text, kind):
    patterns = {'phone': PHONE, 'email': EMAIL, 'url': URL}
    out = patterns[kind].findall(text)
    return list(dict.fromkeys(out))

def redact(text):
    text = PHONE.sub(lambda m: m.group()[:3] + '****' + m.group()[-4:], text)
    text = EMAIL.sub(lambda m: m.group().split('@')[0][:2] + '***@' + m.group().split('@')[1], text)
    return text

def chat_summary(text):
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    keys = ('报名','学费','就业','工资','合同','退费','约定','承诺','明天','后天','联系','电话','到校','面试')
    important = [line for line in lines if any(k in line for k in keys)]
    return '# 聊天整理（规则提取，非 AI 总结）\n\n' + \
        f'原始非空行数：{len(lines)}\n\n## 关键对话\n\n' + \
        ('\n'.join('- ' + redact(line) for line in important[:100]) or '未匹配到预设关键词') + '\n'

def read(path):
    for enc in ('utf-8-sig','utf-16','gb18030'):
        try: return Path(path).read_text(encoding=enc)
        except UnicodeError: pass
    raise ValueError('无法解析文件编码；请转换为 UTF-8 后重试')

def safe_write(path, content, overwrite=False):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f'目标文件存在，拒绝覆盖: {path}（若确认覆盖，增加 --force）')
    fd, tmp = tempfile.mkstemp(prefix='.npp20004-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return path

def ollama(text, prompt, model, endpoint):
    if not (endpoint.startswith('http://127.0.0.1:') or endpoint.startswith('http://localhost:')):
        raise ValueError('为安全起见，仅允许连接本机 Ollama')
    payload = json.dumps({'model':model,'prompt':prompt+'\n\n'+text,'stream':False}, ensure_ascii=False).encode()
    req = urllib.request.Request(endpoint.rstrip('/')+'/api/generate', data=payload, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.loads(response.read().decode())
    return data['response'].strip() + '\n'

def main(argv=None):
    p = argparse.ArgumentParser(description='Notepad++ 20004 Edition: 本地文本与知识库工具')
    p.add_argument('command', choices=['clean','dedup','phones','emails','urls','redact','chat','ollama','daily-log','search'])
    p.add_argument('input', nargs='?', help='源文件；search 模式为检索目录')
    p.add_argument('-o','--output',help='输出文件；不提供时输出到控制台')
    p.add_argument('--force', action='store_true', help='明确允许覆盖输出文件')
    p.add_argument('--date', help='日志日期 YYYY-MM-DD，默认当天')
    p.add_argument('--home',default=str(DEFAULT_DIR),help='知识库根目录，支持 D:/ 或 E:/')
    p.add_argument('--query',help='搜索关键词')
    p.add_argument('--model',default='qwen2.5:7b',help='Ollama 模型名称')
    p.add_argument('--endpoint',default='http://127.0.0.1:11434')
    p.add_argument('--prompt',default='请用中文准确总结下列文本，列出事实、待办和风险，不要编造事实。')
    a = p.parse_args(argv)
    if a.command == 'daily-log':
        date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
        path = Path(a.home).expanduser()/'我的日志'/f'{date:%Y}'/f'{date:%m}'/f'{date:%Y-%m-%d}.md'
        content = f'# {date.isoformat()} 每日日志\n\n## 时间线\n\n## 重要决定\n\n## 跟进事项\n\n## 来源链接\n'
        print(safe_write(path,content,a.force))
        return 0
    if a.command == 'search':
        if not a.input or not a.query: p.error('search 需要目录和 --query')
        root = Path(a.input).expanduser().resolve()
        if not root.is_dir(): p.error('检索路径不是目录')
        found = []
        for path in root.rglob('*'):
            if not path.is_file() or path.suffix.lower() not in ('.txt','.md','.json','.csv','.log'): continue
            try:
                for n,line in enumerate(read(path).splitlines(),1):
                    if a.query.lower() in line.lower():
                        found.append(f'{path}:{n}: {redact(line[:250])}')
                        if len(found)>=1000: break
            except (OSError,UnicodeError,ValueError): continue
            if len(found)>=1000: break
        result = '\n'.join(found)+'\n' if found else '没有找到匹配内容\n'
    else:
        if not a.input: p.error('该操作需要输入文件')
        text = read(a.input)
        if a.command == 'clean': result = clean(text)
        elif a.command == 'dedup': result = clean(text,True)
        elif a.command in ('phones','emails','urls'):
            result = '\n'.join(extract(text,{'phones':'phone','emails':'email','urls':'url'}[a.command]))+'\n'
        elif a.command == 'redact': result = redact(text)
        elif a.command == 'chat': result = chat_summary(text)
        else: result = ollama(text,a.prompt,a.model,a.endpoint)
    if a.output: print(safe_write(a.output,result,a.force))
    else: sys.stdout.write(result)
    return 0

if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError,ValueError,KeyError) as e:
        print(f'错误: {e}', file=sys.stderr)
        sys.exit(1)
