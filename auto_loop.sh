#!/bin/bash
# 词达人全自动循环刷题 — 跑到分数稳定
cd /home/mikt06/词达人

LAST_SCORE=0
STABLE_COUNT=0
MAX_STABLE=2  # 连续2次不涨分就停

while true; do
    echo "===== $(date '+%H:%M:%S') 开始新一轮 ====="
    python3 cidaren.py --auto 2>&1 | tail -5

    # 提取总分
    SCORE=$(grep "总得分:" run.log | tail -1 | grep -oP '[0-9.]+')

    if [ "$SCORE" = "$LAST_SCORE" ]; then
        STABLE_COUNT=$((STABLE_COUNT + 1))
        echo "分数未变: ${SCORE} (连续${STABLE_COUNT}次)"
        if [ $STABLE_COUNT -ge $MAX_STABLE ]; then
            echo "===== 分数稳定，结束 ====="
            echo "最终得分: ${SCORE}"
            break
        fi
    else
        STABLE_COUNT=0
        echo "分数变化: ${LAST_SCORE} → ${SCORE} (+$(echo "$SCORE - $LAST_SCORE" | bc))"
    fi
    LAST_SCORE=$SCORE

    sleep 10
done

echo ""
echo "===== 最终成绩 ====="
python3 -c "
import json, hashlib, ssl, urllib.request, time, base64
TOKEN='f625f133de4b8e8962826f8fdef363b4'
API='https://app.vocabgo.com/student/api/Student'
SECRET='ajfajfamsnfaflfasakljdlalkflak'
VERSION='2.7.0.260528_01'
def md5(s):return hashlib.md5(s.encode()).hexdigest()
def ns():return round(time.time()*1000)
def si(d):
    ks=sorted(d.keys());ps=[]
    for k in ks:
        v=d[k]
        if isinstance(v,(dict,list)):v=json.dumps(v,separators=(',',':'),ensure_ascii=False)
        if v==''or v is None:continue
        ps.append(f'{k}={v}')
    return md5('&'.join(ps)+SECRET)
def ac(d):
    d['app_type']=1;d['timestamp']=ns();d['version']=VERSION;d['sign']=si(d);return d
H={'Host':'app.vocabgo.com','Accept':'application/json, text/plain, */*',
   'User-Agent':'Mozilla/5.0','Origin':'https://app.vocabgo.com',
   'Referer':'https://app.vocabgo.com/student/',
   'ABC':'9c7c7340193fed50e3e6ccac0cbfb1df','UserToken':TOKEN,
   'Content-Type':'application/json;charset=utf-8','X-Requested-With':'XMLHttpRequest'}
def post(path,data):
    ac(data);body=json.dumps(data,separators=(',',':')).encode()
    req=urllib.request.Request(f'{API}/{path}',data=body,headers=H,method='POST')
    with urllib.request.urlopen(req,timeout=15,context=ssl.create_default_context())as r:
        return json.loads(r.read().decode())

tasks=post('ClassTask/PageTask',{'search_type':'1','page_count':1,'page_size':100})
records=tasks['data']['records']
total=sum(t.get('score',0)for t in records)
print(f'总得分: {total:.1f}')
high=[t for t in records if t.get('score',0)>=80]
mid=[t for t in records if 60<=t.get('score',0)<80]
low=[t for t in records if 0<t.get('score',0)<60]
zero=[t for t in records if t.get('score',0)==0]
print(f'🟢 ≥80: {len(high)}个')
print(f'🟡 60-79: {len(mid)}个')
print(f'🔴 <60: {len(low)}个')
print(f'⚫ 0分(权限): {len(zero)}个')
" 2>&1