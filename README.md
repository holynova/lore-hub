# lore-hub · 游戏剧情解析

七个游戏剧情解析站合并后的总站，部署在 https://lore.xiaosang.cc/。

| 分区 | 游戏 | 原仓库 |
| --- | --- | --- |
| `/elden-ring/` | 艾尔登法环（六幕） | holynova/elden-ring-lore |
| `/witcher-3/` | 巫师三（六幕） | holynova/witcher-3-lore |
| `/gta5/` | GTA5（六幕） | holynova/gta5-lore |
| `/rdr2/` | 荒野大镖客2（六幕） | holynova/rdr2-lore |
| `/cyberpunk-2077/` | 赛博朋克2077（六幕） | holynova/cyberpunk-2077-lore |
| `/dark-souls-3/` | 黑暗之魂3（六幕） | holynova/dark-souls-3-lore |
| `/elden-ring-video/` | 艾尔登法环编年史（五章） | holynova/elden-ring-lore-video |

## 合并方式

`scripts/merge-lore.py` 是合并脚本，`.github/workflows/merge.yml`
在 Actions 里跑它：浅克隆 7 个源仓库 main，把每站内容放进对应子路径，
提交回 main。脚本幂等，重跑结果一致。

- 5 份 74MB 苹方字体只留一份在 `/assets/PingFang.ttc`（字体只在合成工程里用，页面用系统字体栈；字体文件不进部署，见 `.assetsignore`）。
- 各站页脚系列导航的旧域名链接改指新子路径，并加了回总站的「全部游戏」链接。
- 旧的 7 个子域名由 Worker 做 301 跳转到对应分区（路径保留），旧 Worker 脚本保留未删。
- 各站的合成工程（`compositions/`、`composition.html`、生成脚本）原样保留在分区内，不进部署。

## 部署

```sh
npx wrangler deploy
```

Worker 名 `lore-hub`，路由 `lore.xiaosang.cc/*`（另有 7 条旧域名路由指到同一 Worker 做跳转）。视频走 Worker 做字节范围请求（见 `worker/media.mjs`），测试：`npm run test:media`。

## 已知问题

- `#42` 赛博朋克2077 第四幕配图错误（人物与图不符），待定夺，合并时保持原样。
- `#43` 法环编年史的视频封面图 `snapshots/frame-00-at-5s.png` 在部署中被排除，线上 404——合并前已存在，非本次引入。
