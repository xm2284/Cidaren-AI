#!/usr/bin/env python3
"""
词达人全自动刷题 — 班级共享版
===============================
用法:
  python3 cidaren.py --auto       # 全自动批量刷题
  python3 cidaren.py --check      # 检查 token 是否有效
  python3 cidaren.py --task-id ID # 单独刷指定任务

首次使用:
  1. 用 Fiddler 抓取你的 UserToken (见 README.md)
  2. 填入 config.json 的 user_token 字段
  3. python3 cidaren.py --check   # 验证
  4. python3 cidaren.py --auto    # 开刷!
"""

import hashlib
import json
import os
import random
import re
import ssl
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "run.log")

SECRET = "ajfajfamsnfaflfasakljdlalkflak"
VERSION = "2.7.0.260528_01"
API_BASE = "https://app.vocabgo.com/student/api/Student"
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)

# ============ 工具函数 ============

def md5(s):
    return hashlib.md5(s.encode()).hexdigest()

def now_ms():
    return round(time.time() * 1000)

def log(msg, end="\n"):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, end=end, flush=True)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + end)
    except:
        pass

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ============ 签名 & HTTP ============

def sign_data(data_dict):
    keys = sorted(data_dict.keys())
    parts = []
    for k in keys:
        v = data_dict[k]
        if isinstance(v, (dict, list)):
            v = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        if v == "" or v is None:
            continue
        parts.append(f"{k}={v}")
    raw = "&".join(parts) + SECRET
    return md5(raw)

def add_common_params(data_dict):
    data_dict["app_type"] = 1
    data_dict["timestamp"] = now_ms()
    data_dict["version"] = VERSION
    data_dict["sign"] = sign_data(data_dict)
    return data_dict

def _headers(token, extra=None):
    h = {
        "Host": "app.vocabgo.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": DEFAULT_UA,
        "Origin": "https://app.vocabgo.com",
        "Referer": "https://app.vocabgo.com/",
        "Connection": "keep-alive",
        "ABC": "9c7c7340193fed50e3e6ccac0cbfb1df",
    }
    if token:
        h["UserToken"] = token
    if extra:
        h.update(extra)
    return h

# ============ JV 数据解码 ============

JV_TABLES = {
    "2_1254": [{"site":0,"num":3},{"site":1,"num":2},{"site":31,"num":1},{"site":41,"num":2},{"site":51,"num":1},{"site":87,"num":1},{"site":97,"num":1}],
    "2_10234": [{"site":0,"num":3},{"site":1,"num":4},{"site":39,"num":1},{"site":57,"num":2},{"site":188,"num":1},{"site":259,"num":1},{"site":316,"num":2}],
    "2_9214": [{"site":0,"num":3},{"site":1,"num":4},{"site":41,"num":2},{"site":57,"num":1},{"site":139,"num":2},{"site":272,"num":1},{"site":361,"num":2}],
    "2_9314": [{"site":0,"num":3},{"site":1,"num":4},{"site":31,"num":2},{"site":60,"num":1},{"site":142,"num":2},{"site":275,"num":1},{"site":364,"num":2}],
}

import base64 as _base64

def decode_response(j):
    jv = j.get("jv", "")
    data = j.get("data")
    if not data or not isinstance(data, str):
        return j
    if jv == "99":
        return j
    if jv == "1":
        data = data[32:]
        try:
            j["data"] = json.loads(_base64.b64decode(data).decode("utf-8"))
        except:
            pass
        return j
    if jv.startswith("2_"):
        table = JV_TABLES.get(jv, [])
        for entry in table:
            site, num = entry["site"], entry["num"]
            if site:
                data = data[:site] + data[site + num:]
            else:
                data = data[num:]
        try:
            j["data"] = json.loads(_base64.b64decode(data).decode("utf-8"))
        except:
            pass
        return j
    if jv == "4":
        try:
            j["data"] = json.loads(_base64.b64decode(data).decode("utf-8"))
        except:
            pass
        return j
    return j

# ============ API 请求 ============

def api_get(path, token, params=None):
    if params is None:
        params = {}
    add_common_params(params)
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{path}?{qs}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=_headers(token, {"Referer": "https://app.vocabgo.com/student/"}))
    for _retry in range(5):
        try:
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                raw = resp.read().decode()
                j = json.loads(raw)
                j = decode_response(j)
                return resp.status, json.dumps(j, ensure_ascii=False)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors='ignore')
        except Exception as e:
            if _retry < 4:
                time.sleep(2 + _retry)
                continue
            return 0, str(e)

