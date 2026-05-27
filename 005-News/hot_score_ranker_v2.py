#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hot_score_ranker_v2.py · v2 · 2026-05-03
每日舆情热点事件评分排名器（含来源URL）

新功能：
  - 从溯源元数据文件读取原始出处URL
  - 实体新增 sources[] 字段
  - 每日 cron 后自动更新实体库

用法：
  PYTHONPATH=/workspace/.python-packages /workspace/.python-venv/bin/python3 \
    /workspace/scripts/hot_score_ranker_v2.py --date 2026-05-03

  --update-db   运行后同时更新实体库（cron 后调用）
  --candidates  今日候选事件标题（用 | 分隔）
"""
import sys, os, json, argparse
from datetime import datetime
from collections import defaultdict

DB_PATH     = '/workspace/005-News/hotspot_event_db_v2.json'
META_DIR    = '/workspace/005-News/{date}'   # 兼容旧格式，sources_metadata.json 已废弃
OUT_PATH    = '/workspace/005-News/hotspot_today_rank_{date}.json'

# ── 评分函数 ────────────────────────────────────────
def parse_date(s):
    return datetime.strptime(s, '%Y-%m-%d')

def score_event(entity, today_str, candidate_rank=None):
    today    = parse_date(today_str)
    last     = parse_date(entity['last_seen'])
    days_ago = (today - last).days
    TR = max(0, 100 - days_ago * 18)
    PD = min(100, entity['persistence'] * 15)
    IM = max(0, 108 - (candidate_rank or 5) * 12) if candidate_rank else 60
    VA = {'🔴【新】': 100, '🟡【续】': 72, '⚪【补】': 45}.get(
        entity['markers'][0], 50)
    DE = -max(0, (days_ago - 3) * 8) if days_ago > 3 else 0
    total = TR*0.35 + PD*0.20 + IM*0.20 + VA*0.15 + max(0, 100+DE)*0.10
    return round(total, 1), {
        'TR': round(TR, 1), 'PD': round(PD, 1),
        'IM': round(IM, 1), 'VA': VA, 'DE': DE
    }

# ── 核心：关键词匹配实体 ────────────────────────────
STOP_WORDS = {
    '发布', '首个', '首次', '正式', '全球', '最新', '亿美元', '万美元',
    '融资', '上市', '合作', '突破', '革命', '免费', '全面', '首超',
    '最强', '史上', '联手', '崛起', '时代', '布局', '落地', '爆发',
    '引发', '风暴', '震荡', '深度', '曝光', '确认', '揭秘',
    '大模型', '里程碑', '国产', 'OpenAI', 'AI模型', 'LLM',
}

def extract_keywords(title):
    t = title
    for ch in '🔴🟡⚪【】⭐\d️⃣🆕，。、！？：；""''（）()·—\\-/':
        t = t.replace(ch, ' ')
    words = [w for w in t if len(w) >= 3 and w not in STOP_WORDS]
    return words

def match_entity(title, db_list):
    """用关键词匹配实体库，返回最佳匹配实体或None"""
    kws = extract_keywords(title)
    best, best_score = None, 0
    for e in db_list:
        e_kws = set(e.get('core_keywords', []))
        overlap = len(set(kws) & e_kws)
        if overlap > best_score:
            best_score = overlap
            best = e
    return best, best_score

# ── 加载溯源元数据 ─────────────────────────────────
def load_sources_meta(date_str):
    """读取今日溯源元数据文件，返回 {事件关键词: [urls]}"""
    meta_file = os.path.join(
        META_DIR.format(date=date_str), 'sources_metadata.json')
    if not os.path.exists(meta_file):
        return {}
    try:
        with open(meta_file, encoding='utf-8') as f:
            data = json.load(f)
        # 返回格式：{event_keyword: [{url, source, verified_date, tag}, ...]}
        return data.get('sources', {})
    except Exception:
        return {}

# ── 合并URL到实体 ─────────────────────────────────
def merge_sources(entity, today_sources):
    """将今日溯源URL合并到实体的sources字段"""
    existing_urls = {s['url'] for s in entity.get('sources', [])}
    new_sources = []
    for kw, urls in today_sources.items():
        # 检查实体的core_keywords是否包含该kw
        if any(kw in ck for ck in entity.get('core_keywords', [])):
            for u in urls:
                if u['url'] not in existing_urls:
                    new_sources.append(u)
    return new_sources

# ── CLI ───────────────────────────────────────────
def run(date_str, update_db=False, candidates_str=''):
    # 加载实体库
    if not os.path.exists(DB_PATH):
        print(f"[WARN] 实体库不存在: {DB_PATH}"); return

    with open(DB_PATH, encoding='utf-8') as f:
        db_list = json.load(f)

    # 加载今日溯源元数据
    today_sources = load_sources_meta(date_str)
    print(f"[INFO] 溯源元数据: {len(today_sources)} 个事件含URL")

    # 候选事件
    candidates = [c.strip() for c in candidates_str.split('|') if c.strip()]
    if not candidates:
        # 无候选 → 返回实体库今日更新后排名
        ranked = []
        for e in db_list:
            s, details = score_event(e, date_str)
            ranked.append({**e, 'score': s, 'score_breakdown': details})
        ranked.sort(key=lambda x: -x['score'])
        for i, e in enumerate(ranked[:20], 1):
            print(f"  #{i:>2} {e['score']:>5.1f}  {e.get('repr',{}).get('title','')[:45]}")
        return

    # 候选评分
    ranked = []
    for i, cand in enumerate(candidates, 1):
        matched, score = match_entity(cand, db_list)
        if matched:
            s, details = score_event(matched, date_str, candidate_rank=i)
            # 合并溯源URL
            new_srcs = merge_sources(matched, today_sources)
            ranked.append({
                'rank': i, 'title': cand[:80],
                'matched': True, 'entity_id': matched.get('entity_id', ''),
                'score': s, 'persistence': matched['persistence'],
                'last_seen': matched['last_seen'],
                'score_breakdown': details,
                'sources': matched.get('sources', []) + new_srcs,
                'recommendation': 'TOP' if not matched.get('persistence', 1) else 'FOLLOW',
                'is_new_candidate': matched['first_seen'] == date_str,
            })
        else:
            # 全新事件（无历史匹配）
            ranked.append({
                'rank': i, 'title': cand[:80],
                'matched': False, 'entity_id': '',
                'score': 60.0,  # 新实体基础分
                'persistence': 0, 'last_seen': date_str,
                'score_breakdown': {'TR': 100, 'PD': 0, 'IM': 80, 'VA': 100, 'DE': 0},
                'sources': today_sources.get(cand[:20], []),
                'recommendation': 'TOP',
                'is_new_candidate': True,
            })

    # 按分数重排
    ranked.sort(key=lambda x: -x['score'])
    for i, e in enumerate(ranked, 1):
        e['final_rank'] = i

    # 打印
    print(f"\n{'最终排名':^6} {'分':^6} {'类型':^8} {'天数':^4}  事件 / 来源URL")
    print("-"*90)
    for e in ranked[:20]:
        rec = {'TOP': '🔴TOP', 'FOLLOW': '🟡续', 'BACKUP': '⚪备'}.get(
            e['recommendation'], '⚪')
        urls = e.get('sources', [])
        url_info = f"  🔗{len(urls)}条来源" if urls else ''
        print(f"  #{e['final_rank']:>2}  {e['score']:>5.1f}  {rec:^8}  {e['persistence'] or '新':>4}  {e['title'][:40]}{url_info}")

    # 保存今日排名
    out = OUT_PATH.format(date=date_str)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            'date': date_str,
            'sources_meta_file': f'{META_DIR.format(date=date_str)}/sources_metadata.json',
            'total': len(ranked),
            'ranked': ranked[:50]
        }, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 今日排名: {out}")

    # 更新实体库（--update-db 时调用）
    if update_db and candidates_str:
        _update_db(date_str, candidates, ranked, db_list, today_sources)

def _update_db(date_str, candidates, ranked, db_list, today_sources):
    """将今日候选事件写入实体库（含URL）"""
    # 构建今日条目索引
    today_entries = {cand[:40]: cand for cand in candidates}

    updated = []
    for e in db_list:
        # 检查该实体今日是否有候选
        matched_cand = next(
            (c for c in candidates
             if any(kw in c for kw in e.get('core_keywords', []))),
            None)
        if matched_cand and date_str not in e['dates']:
            # 新增一天
            e['dates'].append(date_str)
            e['dates'] = sorted(e['dates'], reverse=True)
            e['last_seen'] = date_str
            e['persistence'] = len(set(e['dates']))
            e['appearances'] += 1
            e['markers'].insert(0, '🔴【新】')
            # 合并新来源
            new_srcs = merge_sources(e, today_sources)
            if new_srcs:
                e['sources'] = e.get('sources', []) + new_srcs
        updated.append(e)

    # 新增今日发现的新实体（无历史匹配）
    existing_ids = {e.get('entity_id', '') for e in db_list}
    for e in ranked:
        if not e['matched'] and e['is_new_candidate']:
            title = e['title']
            kws = extract_keywords(title)
            core_kws = sorted(kws, key=lambda w: -len(w))[:4]
            eid = ''.join(core_kws)[:36]
            if eid not in existing_ids:
                new_entity = {
                    'entity_id': eid,
                    'first_seen': date_str,
                    'last_seen': date_str,
                    'persistence': 1,
                    'appearances': 1,
                    'markers': ['🔴【新】'],
                    'titles': [title],
                    'dates': [date_str],
                    'core_keywords': core_kws,
                    'sources': e.get('sources', []),
                    'repr': {'date': date_str, 'title': title, 'rank': e['rank'], 'marker': '🔴【新】'},
                }
                updated.append(new_entity)

    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
    print(f"✅ 实体库已更新: {DB_PATH}（共 {len(updated)} 个实体）")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--date',   default=datetime.now().strftime('%Y-%m-%d'))
    p.add_argument('--candidates', default='')
    p.add_argument('--update-db', action='store_true')
    args = p.parse_args()
    run(args.date, update_db=args.update_db, candidates_str=args.candidates)
