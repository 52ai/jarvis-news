---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "hotspot-entry-flow"
    PropagateID: "hotspot-entry-flow"
---

# 每日舆情热点数据入库流程（v1.0 · 2026-05-25）

---

## 一、数据流转全貌

```
信息源（5个）
    ↓
Step 1: 读取 rss_feeds.md（量子位/机器之心/新浪科技/HN/Wired）
    ↓
Step 2: 并行抓取当日发布（发布时间=今日）
    ↓
Step 3: 撰写每日报告 → hotspot_YYYYMMDD.md
    ↓
Step 4: 质量自检
    ↓
Step 5: announce（mode: none）
```

---

## 二、数据库文件（005-News根目录）

| 文件 | 用途 |
|------|------|
| `hotspot_event_db_v2.json` | 舆情事件实体库 |
| `hot_score_ranker_v2.py` | 舆情库入库脚本 |
| `media_ranking_2026.json` | 媒体排名库 |

### hotspot_event_db_v2.json 关键字段

| 字段 | 说明 |
|------|------|
| `entity_id` | 事件唯一标识（标题关键词哈希） |
| `first_seen` | 首次出现日期 |
| `last_seen` | 最近出现日期 |
| `persistence` | 持续天数 |
| `appearances` | 累计出现次数 |
| `core_keywords` | 核心关键词 |
| `titles[]` | 历史标题列表 |
| `dates[]` | 所有出现日期 |
| `sources[]` | 来源URL列表 |
| `repr{}` | 代表记录（date/rank/marker） |

---

## 三、Job1 执行步骤（v12）

| Step | 动作 | 输出 |
|------|------|------|
| 1 | 读取 rss_feeds.md | 5个信息源 |
| 2 | extract_content_from_websites + batch_web_search | 当日文章原始数据 |
| 3 | 撰写 hotspot_YYYYMMDD.md | 9段规范报告 |
| 4 | 质量自检 | 禁用语/URL/四维评分 |
| 5 | announce 通知 | mode: none（文件已写入） |

---

## 四、热度分计算

```
热度分 = min(100, persistence × 15) + appearances × 10 + max(0, 50 - rank × 5)
```

| 维度 | 权重 |
|------|------|
| 持续天数 | +15分/天 |
| 出现次数 | +10分/次 |
| 排名加成 | TOP3有额外加分 |

---

## 五、附录TOP20数据来源

| 列表 | 来源 | 排序依据 |
|------|------|---------|
| TOP20舆情 | `hotspot_event_db_v2.json` | 热度分 |
| TOP20媒体 | `tech_media_ranking_2026.json` | `total_score` |

---

## 六、005-News 文件夹规范

### 保留文件清单

| 类型 | 路径 |
|------|------|
| 日报 | `YYYY-MM-DD/hotspot_YYYYMMDD.md` |
| 舆情库 | `hotspot_event_db_v2.json` |
| 舆情入库脚本 | `hot_score_ranker_v2.py` |
| 媒体库 | `media_ranking_2026.json` |
| TOP50 | `TOP50_MEDIA_RANKING.md` |
| 信息源配置 | `rss_feeds.md` |
| 写作规范 | `HOTSPOT_WRITE_SPEC.md` |
| 入库流程 | `HOTSPOT_ENTRY_FLOW.md` |

### 已删除（历史垃圾）

- ❌ `hotspot_today_rank_*.json`（中间排名文件，22个）
- ❌ `sources_metadata.json`（冗余元数据，2个）
- ❌ `hotspot_event_db.json`（v1旧库）
- ❌ `hotspot_events.json`（旧名）
- ❌ `DAILY_ARTICLE_SPEC.md`（旧规范）
- ❌ `HOTSPOT_REPORT_SPEC.md`（旧规范）

**共清理：23个文件，释放572KB**

---

## 七、已知问题

**入库脚本路径问题（待修复）：**
- `hot_score_ranker_v2.py` 写的是 `hotspot_event_db.json`（v1路径）
- 应更新为 `hotspot_event_db_v2.json`
- 当前 Job1 payload 尚未嵌入自动入库调用，需在 Step 3 末尾追加

**待完成：** Job1 payload 中嵌入 `--update-db` 调用，实现每次报告生成后自动更新实体库

---

*整理: jarvis42 - 2026-05-25*