def api_post(path, token, data=None):
    if data is None:
        data = {}
    add_common_params(data)
    body = json.dumps(data, separators=(",", ":")).encode()
    url = f"{API_BASE}/{path}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = _headers(token, {"Content-Type": "application/json;charset=utf-8"})
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    for _retry in range(5):
        try:
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                raw = resp.read().decode()
                j = json.loads(raw)
                j = decode_response(j)
                return resp.status, json.dumps(j, ensure_ascii=False)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode(errors='ignore')
        except Exception as e:
            if _retry < 4:
                time.sleep(2 + _retry)
                continue
            return 0, str(e)

# ============ Token 验证 ============

def check_token_valid(token):
    status, body = api_get("Main", token)
    if status == 200:
        try:
            j = json.loads(body)
            if j["code"] == 1:
                user = j["data"]["user_info"]
                name = user.get("student_name", user.get("nick_name", "未知"))
                cls = user.get("class_name", "")
                info = f"{name} ({cls})" if cls else name
                log(f"Token 有效 — {info}")
                return True, user
            else:
                log(f"Token 无效: code={j['code']} msg={j.get('msg','')}")
        except:
            pass
    return False, None

# ============ 任务获取 ============

def _is_task_expired(task):
    """判断任务是否已截止（参考 GitHub 版本的逻辑）"""
    now_ms = round(time.time() * 1000)
    start = task.get("start_time", 0)
    over = task.get("over_time", 0)
    if start and over and (start + over) <= now_ms:
        return True
    return False

def get_class_tasks(token):
    log("获取班级任务...")
    all_tasks = []
    for page in range(1, 10):
        status, body = api_get("ClassTask/List", token,
                               {"page_count": page, "page_size": 20})
        if status != 200:
            break
        try:
            j = json.loads(body)
            tasks = j["data"]["task_list"]
            all_tasks.extend(tasks)
            if len(tasks) < 20:
                break
        except:
            break

    active = [t for t in all_tasks
              if t.get("score", 0) < 100
              and not _is_task_expired(t)]
    log(f"  找到 {len(active)} 个待做任务")
    return active

def start_answer(token, task):
    params = {
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        "release_id": task["release_id"],
    }
    status, body = api_get("ClassTask/StartAnswer", token, params)
    try:
        return json.loads(body)
    except:
        log(f"  StartAnswer 响应异常: status={status} body={str(body)[:200]}")
        return {"code": -1}

# ============ AI 兜底答题 ============

def ai_solve_question(content, topic_mode, options=None, word=None, config=None, stem_raw=None, task_words=None):
    """调用 AI API 答题，返回答案字符串或 None"""
    ai_cfg = (config or {}).get("ai", {})
    if not ai_cfg.get("enabled") or not ai_cfg.get("api_key"):
        return None

    api_key = ai_cfg["api_key"]
    base_url = ai_cfg.get("base_url", "https://api.deepseek.com").rstrip("/")
    model = ai_cfg.get("model", "deepseek-chat")

    # 如果content为空或只是占位符，用stem_raw补充信息
    content_display = content if content and content not in ("{}", "[]", "") else ""
    if not content_display and stem_raw:
        content_display = json.dumps(stem_raw, ensure_ascii=False)[:500]

    word_display = urllib.parse.unquote(word) if word else ""
    # 本任务学过的单词列表（答案就在这些词中）
    words_hint = ""
    if task_words:
        words_hint = f"\n本任务学习的单词（答案必在其中）: {', '.join(task_words)}"

    # 构造提示词 - 根据题型定制
    if topic_mode in (51, 73):
        # 选词填空/拼写题: {} 表示空格，答案从 task_words 中选
        prompt = f"""英语选词填空题。题目中 {{}} 表示需要填入的空格，请从下方"可选单词"中选出最合适的一个填入空格。

英文题目: {content_display}
中文含义: {word_display}
可选单词: {', '.join(task_words) if task_words else ('选项中的词' if options else '无')}"""

        if options:
            prompt += f"\n选项:\n{options}"
        prompt += """

只回答一个英文单词(如: responsible), 不要解释, 不要标点。"""
    elif topic_mode == 32:
        prompt = f"""用选项中的词组成短语, 中文含义是「{content_display}」
选项:
{options if options else '无选项'}{words_hint}

请选出正确的词并按正确顺序排列。只回答逗号分隔的选项内容(如: in,many,instances), 不要其他文字。"""
    elif topic_mode in (11, 13, 15, 16, 17, 18, 21, 22, 41, 42, 43, 44, 53, 54):
        prompt = f"""英语选择题，请选出正确答案。

题目: {content_display}
选项:
{options if options else '无选项'}{words_hint}

只回答正确选项的编号(0-{len(options)-1 if options else 9}), 不要其他文字。"""
    else:
        mode_desc = {
            31: "选词补全句子", 52: "拼写填空题",
        }.get(topic_mode, "英语词汇题")
        prompt = f"这是一道{mode_desc}。请根据题目给出答案，只输出答案本身，不要解释。\n\n题目: {content_display}"
        if options:
            prompt += f"\n选项: {options}"
        if word:
            prompt += f"\n提示词: {word_display}"
        if words_hint:
            prompt += words_hint

    # 调用 OpenAI 兼容 API
    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.1,
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            result = json.loads(resp.read().decode())
            msg = result["choices"][0]["message"]
            # 推理模型(如mimo): content是最终答案, reasoning_content是思考过程
            # 只用content，不用reasoning_content
            answer = msg.get("content", "") or ""
            answer = answer.strip()
            # 清理答案中的多余内容
            answer = re.sub(r'^[A-D][.、)\s]+', '', answer)  # 去掉 "A. " 前缀
            answer = answer.strip('"\'`*')
            # 如果答案包含换行，取最后一行（可能有多余解释）
            if "\n" in answer:
                lines = [l.strip() for l in answer.split("\n") if l.strip()]
                answer = lines[-1] if lines else ""
            return answer if answer else None
    except Exception as e:
        log(f" AI_ERR({e})", end="")
        return None

