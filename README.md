# 角色服装作品集 · Character Costume Portfolio

Blender 角色服装建模作品集。风格对标《原神》《鸣潮》等大型角色扮演游戏的服装设计水准，
以低模风格化（stylized low-poly）的方式演绎：追的是廓形、层次、配色、配饰的设计质量，
而不是原游戏高模的面数。

A Blender portfolio of character costume modeling. The design bar is set by
Genshin Impact and Wuthering Waves–class RPG outfits, interpreted as stylized
low-poly garments: silhouette, layering, palette and accessories carry the quality.

## 方向

1. **整套服装建模**：一整套角色服装（上装 / 下装 / 外层 / 鞋靴 / 头饰）
2. **服装部件与配饰**：腰带、披风、肩甲、头饰、挂件等单件
3. **服装质检**：拓扑、法线、UV、穿搭穿帮检查，数值实测
4. **二创设计**：在现有服饰语言上的原创再设计（见下）

## 质量标准

- 每件作品先有设计说明：灵感来源、廓形、配色、部件清单，再动手建模
- 服装分层穿搭，关节活动处不穿帮；配色主色不超过 3 个 + 1 个点缀色
- 渲染：Eevee 1024×1024，三点式影棚光，正面 + 线框图，目视检查通过才提交
- 质检数值用脚本实测填写，不编造

## 流程

每 4 小时一件：读 `BACKLOG.md` 取最上面未勾项 → 研究设计 → Blender Python 脚本建模 →
Eevee 渲染 → 目视检查 → 打勾提交推送。定时任务见仓库外的目标文档。

## 版权说明（学习参考）

本仓库所有作品均为**原创设计**，或受游戏服装语言启发的**二创设计**，
仅供学习参考，不用于商业用途；不复制、不提取任何游戏原始模型、贴图或资产。

## 目录

- `scenes/`：场景源文件（.blend + 构建脚本 + 设计说明 .md）
- `renders/`：渲染图（效果图 + 线框图）
- `docs/`：设计指南
- `BACKLOG.md`：待办池
