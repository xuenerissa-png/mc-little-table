#!/usr/bin/env python3
"""Local-only token configuration UI. Never serves on a public interface."""
import html
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
import webbrowser

CONFIG_DIR = Path.home() / '.config' / 'mc-little-table'
TOKEN_FILE = CONFIG_DIR / 'token'

def save_token(value):
    token = value.strip()
    if not token or '\n' in token or '\r' in token or len(token) > 8192:
        raise ValueError('Token 不能为空、包含换行或超过长度限制')
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    try: os.chmod(CONFIG_DIR, 0o700)
    except OSError: pass
    temp = TOKEN_FILE.with_name('token.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(token)
    os.replace(temp, TOKEN_FILE)
    os.chmod(TOKEN_FILE, 0o600)

def load_token():
    if TOKEN_FILE.is_file(): return TOKEN_FILE.read_text(encoding='utf-8').strip()
    return None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log paths, POST bodies or secrets.
        pass
    def respond(self, code, body, mime='text/html; charset=utf-8'):
        payload=body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(payload)
    def do_GET(self):
        if self.path != '/': return self.respond(404,'Not found','text/plain; charset=utf-8')
        saved = load_token() is not None
        state = '已保存 Token ✓' if saved else '尚未配置 Token'
        page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>麦麦亲子小饭桌 · MCP 设置</title>
<style>body{background:#fff9eb;color:#392f23;font:16px system-ui,-apple-system,sans-serif;margin:0;padding:5vh 16px}.card{max-width:540px;margin:auto;background:white;border:1px solid #f2ddad;border-radius:22px;padding:32px;box-shadow:0 12px 32px #3b2d1912}h1{font-size:27px}p{line-height:1.7;color:#65584a}.status{background:#f9f4e9;border-radius:12px;padding:12px;margin:20px 0}label{display:block;font-weight:700;margin:16px 0 8px}input{width:100%;box-sizing:border-box;border:1px solid #cabfae;border-radius:10px;padding:13px;font-size:16px}button{border:0;background:#f6b719;color:#332100;font-size:16px;font-weight:700;border-radius:12px;padding:12px 22px;cursor:pointer;margin-top:16px}.secondary{background:#f1ece4;margin-left:8px}small{color:#6d655c}</style>
<div class="card"><div style="font-size:38px">🍟</div><h1>麦麦亲子小饭桌</h1><p>麦当劳 MCP · 本地 Token 配置</p><div class="status">''' + html.escape(state) + '''</div>
<form method="post" action="/save"><label for="token">MCP Token</label><input id="token" name="token" type="password" required autocomplete="off" placeholder="粘贴你的麦当劳 MCP Token"><button type="submit">保存到本机</button></form>
<form method="post" action="/delete"><button class="secondary" type="submit">删除已保存 Token</button></form><p><small>🔒 只在 127.0.0.1 本地运行。Token 不显示在页面上，不写入 ZIP；保存文件权限仅当前用户可读。关闭终端即可停止配置服务。</small></p></div></html>'''
        self.respond(200,page)
    def do_POST(self):
        if self.path not in ('/save','/delete'): return self.respond(404,'Not found','text/plain; charset=utf-8')
        # Reject cross-origin browser form submissions.
        origin=self.headers.get('Origin')
        host=self.headers.get('Host','')
        if origin and origin not in ('http://'+host,'http://127.0.0.1:'+host.rsplit(':',1)[-1]):
            return self.respond(403,'Forbidden','text/plain; charset=utf-8')
        length=int(self.headers.get('Content-Length','0'))
        if length>12000: return self.respond(413,'Too large','text/plain; charset=utf-8')
        data=self.rfile.read(length)
        try:
            if self.path=='/save':
                value=parse_qs(data.decode('utf-8'),keep_blank_values=True).get('token',[''])[0]
                save_token(value)
            else:
                TOKEN_FILE.unlink(missing_ok=True)
        except (ValueError, UnicodeError) as e:
            return self.respond(400,html.escape(str(e)),'text/plain; charset=utf-8')
        self.send_response(303); self.send_header('Location','/'); self.send_header('Cache-Control','no-store'); self.end_headers()

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url='http://127.0.0.1:'+str(server.server_port)+'/'
    print('麦麦亲子小饭桌 Token 设置页面：'+url,flush=True)
    print('按 Ctrl+C 关闭。',flush=True)
    webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