# ============ 答题核心 ============

def verify_answer(token, answer_str, topic_code, task_type="ClassTask"):
    data = {"answer": answer_str, "topic_code": topic_code}
    status, body = api_post(f"ClassTask/VerifyAnswer", token, data)
    try:
        return json.loads(body)
    except:
        return {"code": -1}

def submit_answer(token, topic_code, time_spent, task_type="ClassTask"):
    data = {"topic_code": topic_code, "time_spent": time_spent}
    status, body = api_post(f"ClassTask/SubmitAnswerAndSave", token, data)
    try:
        return json.loads(body)
    except:
        return {"code": -1}

def skip_answer(token, topic_code, topic_mode, task_type="ClassTask"):
    max_t = {11:20,13:35,15:15,16:15,17:10,18:10,
             21:15,22:15,31:25,32:20,41:25,42:25,
             43:30,44:30,51:25,52:25,53:35,54:35,73:20}
    time_spent = max_t.get(topic_mode, 20) * 1000
    data = {"topic_code": topic_code, "time_spent": time_spent}
    status, body = api_post("ClassTask/SubmitAnswerAndSave", token, data)
    try:
        return json.loads(body)
    except:
        return {"code": -1}

def solve_question(token, stem_data, task_id, task_type, release_id, config, task_words=None):
    topic_code = stem_data["topic_code"]
    topic_mode = stem_data["topic_mode"]
    raw_content = stem_data["stem"]["content"]
    # content可能是dict/list，转成JSON字符串
    if isinstance(raw_content, (dict, list)):
        content = json.dumps(raw_content, ensure_ascii=False)
    else:
        content = str(raw_content)
    options = stem_data.get("options", [])
    opts_str = "\n".join(f"{i}. {o.get('content','')}" for i, o in enumerate(options)) if options else ""
    # 获取word字段（选词填空/拼写题需要）
    word = stem_data.get("word", "") or stem_data.get("stem", {}).get("word", "")

    log(f"  [mode={topic_mode}] {content[:50]}", end="")

    # mode 0: 学习卡片，直接跳过不延迟
    if topic_mode == 0:
        log(" skip(card)")
        submit_answer(token, topic_code, 0, task_type)
        return None

    settings = config.get("settings", {})
    min_t = settings.get("delay_per_question", 3)
    max_t = min_t + 2
    time.sleep(random.uniform(min_t * 0.3, max_t * 0.3))

    # === AI 优先答题 ===
    ai_ans = ai_solve_question(content, topic_mode, options=opts_str, word=word, config=config, stem_raw=stem_data, task_words=task_words)
    if ai_ans:
        log(f" AI({ai_ans})", end="")
        # 对于选择题，AI 可能返回编号或内容
        if topic_mode in (11, 13, 15, 16, 17, 18, 21, 22, 41, 42, 43, 44, 53, 54):
            # 选择题: 尝试匹配选项
            ans_to_verify = ai_ans
            try:
                idx = int(ai_ans.strip())
                if 0 <= idx < len(options):
                    ans_to_verify = options[idx].get("content", ai_ans)
            except ValueError:
                pass
            rv_ai = verify_answer(token, ans_to_verify, topic_code, task_type)
        elif topic_mode in (51, 73):
            # 选词填空: AI 返回单词
            rv_ai = verify_answer(token, ai_ans, topic_code, task_type)
        else:
            rv_ai = verify_answer(token, ai_ans, topic_code, task_type)
        rd_ai = rv_ai.get("data", {}) or {}
        if rv_ai.get("code") == 1 and rd_ai.get("answer_result") == 1:
            log(" OK")
            ts = random.randint(int(min_t * 1000), int(max_t * 1000))
            submit_answer(token, rd_ai.get("topic_code", topic_code), ts, task_type)
            return rd_ai
        log(" FAIL", end="")

    # mode 73: 拼写题 (JSON数组格式)
    if topic_mode == 73:
        w_lens = stem_data.get("w_lens", [])
        blank_count = len(w_lens) if w_lens else content.count('{')
        if blank_count == 0:
            blank_count = 1

        blank_arr = json.dumps([""] * blank_count)
        rv = verify_answer(token, blank_arr, topic_code, task_type)
        rd = rv.get("data", {}) or {}

        if rv.get("code") != 1:
            log(" SKIP(api_fail)")
            submit_answer(token, topic_code, 20000, task_type)
            return None

        if rd.get("answer_result") == 1:
            log(" OK(blank)")
            submit_answer(token, rd.get("topic_code", topic_code), 10000, task_type)
            return rd

        word = rd.get("word", "")
        if word:
            word = urllib.parse.unquote(word)
            hints = re.findall(r'\{([^}]+)\}', content)
            if not hints:
                hints = [w[:2] for w in word.split()[-blank_count:]]

            all_words = word.split()
            answers = []
            for hint, wlen in zip(hints, w_lens if len(w_lens) == len(hints) else [len(h) for h in hints]):
                found = None
                for w in all_words:
                    cw = w.strip('.,;:!?()[]{}"')
                    if cw.lower().startswith(hint.lower()) and len(cw) == wlen:
                        found = cw; break
                if not found:
                    for w in all_words:
                        cw = w.strip('.,;:!?()[]{}"')
                        if cw.lower().startswith(hint.lower()):
                            found = cw; break
                if found:
                    answers.append(found)

            if len(answers) == len(hints):
                correct_arr = json.dumps(answers)
                rv2 = verify_answer(token, correct_arr, rd.get("topic_code", topic_code), task_type)
                rd2 = rv2.get("data", {}) or {}
                if rv2.get("code") == 1 and rd2.get("answer_result") == 1:
                    log(f" OK({','.join(answers)})")
                    submit_answer(token, rd2.get("topic_code", rd.get("topic_code", topic_code)), 10000, task_type)
                    return rd2

        log(" SKIP")
        # AI 兜底: mode 73 拼写题匹配失败时尝试 AI
        ai_ans = ai_solve_question(content, topic_mode, word=rd.get("word", ""), config=config, stem_raw=stem_data, task_words=task_words)
        if ai_ans:
            log(f" AI({ai_ans})", end="")
            if blank_count > 1:
                try:
                    ai_list = json.loads(ai_ans) if ai_ans.startswith("[") else [ai_ans]
                    ai_arr = json.dumps(ai_list[:blank_count])
                    rv_ai = verify_answer(token, ai_arr, topic_code, task_type)
                except:
                    rv_ai = verify_answer(token, ai_ans, topic_code, task_type)
            else:
                rv_ai = verify_answer(token, ai_ans, topic_code, task_type)
            rd_ai = rv_ai.get("data", {}) or {}
            if rv_ai.get("code") == 1 and rd_ai.get("answer_result") == 1:
                log(" OK")
                submit_answer(token, rd_ai.get("topic_code", topic_code), 10000, task_type)
                return rd_ai
            log(" FAIL")
        submit_answer(token, topic_code, 20000, task_type)
        return None

    # 通用解法: 两次空白获取正确答案
    rv = verify_answer(token, "", topic_code, task_type)
    rd = rv.get("data", {}) or {}

    if rv.get("code") != 1:
        # AI 兜底: api_fail 时尝试 AI 答题
        ai_ans = ai_solve_question(content, topic_mode, config=config, stem_raw=stem_data, task_words=task_words)
        if ai_ans:
            log(f" AI({ai_ans})", end="")
            rv_ai = verify_answer(token, ai_ans, topic_code, task_type)
            rd_ai = rv_ai.get("data", {}) or {}
            if rv_ai.get("code") == 1 and rd_ai.get("answer_result") == 1:
                log(" OK")
                ts = random.randint(int(min_t * 1000), int(max_t * 1000))
                submit_answer(token, rd_ai.get("topic_code", topic_code), ts, task_type)
                return rd_ai
            log(" FAIL")
        submit_answer(token, topic_code, 20000, task_type)
        return None

    if rd.get("answer_result") == 1:
        log(" OK(blank)")
        ts = random.randint(int(min_t * 1000), int(max_t * 1000))
        submit_answer(token, rd.get("topic_code", topic_code), ts, task_type)
        return rd

    new_tc = rd.get("topic_code", topic_code)
    rv2 = verify_answer(token, "", new_tc, task_type)
    rd2 = rv2.get("data", {}) or {}

    corrects = (rd2.get("answer_corrects") or
                rd2.get("answer") or
                rd2.get("correct_answer") or [])

    if not corrects:
        word = rd2.get("word", "") or rd.get("word", "")
        # AI 兜底: no_corrects 时尝试 AI 答题
        ai_ans = ai_solve_question(content, topic_mode, word=word, config=config, stem_raw=stem_data, task_words=task_words)
        if ai_ans:
            log(f" AI({ai_ans})", end="")
            rv_ai = verify_answer(token, ai_ans, new_tc, task_type)
            rd_ai = rv_ai.get("data", {}) or {}
            if rv_ai.get("code") == 1 and rd_ai.get("answer_result") == 1:
                log(" OK")
                ts = random.randint(int(min_t * 1000), int(max_t * 1000))
                submit_answer(token, rd_ai.get("topic_code", new_tc), ts, task_type)
                return rd_ai
            log(" FAIL")
        else:
            if word:
                log(f" [word={urllib.parse.unquote(word)}]", end="")
        log(" SKIP(no_corrects)")
        skip_answer(token, new_tc, topic_mode, task_type)
        return None

    ans = corrects[0] if isinstance(corrects, list) else corrects

    if topic_mode in (32,):
        if isinstance(ans, str):
            words = ans.split()
            blank_count = content.count('_')
            if len(words) < blank_count:
                expanded = []
                for w in words:
                    if '-' in w:
                        expanded.extend(w.split('-'))
                    else:
                        expanded.append(w)
                words = expanded
            ans = ",".join(words) if len(words) > 1 else ans
        elif isinstance(ans, list):
            ans = ",".join(str(x) for x in ans)

    ans_str = str(ans)
    rv3 = verify_answer(token, ans_str, new_tc, task_type)
    rd3 = rv3.get("data", {}) or {}

    if rv3.get("code") == 1 and rd3.get("answer_result") == 1:
        log(f" OK({ans_str})")
        ts = random.randint(int(min_t * 1000), int(max_t * 1000))
        submit_answer(token, rd3.get("topic_code", new_tc), ts, task_type)
        return rd3
    else:
        # AI 兜底: verify_fail 时尝试 AI 答题
        ai_ans = ai_solve_question(content, topic_mode, config=config, stem_raw=stem_data, task_words=task_words)
        if ai_ans:
            log(f" AI({ai_ans})", end="")
            rv_ai = verify_answer(token, ai_ans, new_tc, task_type)
            rd_ai = rv_ai.get("data", {}) or {}
            if rv_ai.get("code") == 1 and rd_ai.get("answer_result") == 1:
                log(" OK")
                ts = random.randint(int(min_t * 1000), int(max_t * 1000))
                submit_answer(token, rd_ai.get("topic_code", new_tc), ts, task_type)
                return rd_ai
            log(" FAIL")
        log(f" SKIP(verify_fail:{ans_str})")
        skip_answer(token, new_tc, topic_mode, task_type)
        return None

