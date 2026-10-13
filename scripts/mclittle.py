#!/usr/bin/env python3
"""McLittle Table: child-focused sodium comparison with McDonald's MCP."""
import argparse, json, os, re, sys, uuid, urllib.request

URL = 'https://mcp.mcd.cn'
GUIDE = [(1,3,1200),(4,8,1500),(9,12,1800)]  # US DGA 2025-2030, mg/day; <, not <=


def sodium_limit(age):
    for lo,hi,limit in GUIDE:
        if lo <= age <= hi: return limit
    raise ValueError('仅支持 1–12 岁儿童')


def parse_toon(value):
    """Parse McD nutrition compact toon payload, retaining only reliable columns."""
    if isinstance(value, dict):
        if 'data' in value: return parse_toon(value['data'])
        if 'productName' in value: return [value]
        return []
    if isinstance(value, list):
        out=[]
        for x in value: out.extend(parse_toon(x))
        return out
    if not isinstance(value,str): return []
    s=value.strip()
    # Some deployments wrap the payload in markdown docs; extract the embedded JSON object.
    marker=s.find('## Original Response')
    if marker>=0:
        brace=s.find('{',marker)
    elif s.startswith('#'):
        brace=s.find('{')
    else:
        brace=0
    if brace>0:
        s=s[brace:]
    try:
        decoded=json.loads(s)
        if decoded != value: return parse_toon(decoded)
    except (ValueError,TypeError): pass
    match=re.search(r'\{([^}]+)\}\s*:',s)
    if not match: return []
    columns=[x.strip() for x in match.group(1).split(',')]
    out=[]
    for line in s[match.end():].splitlines():
        row=[x.strip() for x in line.strip().split(',')]
        if len(row)==len(columns): out.append(dict(zip(columns,row)))
    return out


def number(v):
    try:
        if v is None or str(v).strip().lower() in ('','null','none','-'): return None
        return float(str(v).replace(',',''))
    except (TypeError,ValueError): return None


def analyze(rows, age, budget=None, avoid=None):
    limit=sodium_limit(age)
    if budget is not None and budget <= 0: raise ValueError('本餐预算必须大于 0')
    avoid=[x.strip().lower() for x in (avoid or []) if x.strip()]
    result=[]
    for r in rows:
        name=str(r.get('productName') or r.get('name') or '').strip()
        if not name: continue
        if any(x in name.lower() for x in avoid): continue
        # Conservative name-only screening: unknown spice/allergens are never declared safe.
        if any(x in name.lower() for x in ['辣','香辣','麻辣','spicy','chili','hot & spicy']): continue
        sodium=number(r.get('sodium'))
        if sodium is None or sodium < 0: continue
        result.append({'name':name,'sodium_mg':sodium,'daily_reference_mg':limit,
                       'daily_reference_fraction':round(sodium/limit,3),
                       'within_user_meal_budget':None if budget is None else sodium <= budget,
                       'energy_kcal':number(r.get('energyKcal')),
                       'protein_g':number(r.get('protein')),
                       'note':'仅为营养数据筛选；未验证过敏原、实际辣度、幼儿进食安全或门店可售。'})
    return sorted(result,key=lambda x:x['sodium_mg'])


def compare(rows, old, new):
    by_name={r['name']:r for r in rows}
    if old not in by_name or new not in by_name: raise ValueError('未找到可核实的两款餐品')
    a,b=by_name[old],by_name[new]
    return {'from':old,'to':new,'sodium_change_mg':round(b['sodium_mg']-a['sodium_mg'],2),
            'energy_change_kcal':None if a['energy_kcal'] is None or b['energy_kcal'] is None else round(b['energy_kcal']-a['energy_kcal'],2),
            'notice':'仅比较独立餐品；不代表官方套餐允许替换。'}