# ============ 学习任务处理 ============

def handle_learning_task(token, task, resp):
    task_id = task["task_id"]
    task_type = task["task_type"]
    collected_words = []  # 收集学习卡片中的单词

    if resp.get("code") == 20001:
        log("   选词中...")
        status, body = api_get("ClassTask/ChoseWordList", token,
                               {"task_id": task_id, "task_type": task_type})
        try:
            j = json.loads(body)
            if j.get("code") == 0 and "权限" in j.get("msg", ""):
                log("   !! 权限不足，跳过此任务")
                return {"code": 0, "msg": "skip"}, collected_words
            word_list = j["data"]["word_list"]
            # 收集选词列表中的单词
            for w in word_list:
                if w.get("word") and w["word"] not in collected_words:
                    collected_words.append(w["word"])
            word_map = {}
            for w in word_list:
                if w.get("score", 0) != 10:
                    key = f"{w['course_id']}:{w['list_id']}"
                    word_map.setdefault(key, []).append(w["word"])
            for w in word_list:
                if sum(len(v) for v in word_map.values()) >= 5:
                    break
                key = f"{w['course_id']}:{w['list_id']}"
                if w["word"] not in word_map.get(key, []):
                    word_map.setdefault(key, []).append(w["word"])
            if word_map:
                api_post("ClassTask/SubmitChoseWord", token,
                         {"task_id": task_id, "task_type": task_type,
                          "word_map": word_map, "chose_err_item": 1, "reset_chose_words": 1})
                log("   选词完成")
                # 选词后重新获取题目（带重试）
                for _r in range(3):
                    resp = start_answer(token, task)
                    if resp.get("code") not in (0, -1):
                        break
                    time.sleep(3)
        except Exception as e:
            log(f"   选词出错: {e}")
            return resp, collected_words

    # 循环跳过所有 mode=0 学习卡片，同时收集单词
    card_count = 0
    while True:
        d = resp.get("data") or resp
        if not (isinstance(d, dict) and d.get("topic_mode") == 0):
            break
        tc = d["topic_code"]
        # 从学习卡片中提取单词
        stem = d.get("stem", {})
        if isinstance(stem, dict):
            card_word = stem.get("word", "") or stem.get("content", "")
            if isinstance(card_word, str) and card_word and card_word not in collected_words:
                # 只收集看起来像英文单词的内容（过滤中文和过长的内容）
                card_word_stripped = card_word.strip()
                if len(card_word_stripped) < 30 and not all('\u4e00' <= c <= '\u9fff' for c in card_word_stripped):
                    collected_words.append(card_word_stripped)
        submit_answer(token, tc, 0, task_type)
        card_count += 1
        # 获取下一题（带重试）
        for _r in range(3):
            resp = start_answer(token, task)
            if resp.get("code") not in (0, -1):
                break
            time.sleep(2)
        if resp.get("code") in (0, -1):
            break
    if card_count > 0:
        log(f"   已跳过 {card_count} 张学习卡片")
    if collected_words:
        log(f"   收集到 {len(collected_words)} 个单词: {', '.join(collected_words[:10])}{'...' if len(collected_words) > 10 else ''}")

    return resp, collected_words

# ============ 执行单个任务 ============

def do_task(token, task, config):
    t_name = task["task_name"]
    task_type = "ClassTask" if task.get("task_type") in (1, 2) else "MyselfTask"
    release_id = task["release_id"]
    max_rounds = 10
    task_words = []  # 本轮学习的单词列表（每轮重置后更新）
    prev_score = task.get("score", 0)  # 上一轮分数，用于判断是否卡住
    stuck_count = 0  # 连续分数未提升的轮次

    log(f"\n{'='*40}")
    log(f"{t_name}")

    for round_num in range(1, max_rounds + 1):
        if round_num > 1:
            log(f"  --- 第 {round_num} 轮 ---")
            time.sleep(1)  # 重置后等1秒

        # 获取答题数据（带网络重试），每轮重新收集单词
        resp, new_words = _start_with_retry(token, task, max_retries=3)
        if new_words:
            task_words = new_words  # 每轮重置后用新单词替换
        if resp is None:
            log(f"  网络错误，跳过此任务")
            return

        # 如果没有从学习卡片收集到单词，主动获取单词列表
        if not task_words:
            try:
                status, body = api_get("ClassTask/ChoseWordList", token,
                    {"task_id": task["task_id"], "task_type": task["task_type"]})
                j = json.loads(body)
                if j.get("code") == 1 and isinstance(j.get("data"), dict):
                    wl = j["data"].get("word_list", [])
                    task_words = [w["word"] for w in wl if w.get("word")]
                    if task_words:
                        log(f"  获取单词列表: {', '.join(task_words[:10])}{'...' if len(task_words) > 10 else ''}")
            except Exception as e:
                log(f"  获取单词列表失败: {e}")

        if resp.get("code") == 0 and resp.get("msg") == "skip":
            log(f"  跳过: 无权限")
            return

        data = resp.get("data")
        if not isinstance(data, dict):
            log("  无法获取答题数据")
            return

        q_count = 0  # 本轮答题数
        while True:
            code = resp.get("code", -1)
            d = resp.get("data", resp)

            if code == 20004:
                log("  任务已完成 (20004)")
                break

            if code == 20001:
                # 选词阶段，需要处理选词后继续答题
                log("  需要选词，处理中...")
                resp, sel_words = handle_learning_task(token, task, resp)
                if sel_words:
                    task_words = sel_words  # 选词后更新单词列表
                log(f"  选词处理完 code={resp.get('code')}")
                # 选词完成后重新获取题目
                resp2, extra_words = _start_with_retry(token, task, max_retries=3)
                if extra_words and not sel_words:
                    task_words = extra_words
                if resp2 is None:
                    log("  选词后获取题目失败")
                    break
                resp = resp2
                continue

            # 先检查是否有题目可答，再看是否完成
            if "stem" in d:
                solve_question(token, d, task["task_id"], task_type, release_id, config, task_words)
                q_count += 1
                # 每答3题实时显示一次分数
                if q_count % 3 == 0:
                    cur_score = _get_task_score(token, release_id, task_type)
                    log(f"  [{q_count}题] 当前分数: {cur_score:.1f}")
            elif code == 1:
                done = d.get("topic_done_num", 0)
                total = d.get("topic_total", 0)
                if done >= total and total > 0:
                    log(f"  题目完成 {done}/{total}")
                    break
                else:
                    log(f"  无题目数据 (done={done}/{total}, code={code})")
                    break
            else:
                log(f"  异常 code={code}")
                break

            params = {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "release_id": release_id,
            }
            # 获取下一题（带重试）
            next_resp = None
            for _retry in range(5):
                try:
                    status, body = api_get("ClassTask/StartAnswer", token, params)
                    next_resp = json.loads(body)
                    break
                except Exception as e:
                    log(f"  获取下一题失败: {e}, 重试...")
                    time.sleep(2 + _retry)
            if next_resp is None:
                log(f"  获取下一题失败，跳过")
                break
            resp = next_resp

            time.sleep(random.uniform(0.1, 0.3))

        score = _get_task_score(token, release_id, task_type)
        log(f"  第 {round_num} 轮完成，分数: {score:.1f}")

        if score >= 100:
            log(f"  满分!")
            return

        # 判断分数是否卡住（连续2轮没有提升）
        if score <= prev_score + 0.1:
            stuck_count += 1
        else:
            stuck_count = 0
        prev_score = score

        if stuck_count >= 2:
            log(f"  分数连续 {stuck_count} 轮未提升 ({score:.1f}分)，跳过此任务")
            return

        # 分数不够，尝试重置任务再刷
        if round_num < max_rounds:
            log(f"  分数未满分，尝试重置任务...")
            r_reset = json.loads(api_get("ClassTask/ChoseWordList", token,
                               {"task_id": task["task_id"], "task_type": task["task_type"]})[1])
            if r_reset.get("code") == 1:
                wl = r_reset["data"]["word_list"]
                wm = {}
                for w in wl[:10]:
                    k = f"{w['course_id']}:{w['list_id']}"
                    if k not in wm: wm[k] = []
                    wm[k].append(w['word'])
                r2 = json.loads(api_post("ClassTask/SubmitChoseWord", token,
                    {"task_id": task["task_id"], "task_type": task["task_type"],
                     "word_map": wm, "chose_err_item": 1, "reset_chose_words": 1})[1])
                if r2.get("code") == 1:
                    log(f"  重置成功，开始新一轮")
                    continue
            log(f"  重置失败，停止重试")
            return
        else:
            log(f"  已达最大重试次数 ({max_rounds})")