class MCP:
    def __init__(self, token=None, url=URL):
        self.token=token or os.environ.get('MCD_MCP_TOKEN')
        if not self.token:
            try:
                from token_settings import load_token
                self.token=load_token()
            except ImportError:
                pass
        if not self.token: raise RuntimeError('缺少 MCD_MCP_TOKEN；请在本机配置，勿发到聊天或提交仓库')
        self.url=url; self.session=None; self.version='2025-03-26'; self.next_id=0

    def send(self,method,params=None,notification=False):
        self.next_id+=1
        obj={'jsonrpc':'2.0','method':method}
        if not notification: obj['id']=self.next_id
        if params is not None: obj['params']=params
        headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json',
                 'Accept':'application/json, text/event-stream','MCP-Protocol-Version':self.version}
        if self.session: headers['Mcp-Session-Id']=self.session
        req=urllib.request.Request(self.url,data=json.dumps(obj).encode(),headers=headers,method='POST')
        with urllib.request.urlopen(req,timeout=35) as res:
            self.session=res.headers.get('Mcp-Session-Id',self.session)
            if notification: return None
            body=res.read().decode('utf-8')
            if 'text/event-stream' in res.headers.get('Content-Type',''):
                for block in re.split(r'\r?\n\r?\n',body):
                    lines=[ln[5:].strip() for ln in block.splitlines() if ln.startswith('data:')]
                    if not lines: continue
                    try: data=json.loads('\n'.join(lines))
                    except ValueError: continue
                    if data.get('id')==obj['id']: break
                else: raise RuntimeError('SSE 中没有匹配的 JSON-RPC 响应')
            else: data=json.loads(body)
            if 'error' in data: raise RuntimeError('MCP 返回错误: '+str(data['error']))
            return data.get('result',data)

    def initialize(self):
        r=self.send('initialize',{'protocolVersion':self.version,'capabilities':{},
                                 'clientInfo':{'name':'mc-little-table','version':'0.1.0'}})
        self.version=r.get('protocolVersion',self.version)
        self.send('notifications/initialized',notification=True)
        return r

    def tools(self): return self.send('tools/list').get('tools',[])
    def call(self,name,args=None): return self.send('tools/call',{'name':name,'arguments':args or {}})


def unwrap_tool(response):
    if response.get('isError'): raise RuntimeError('MCP 工具执行失败')
    for part in response.get('content',[]):
        if part.get('type')=='text':
            try: return json.loads(part['text'])
            except ValueError: return part['text']
    return response.get('structuredContent',response)


def extract_payload(value):
    """Return the embedded JSON object from an MCP text payload (markdown-wrapped or plain)."""
    if isinstance(value,dict): return value
    s=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)
    marker=s.find('## Original Response')
    brace=s.find('{',marker if marker>=0 else 0)
    if brace<0: return {}
    try: return json.loads(s[brace:])
    except ValueError: return {}


def main():
    p=argparse.ArgumentParser(description='麦麦亲子小饭桌 · 1–12 岁儿童营养比较')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('tools',help='查看 MCP 实际可用工具及参数')
    f=sub.add_parser('nutrition',help='拉取官方营养数据并按钠排序')
    f.add_argument('--age',type=int,required=True); f.add_argument('--meal-budget',type=float)
    f.add_argument('--avoid',default='',help='逗号分隔的名称排除词，如 辣,咖啡')
    f.add_argument('--top',type=int,default=12)
    f.add_argument('--save',help='将原始营养响应保存到本地文件（不要上传含个人信息的文件）')
    c=sub.add_parser('compare',help='比较本地已获取的营养数据中的两款餐品')
    c.add_argument('--file',required=True); c.add_argument('--age',type=int,required=True)
    c.add_argument('--from-name',required=True); c.add_argument('--to-name',required=True)
    t=sub.add_parser('call',help='按 tools/list 的真实 schema 调用指定工具')
    t.add_argument('tool'); t.add_argument('--args',default='{}',help='JSON 对象')
    a=p.parse_args()
    if a.cmd=='compare':
        with open(a.file,encoding='utf-8') as fp: raw=json.load(fp)
        rows=analyze(parse_toon(raw),a.age)
        print(json.dumps(compare(rows,a.from_name,a.to_name),ensure_ascii=False,indent=2)); return
    if a.cmd=='nutrition': sodium_limit(a.age)
    client=MCP(); client.initialize()
    if a.cmd=='tools': result=client.tools()
    elif a.cmd=='call':
        args=json.loads(a.args)
        if not isinstance(args,dict): raise ValueError('--args 必须是 JSON 对象')
        names={t['name'] for t in client.tools()}
        if a.tool not in names: raise ValueError('服务器未提供此工具：'+a.tool)
        result=unwrap_tool(client.call(a.tool,args))
    else:
        names={t['name'] for t in client.tools()}
        if 'list-nutrition-foods' not in names: raise RuntimeError('服务器没有 list-nutrition-foods')
        result=unwrap_tool(client.call('list-nutrition-foods'))
        if a.save:
            with open(a.save,'w',encoding='utf-8') as fp: json.dump(result,fp,ensure_ascii=False,indent=2)
        rows=parse_toon(result)
        result={'age':a.age,'daily_sodium_reference_mg':sodium_limit(a.age),
                'reference':'美国 2025–2030 膳食指南；每日上限，不是每餐标准',
                'meal_budget_mg':a.meal_budget,'data_count':len(rows),
                'candidates':analyze(rows,a.age,a.meal_budget,a.avoid.split(','))[:a.top],
                'caveat':'仅为营养数据排名；需要另查门店在售、配料、过敏原、辣度与食物质地。'}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('错误：'+str(exc),file=sys.stderr); sys.exit(1)