def _start_with_retry(token, task, max_retries=3):
    """带网络重试的 start_answer + 跳过学习卡片，返回 (resp, task_words)"""
    task_words = []
    for attempt in range(max_retries):
        log(f"  正在获取题目...")
        resp = start_answer(token, task)
        log(f"  获取题目返回 code={resp.get('code')}")

        # 只处理学习卡片(mode=0)，不处理选词(20001)
        if isinstance(resp.get("data") or resp, dict) and (resp.get("data") or resp).get("topic_mode") == 0:
            resp, words = handle_learning_task(token, task, resp)
            task_words.extend(w for w in words if w not in task_words)
            log(f"  学习阶段处理完 code={resp.get('code')}")

        if resp.get("code") == 0 and resp.get("msg") == "skip":
            return resp, task_words

        if resp.get("code") in (0, -1):
            wait = 3 + attempt * 2
            log(f"  网络错误 (重试 {attempt+1}/{max_retries}, {wait}s后)...")
            time.sleep(wait)
            continue

        return resp, task_words  # 成功

    return None, task_words  # 全部重试失败

def _get_task_score(token, release_id, task_type="ClassTask"):
    status, body = api_get("ClassTask/List", token,
                           {"page_count": 1, "page_size": 100})
    try:
        for t in json.loads(body)["data"]["task_list"]:
            if t.get("release_id") == release_id:
                return t.get("score", 0)
    except:
        pass
    return 0

# ============ 主入口 ============

def main():
    import argparse
    p = argparse.ArgumentParser(description="词达人全自动刷题")
    p.add_argument("--check", action="store_true", help="检查 token")
    p.add_argument("--task-id", type=str, help="指定任务ID")
    p.add_argument("--auto", action="store_true", help="全自动模式")
    p.add_argument("--all", action="store_true", help="全自动+所有任务(含已完成)")
    args = p.parse_args()

    config = load_config()
    token = config.get("user_token", "")

    if not token:
        log("请先在 config.json 中设置 user_token")
        log("获取方法: 用 Fiddler 抓包, 见 README.md")
        return

    ok, user = check_token_valid(token)
    if not ok:
        log("Token 无效或已过期，请重新抓取")
        return

    if args.check:
        return

    config["user_token"] = token
    save_config(config)

    tasks = get_class_tasks(token)

    if not tasks:
        log("没有待做任务")
        return

    log(f"\n待做任务 ({len(tasks)} 个):")
    for i, t in enumerate(tasks):
        ttype = {1: "学习", 2: "测试"}.get(t.get("task_type", 1), "?")
        log(f"  [{i+1}] [{ttype}] {t['task_name']} ({t.get('score',0):.1f}分)")

    if args.auto or args.all:
        selected = tasks if args.all else [t for t in tasks if t.get('score', 0) < 100]
        log(f"\n全自动模式: 运行 {len(selected)} 个任务\n")
        for i, t in enumerate(selected):
            log(f"[{i+1}/{len(selected)}] {t['task_name']}")
            try:
                do_task(token, t, config)
            except Exception as e:
                log(f"  !! 任务异常: {e}")
                time.sleep(5)
        log("\n===== 全部完成! =====")
        _print_final_scores(token)
        return

    if args.task_id:
        for t in tasks:
            if str(t.get("task_id")) == args.task_id or str(t.get("release_id")) == args.task_id:
                do_task(token, t, config)
                return
        log(f"未找到任务ID: {args.task_id}")
        return

    log("\n输入序号(空格分隔多个), 留空=全部, a=全自动: ", end="")
    try:
        choice = input().strip()
    except EOFError:
        choice = ""

    if not choice:
        selected = tasks
    elif choice.lower() == 'a':
        selected = [t for t in tasks if t.get('score', 0) < 100]
    else:
        selected = []
        for c in choice.split():
            try:
                idx = int(c) - 1
                if 0 <= idx < len(tasks):
                    selected.append(tasks[idx])
            except:
                pass

    for t in selected:
        do_task(token, t, config)

    if not choice or choice.lower() == 'a':
        log("\n===== 全部完成! =====")
        _print_final_scores(token)

def _print_final_scores(token):
    status, body = api_get("ClassTask/List", token, {"page_count": 1, "page_size": 100})
    try:
        tasks = json.loads(body)["data"]["task_list"]
        total_score = sum(t.get('score', 0) for t in tasks)
        log(f"总得分: {total_score:.1f}")
        for t in tasks:
            if t.get('score', 0) > 0:
                log(f"  {t['task_name']}: {t['score']:.1f}分")
    except:
        pass

if __name__ == "__main__":
    main()
