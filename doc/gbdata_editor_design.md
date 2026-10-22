# GBData Editor — 设计文档

## 概述

GBData Editor 是面向 GBox 游戏引擎的可视化数据编辑器。以 `.gbdata` 项目文件为入口，本地 Web 应用提供卡片式数据浏览和编辑体验。

核心设计理念：**统一覆盖链、Schema 驱动、组件三态**。

架构原则：**简洁高效清晰可扩展，高内聚低耦合**。
- 每个文件只做一件事，职责边界清晰
- 核心逻辑（core）不依赖 UI，UI 组件（widgets）不依赖页面视图（views）
- 新增功能只需在对应目录加文件，不改已有代码
- 不做过度抽象，不写用不到的代码

视觉标准：**专业、现代、简洁美观**。
- 整体风格对标 VS Code / Figma 等专业工具的质感，暗色主题为主
- 圆角、阴影、过渡动画等细节到位，交互有反馈（hover、active、focus 状态完整）
- 排版留白舒适，信息密度适中，不拥挤不空旷
- 统一的设计语言：一套 CSS 变量控制色板、间距、圆角、字号、阴影，全局一致
- 卡片、面板、弹窗都要有精致的边框和层次感
- 不使用浏览器原生控件（select、checkbox 等），所有控件自绘以保持风格统一

---

## 1. 类型系统 — 统一覆盖模型

整个类型系统只有一个核心概念：**类型定义**。所有类型定义共享同一个结构，通过 `base` 指向父类型，子类型覆盖父类型的任意属性。

```
    int ─── range_int ─── hp_value ─── [字段 hp] ─── [分类覆盖]
    (内置)   (覆盖ui)    (覆盖params)  (覆盖default)  (覆盖default)

    array ── id_num ──── [字段 drops 使用 array[id_num]]
    (内置)   (覆盖template,ui,default)
```

### 1.1 类型定义的统一结构

每个类型定义可以包含以下属性，子类型只需写要覆盖的部分：

| 属性 | 说明 |
|------|------|
| `base` | 父类型（覆盖链的上一级） |
| `label` | 显示名称 |
| `ui` | UI 组件 key（决定渲染方式） |
| `params` | UI 组件参数（deep merge：子覆盖父的同名 key，父的其他 key 保留） |
| `default` | 默认值 |
| `template` | 结构体模板（仅 base 链根为 `array` 时有效） |

**解析规则：** 沿 `base` 链向上递归，逐层合并。子属性覆盖父属性，`params` 做 deep merge，其他属性做直接替换。

### 1.2 基础类型（根类型，4个，内置）

| 类型 | 说明 | 默认 ui | 默认值 |
|------|------|--------|--------|
| `int` | 整数 | `input` | 0 |
| `float` | 浮点数 | `input` | 0.0 |
| `string` | 字符串 | `input` | "" |
| `array` | 列表 | `list` | [] |

基础类型是覆盖链的根，没有 `base`。这 4 种也是 **原始编辑模式** 下所有组件回退的编辑形式。

**array 子类型语法：**

- `array` — 无约束数组
- `array[int]` / `array[float]` / `array[string]` — 元素约束为基础类型
- `array[结构体名]` — 元素约束为指定结构体（如 `array[id_num]`）
- `array[array]` — **禁止**，不支持嵌套

### 1.3 系统内置字段

系统预置 3 个全局字段，新建项目和新建分类时自动包含：

| 字段 key | 类型 | 说明 | 特殊行为 |
|---------|------|------|---------|
| `_id` | int | 全局唯一 ID | 自动生成，只读，不可删除 |
| `name` | string | 名称 | 默认 card_slot: title |
| `description` | string (textarea) | 描述 | 可选 |

- `_id` 是系统字段，不出现在 fields 配置中，由编辑器自动管理
- `name` 和 `description` 是默认字段，新建分类时自动包含，用户可以在分类中移除
- 新建项目的 `.gbdata` 的 `fields` 中预置 `name` 和 `description`
- 所有实体数据（测试和正式）都是分类子目录中的 JSON 文件，系统不硬编码任何假想数据

### 1.4 UI 组件（渲染层，与类型分离）

UI 组件是独立的渲染代码，每个组件声明自己可以绑定哪些基础类型。类型定义通过 `ui` 字段引用组件。

**内置 UI 组件：**

| 组件 key | 可绑定基础类型 | 渲染方式 | 默认参数 |
|---------|--------------|---------|---------|
| `input` | int, float, string | 单行文本输入 | `maxLength` |
| `textarea` | string | 多行文本框 | `rows` |
| `range` | int, float | 滑块 | `min`, `max`, `step`, `suffix` |
| `enum` | int, string | 下拉选项 | `options: {value: label}` |
| `toggle` | int | 开关（0/1） | — |
| `color` | int | 颜色选择器 | `format: "argb"\|"rgb"` |
| `tags` | array | 标签多选 | `options: [string]` |
| `image` | string | 图片预览 + 文件选择 | `accept` |
| `audio` | string | 音频播放器 + 文件选择 | `accept` |
| `file` | string | 文件路径选择 | `accept` |
| `2dani` | string | 2dani.bmp Canvas 预览 | `editable_center`, `show_footprint` |
| `isometric` | array | 菱形占地网格 | `max_x`, `max_y` |
| `ref` | int | 引用选择器（下拉+跳转） | `category` |
| `date` | string | 日期选择器 | — |
| `list` | array | 列表编辑器（增删元素） | — |
| `struct` | array | 结构体容器（按 template 逐位渲染子组件） | — |
| `json` | int, float, string, array | 原始 JSON 编辑器 | — |

> 类型的 `ui` 必须与其基础类型链的根兼容。编辑器在创建/编辑类型时自动过滤可选组件。
> 未指定 `ui` 时使用基础类型的默认 ui。未知组件回退为 `json`。

### 1.5 用户自定义类型（全部在 `types` 中）

所有用户定义的类型 — 无论是 UI 特化类型、结构体、还是具体业务类型 — 都写在 `.gbdata` 的 `types` 字典中，结构完全一致：

```json
"types": {

    // ── UI 特化类型（覆盖 ui 和默认 params）──

    "range_int":    { "base": "int",    "label": "范围整数", "ui": "range", "params": { "min": 0, "max": 100 } },
    "range_float":  { "base": "float",  "label": "范围小数", "ui": "range", "params": { "min": 0, "max": 1, "step": 0.01 } },
    "enum_int":     { "base": "int",    "label": "选项(整型)", "ui": "enum" },
    "enum_string":  { "base": "string", "label": "选项(文本)", "ui": "enum" },
    "toggle":       { "base": "int",    "label": "开关",     "ui": "toggle", "default": 0 },
    "color_value":  { "base": "int",    "label": "颜色",     "ui": "color", "params": { "format": "argb" } },
    "image_path":   { "base": "string", "label": "图片",     "ui": "image", "params": { "accept": ".png,.jpg,.jpeg" } },
    "audio_path":   { "base": "string", "label": "音频",     "ui": "audio", "params": { "accept": ".mp3,.wav,.ogg" } },
    "ani_2d":       { "base": "string", "label": "2D动画",   "ui": "2dani" },
    "entity_ref":   { "base": "int",    "label": "实体引用",  "ui": "ref", "default": 0 },
    "date_value":   { "base": "string", "label": "日期",     "ui": "date" },
    "tag_list":     { "base": "array",  "label": "标签列表",  "ui": "tags", "params": { "options": [] } },

    // ── 结构体（base=array + template，默认 ui=struct 容器）──

    "id_num": {
        "base": "array",
        "label": "ID+数量",
        "ui": "struct",
        "template": [
            { "key": "id",  "label": "引用", "type": "entity_ref", "default": 0 },
            { "key": "num", "label": "数量", "type": "int",        "default": 0 }
        ],
        "default": [0, 0]
    },
    "reward": {
        "base": "array",
        "label": "奖励",
        "ui": "struct",
        "template": [
            { "key": "item",  "label": "物品", "type": "entity_ref", "default": 0 },
            { "key": "count", "label": "数量", "type": "int",        "default": 1 },
            { "key": "prob",  "label": "概率", "type": "float",      "default": 1.0 }
        ],
        "default": [0, 1, 1.0]
    },

    // ── 具体业务类型（覆盖 params / default）──

    "hp_value":     { "base": "range_int",   "label": "生命值", "params": { "min": 0, "max": 99999 } },
    "atk_value":    { "base": "int",         "label": "攻击力", "params": { "min": 0 } },
    "speed_val":    { "base": "range_float",  "label": "速度值", "params": { "min": 0, "max": 20, "step": 0.1 } },
    "char_class":   { "base": "enum_string", "label": "职业",   "params": { "options": { "warrior": "战士", "mage": "法师", "rogue": "刺客" } } },
    "portrait":     { "base": "image_path",  "label": "头像" },
    "ani_file":     { "base": "ani_2d",      "label": "动画文件" },
    "quality_color":{ "base": "color_value",  "label": "品质色" },
    "game_tags":    { "base": "tag_list",    "label": "游戏标签", "params": { "options": ["boss", "npc", "rare", "monster", "melee"] } },
    "price_val":    { "base": "int",         "label": "价格",   "params": { "min": 0 } },
    "desc_text":    { "base": "string",      "label": "描述",   "ui": "textarea", "params": { "rows": 3 } },
    "footprint":    { "base": "array",       "label": "占地",   "ui": "isometric", "params": { "max_x": 8, "max_y": 8 } }
}
```

**覆盖链示例 — 解析 `hp_value`：**

```
hp_value                         → range_int                    → int (根)
label: "生命值"                    label: "范围整数"                label: —
params: {min:0, max:99999}        params: {min:0, max:100}       params: —
                                  ui: "range"                    ui: "input"

合并结果：base_type=int, ui=range, params={min:0, max:99999}, label="生命值"
```

**覆盖链示例 — 解析 `id_num`：**

```
id_num                           → array (根)
label: "ID+数量"                   label: —
ui: "struct"                      ui: "list"
template: [{...}, {...}]          template: —
default: [0, 0]                   default: []

合并结果：base_type=array, ui=struct, template=[...], default=[0, 0], label="ID+数量"
```

### 1.6 结构体的特殊规则

结构体是 `base` 链根为 `array` 且带有 `template` 的类型。额外约束：

- 名字全局唯一，不能与基础类型名、其他类型 key、UI 组件 key 冲突
- `template` 至少 **2 项**
- 每项必须有 `key`、`label`、`type`、`default`
- 每项的 `type` 不能是 `array` 或其他结构体名（结构体不嵌套）
- 结构体可以指定专属 UI 组件（覆盖默认的 `struct` 容器），只要该组件兼容 `array` 基础类型
- `default` 由 template 各项的 `default` 组合而成

**结构体在 JSON 中存储为普通数组：**

```json
[2001, 3]         // id_num: id=2001, num=3
[2001, 1, 0.5]    // reward: item=2001, count=1, prob=0.5
```

### 1.7 类型系统的统一性

整个系统只有 **一种机制**：

| 你想做什么 | 怎么做 |
|-----------|--------|
| 给 int 加滑块 UI | 新类型 `base: "int", ui: "range"` |
| 给滑块加具体范围 | 新类型 `base: "range_int", params: {max: 99999}` |
| 定义结构体 | 新类型 `base: "array", template: [...]` |
| 给结构体定制 UI | 新类型 `base: "id_num", ui: "my_custom_widget"` |
| 字段覆盖默认值 | 字段定义 `type: "hp_value", default: 500` |
| 分类覆盖默认值 | 分类 fields `{"key": "hp", "default": 5000}` |

都是同一个 `{base, ...overrides}` 模式。没有"数据类型""结构体""字段类型"的人为分类 — 它们只是覆盖链上不同深度的节点。

---

## 2. 字段、分类与实体

### 2.1 全局字段

字段 = 类型的最后一层覆盖，附加展示和校验元信息：

```json
"fields": {
    "name":      { "type": "string",       "label": "名称",   "required": true, "card_slot": "title" },
    "class":     { "type": "char_class",   "label": "职业",   "card_slot": "subtitle" },
    "level":     { "type": "int",          "label": "等级",   "default": 1, "card_slot": "info" },
    "hp":        { "type": "hp_value",     "label": "生命值",  "default": 100, "card_slot": "info" },
    "atk":       { "type": "atk_value",    "label": "攻击力" },
    "speed":     { "type": "speed_val",    "label": "速度" },
    "portrait":  { "type": "portrait",     "label": "头像",   "card_slot": "thumbnail" },
    "ani":       { "type": "ani_file",     "label": "动画" },
    "tags":      { "type": "game_tags",    "label": "标签",   "card_slot": "badges" },
    "drops":     { "type": "array[id_num]","label": "掉落" },
    "price":     { "type": "price_val",    "label": "价格",   "card_slot": "info" },
    "icon":      { "type": "portrait",     "label": "图标",   "card_slot": "thumbnail" },
    "desc":      { "type": "desc_text",    "label": "描述" },
    "color":     { "type": "quality_color", "label": "品质色", "card_slot": "accent" },
    "footprint": { "type": "footprint",    "label": "占地" }
}
```

| 属性 | 类型 | 必选 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 引用的类型 key（用户定义类型或基础类型名） |
| `label` | string | 是 | 显示名称（覆盖类型的 label） |
| `default` | any | 否 | 默认值（覆盖类型的 default） |
| `required` | bool | 否 | 是否必填 |
| `description` | string | 否 | 字段说明 |
| `card_slot` | string | 否 | 卡片槽位（见 2.3） |

> 字段也是覆盖链的一环。`label`、`default` 都会覆盖所引用类型的对应值。

### 2.2 分类

```json
"categories": {
    "characters": {
        "label": "角色",
        "icon": "sword",
        "fields": [
            "name", "class", "level",
            { "key": "hp", "default": 100 },
            "atk", "speed", "portrait", "ani", "drops", "tags"
        ],
        "defaultSort": "name"
    },
    "items": {
        "label": "道具",
        "icon": "backpack",
        "fields": ["name", "price", "icon", "desc", "tags", "color"],
        "defaultSort": "name"
    },
    "buildings": {
        "label": "建筑",
        "icon": "house",
        "fields": ["name", "ani", "footprint", "tags"],
        "defaultSort": "name"
    }
}
```

| 属性 | 类型 | 必选 | 说明 |
|------|------|------|------|
| `label` | string | 是 | 显示名称 |
| `icon` | string | 否 | 图标 |
| `fields` | array | 是 | 字段列表。字符串或 `{"key", "default"}` 覆盖默认值 |
| `defaultSort` | string | 否 | 默认排序字段 |

分类的字段覆盖是覆盖链的最末端：

```
int → range_int → hp_value → [字段 hp, default:100] → [角色分类, default:100]
                                                      → [Boss分类, default:5000]
```

### 2.3 卡片槽位系统

卡片布局采用 **槽位（slot）系统**。字段通过 `card_slot` 声明显示在哪个槽位。

```
┌─────────────────────────┐
│                         │
│      [thumbnail]        │  ← 主图区，最多1个字段
│                         │
├─────────────────────────┤
│ [title]                 │  ← 标题，最多1个字段
│ [subtitle]              │  ← 副标题，最多1个字段
├─────────────────────────┤
│ [info]  [info]  [info]  │  ← 信息行，可多个字段，自动排列
├─────────────────────────┤
│ [badge] [badge] [badge] │  ← 底部标签，可多个字段
└─────────────────────────┘
  ▌← [accent] 左边框色条
```

| 槽位 | 容量 | 渲染方式 |
|------|------|---------|
| `thumbnail` | 1 | 图片/2dani/Canvas 预览 |
| `title` | 1 | 大字粗体 |
| `subtitle` | 1 | 小字灰色 |
| `info` | 多个 | label:value 键值对，自动排列换行 |
| `badges` | 多个 | 小标签/药丸 |
| `accent` | 1 | 左边框颜色条 |

- 未使用的槽位自动折叠
- 没有 `card_slot` 的字段只在属性面板显示
- 同一槽位多个字段按分类 `fields` 顺序排列
- 未配置时默认：`title` = 第一个 string 字段，`thumbnail` = 第一个 image/2dani 字段

### 2.4 实体

每个实体是独立 JSON 文件：

```json
{
    "_id": 7284619482734592,
    "name": "哥布林",
    "hp": 50,
    "atk": 8,
    "speed": 4.0,
    "portrait": "goblin_portrait.png",
    "drops": [[2001, 3], [2002, 1]],
    "tags": ["monster", "melee"]
}
```

- `_id` 全局唯一 int64，创建时自动生成，不可修改
- 缺少的字段沿覆盖链向上取默认值：分类级 → 字段级 → 类型级 → 基础类型级

**文件命名规则：**

文件名格式为 `{id}_{name}.json`，方便人类和 AI 快速定位：

```
characters/
├── 7284619482734592_goblin.json
├── 7284619482831104_knight.json
└── 7284619482945280_dragon.json
```

- `{id}` 为实体的 `_id` 值
- `{name}` 取自实体的 `title` 槽位字段（通常是 name 字段），特殊字符清理（空格→下划线，去掉 `/\:*?"<>|` 等）
- 如果 name 为空或该分类没有 title 字段，则使用 `{id}.json` 兜底
- **保存时如果 name 变了，自动重命名文件**（因为引用关系基于 `_id`，重命名不影响任何引用）
- `.gbdata` 只存结构定义（types、fields、categories），**不存任何实体数据**

---

## 3. UI 组件三态

所有 UI 组件统一支持三种交互模式：

```
┌──────────────────────────────────────────────────┐
│                                                  │
│  只读模式 ←→ 快捷编辑模式 ←→ 原始编辑模式          │
│  (readonly)   (quick-edit)    (raw-edit)         │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 3.1 三种模式

| 模式 | 说明 | 触发方式 |
|------|------|---------|
| **只读模式** | 仅显示值，不可交互 | 卡片上的字段显示 |
| **快捷编辑模式** | 使用该数据类型绑定的 UI 组件交互 | 属性面板中的默认编辑状态 |
| **原始编辑模式** | 回退为基础类型的文本输入框 | 点击组件右侧的 `[⊞]` 按钮切换 |

### 3.2 组件右侧切换按钮

属性面板中，每个字段组件的最右侧有一个小方块按钮 `[⊞]`：

```
┌─────────────────────────────────────────┐
│ 生命值  [████████░░░░░░] 50/99999  [⊞] │  ← 快捷编辑（range 滑块）
└─────────────────────────────────────────┘
                    点击 [⊞]
                      ↓
┌─────────────────────────────────────────┐
│ 生命值  [ 50                       ] [⊞]│  ← 原始编辑（int 文本框）
└─────────────────────────────────────────┘
```

- 快捷模式 → 原始模式：方便输入精确值，或处理 UI 组件无法表达的极端情况
- 原始模式 → 快捷模式：恢复友好交互
- 只读模式不显示此按钮

### 3.3 各基础类型的原始编辑形式

| 基础类型 | 原始编辑 UI |
|---------|-----------|
| `int` | 单行文本框，支持十进制/十六进制（0x）/二进制（0b） |
| `float` | 单行文本框 |
| `string` | 单行文本框 |
| `array` | JSON 文本编辑（结构体类型的字段在原始模式下也是编辑数组文本） |

### 3.4 组件实现协议

每个 UI 组件实现以下接口：

```typescript
interface UIComponent {
    // 声明可绑定的基础类型
    base_types: string[];

    // 三种渲染模式
    renderReadonly(value, params): VNode;     // 卡片上的只读显示
    renderQuickEdit(value, params): VNode;    // 属性面板的快捷编辑
    renderRawEdit(value, params): VNode;      // 原始编辑（通常不需要自定义，框架提供默认实现）

    // 可选
    validate?(value, params): string | null;  // 校验，返回错误信息或 null
    parseRaw?(raw: string): any;              // 从原始文本解析值
    formatRaw?(value): string;                // 值格式化为原始文本
}
```

---

## 4. 编辑器 UI 设计

### 4.1 可停靠面板系统

编辑器采用可停靠面板（Dockable Panel）架构，类似 VS Code / JetBrains 的布局体验。使用 **Dockview** 库（零依赖、支持 React、MIT 协议）实现。

**面板能力：**
- 面板可拖拽到上下左右任意位置停靠
- 两个面板之间的分割线可拖动调整大小
- 面板可拖到另一个面板上合并为 Tab 标签组
- 面板可浮动（脱离主布局成为独立窗口）
- 布局自动保存到 localStorage，重启后恢复

**默认布局（类似 VS Code）：**

所有面板都可自由拖拽重排，以下仅为初始默认布局：

```
┌──────────────────────────────────────────────────────────────┐
│  工具栏: [项目名]  [类型管理] [字段管理]  [⟲ ⟳] [历史] [设置] │
├──────────┬────────────────────────┬──────────────────────────┤
│          │                        │                          │
│ 分类列表  │   卡片网格 (主视图)     │   属性面板                │
│          │                        │   (选中实体的字段编辑)     │
│ 角色 (3) │  ┌──────┐ ┌──────┐   │                          │
│ 道具 (2) │  │ Card │ │ Card │   │  _id: ...                │
│ 建筑 (2) │  │      │ │      │   │  name: [...]          [⊞]│
│          │  └──────┘ └──────┘   │  description: [...]   [⊞]│
│          │  ┌──────┐  [+]       │  ...                      │
│          │  │ Card │            │                          │
│          │  └──────┘            │  [保存]  [重置]           │
├──────────┴────────────────────────┴──────────────────────────┤
│ [AI 对话] [变更审查] [操作历史]                 (底部 Tab 组)  │
│  AI 聊天面板 / 变更审查面板 / 操作历史面板                      │
├──────────────────────────────────────────────────────────────┤
│  状态栏                                                      │
└──────────────────────────────────────────────────────────────┘
```

> 每个区域都可以包含多个 Tab。例如用户可以把"类型管理"拖到主视图区域和"卡片网格"并列为 Tab，或者把"AI 对话"拖到右侧和"属性面板"并列。

**面板列表：**

| 面板 | 默认位置 | 说明 |
|------|---------|------|
| 分类导航 | 左侧 | 分类列表 + 搜索 |
| 卡片网格 | 中间（主区域） | 当前分类的实体卡片 |
| 属性面板 | 右侧 | 选中实体的字段编辑 |
| AI 对话 | 底部 Tab | AI 聊天交互 |
| 变更审查 | 底部 Tab | AI 产生的变更集审查 |
| 操作历史 | 底部 Tab | Undo/Redo 历史列表 |
| 类型管理 | 弹窗 / 可停靠 | types CRUD |
| 字段管理 | 弹窗 / 可停靠 | fields CRUD |
| 分类管理 | 弹窗 / 可停靠 | categories CRUD |
| 设置 | 弹窗 / 可停靠 | AI 配置、编辑器偏好 |

> 用户可以随意拖拽重排这些面板。比如把"操作历史"拖到右侧和"属性面板"并列为 Tab，或者把"AI 对话"拖到独立浮动窗口。

### 4.2 管理界面

**类型管理（统一的 types 管理）：**

所有类型在同一个列表中管理，通过 base 链直观展现覆盖关系：

```
┌──────────────────────────────────────────────────────────────────┐
│  类型管理                                              [+ 新建]  │
├──────────────┬──────────┬────────┬──────────────────────────────┤
│ key          │ base     │ ui     │ 说明                         │
├──────────────┼──────────┼────────┼──────────────────────────────┤
│ range_int    │ int      │ range  │ min:0 max:100                │
│ range_float  │ float    │ range  │ min:0 max:1 step:0.01        │
│ enum_string  │ string   │ enum   │                              │
│ entity_ref   │ int      │ ref    │                              │
│ image_path   │ string   │ image  │ accept:.png,.jpg             │
│ ─ portrait   │ image_path│       │ label:头像                    │
│ id_num       │ array    │ struct │ template:[entity_ref, int]   │
│ hp_value     │ range_int│        │ min:0 max:99999              │
│ char_class   │ enum_string│      │ options:warrior,mage,rogue   │
└──────────────┴──────────┴────────┴──────────────────────────────┘
```

新建流程：填 key/名称 → 选 base（基础类型或已有类型） → 自动过滤可用 UI 组件 → 选组件（可选，不选则继承 base 的 ui） → 填参数 → 确定。

> 结构体就是 base=array + 添加 template 的类型，在同一个列表中管理，不需要独立的结构体管理界面。

**字段管理：**

```
┌───────────────────────────────────────────────────────────┐
│  全局字段                                        [+ 新建] │
├──────────┬──────────┬──────────────┬────────┬────────────┤
│ key      │ 名称     │ 类型          │ 卡片槽位│ 被引用次数  │
├──────────┼──────────┼──────────────┼────────┼────────────┤
│ name     │ 名称     │ string       │ title  │ 3          │
│ hp       │ 生命值   │ hp_value     │ info   │ 2          │
│ portrait │ 头像     │ portrait     │thumbnail│ 1          │
│ tags     │ 标签     │ game_tags    │ badges │ 3          │
│ drops    │ 掉落     │ array[id_num]│ —      │ 1          │
└──────────┴──────────┴──────────────┴────────┴────────────┘
```

### 4.3 交互流程

**打开项目：**
1. 双击 `.gbdata` 文件（或命令行指定路径）
2. 编辑器启动，读取 `.gbdata`，扫描各分类文件夹
3. 左侧显示所有分类，默认选中第一个
4. 中间显示该分类下所有实体卡片

**编辑实体：**
1. 点击卡片 → 右侧属性面板显示所有字段（快捷编辑模式）
2. 修改字段值 → 仅修改内存，卡片实时更新预览，标记为"未保存"（卡片角落小圆点）
3. 点击 `[⊞]` 切换单个字段到原始编辑模式
4. 点击保存 → 才真正写入 JSON 文件
5. 点击重置 → 丢弃内存中的修改，从文件重新读取

**新建实体：**
1. 卡片区点击 `[+]` 卡片
2. 填写文件名
3. 在内存中创建临时实体（自动生成 `_id`，字段填充默认值），卡片标记为"新建未保存"
4. 自动选中并打开编辑
5. 点击保存 → 才真正创建 JSON 文件
6. 点击取消 → 丢弃，文件系统无变化

**删除实体：**
1. 选中实体，点击删除
2. 卡片标记为"待删除"（灰显/划线），内存中标记
3. 点击保存 → 才真正删除文件
4. 点击撤销 → 恢复，文件未动

> **所有对文件系统的操作都收拢到"保存"这一个动作上**。改到一半不满意可以随时放弃，误操作有缓冲。

**新建分类：**
1. 工具栏 `[+ 新建分类]`（或左侧栏底部 `[+]`）
2. 填写 key、名称、图标
3. 从字段池勾选字段，拖拽排序
4. 确认 → 更新 `.gbdata`，创建文件夹

**外部修改自动刷新：**
1. 文件监听检测到实体 JSON 变更 → WebSocket 推送
2. 非编辑中的实体：静默刷新卡片
3. 正在编辑且有未保存修改：显示「文件已被外部修改，[重新加载] [保留我的]」
4. `.gbdata` 变更 → 重新加载项目配置

### 4.4 缓存与崩溃恢复

编辑器在项目目录下维护 `.gbdata.cache` 文件，实时记录所有未保存的变更：

```json
{
    "pending": {
        "characters/goblin.json": { "action": "modify", "data": { "_id": 123, "hp": 999 } },
        "characters/new_elf.json": { "action": "create", "data": { "_id": 456, "name": "精灵" } },
        "items/old_sword.json":   { "action": "delete" }
    },
    "history": [ ... ],
    "history_cursor": 4,
    "timestamp": "2026-03-31T17:00:00Z"
}
```

- 每次编辑操作实时写入缓存
- 编辑器启动时检测到缓存 → 提示「上次有未保存的修改，[恢复] [丢弃]」
- 保存成功 → 清除对应缓存条目
- 全部保存完 → 删除缓存文件
- `.gbdata.cache` 加入 `.gitignore`

### 4.5 Undo/Redo 与操作历史

编辑器维护一个操作历史栈（最多 50 步），支持任意跳转：

**工具栏历史按钮：**

```
┌─────────────────────────────────────┐
│  操作历史                     [清空] │
├─────────────────────────────────────┤
│  ✓ 修改 goblin.hp: 50 → 999       │
│  ✓ 修改 goblin.name: 哥布林 → 精英  │
│  ✓ 新建 elf_archer                 │
│  ✓ 删除 old_sword                  │
│  ● 修改 knight.atk: 20 → 35       │  ← 当前位置
│  ○ (redo 区域)                      │
└─────────────────────────────────────┘
```

**数据结构：**

```javascript
{
    history: [
        {
            label: "修改 goblin.hp: 50 → 999",
            undo: { entity: "characters/goblin.json", field: "hp", value: 50 },
            redo: { entity: "characters/goblin.json", field: "hp", value: 999 }
        },
        // ...
    ],
    cursor: 4,     // 当前位置
    maxSize: 50    // 最大记录数
}
```

**操作方式：**

| 操作 | 快捷键 | 说明 |
|------|--------|------|
| Undo | Ctrl+Z | cursor 后退一步，执行该步的 undo |
| Redo | Ctrl+Shift+Z | 执行当前步的 redo，cursor 前进 |
| 跳转 | 点击历史列表某步 | 从当前 cursor 连续执行 undo 或 redo 到目标位置 |
| 新操作 | — | cursor 之后的记录全部截断（丢弃 redo 分支） |

**操作历史也写入 `.gbdata.cache`**，崩溃恢复后历史记录仍然可用。

### 4.6 历史记录的防抖策略

不同 UI 组件在不同时机产生历史记录，原则：**用户的一次"意图"产生一条记录**。

| 组件类型 | 记录触发时机 | 说明 |
|---------|------------|------|
| 文本输入 input | 回车 / 失去焦点 | 编辑过程不记录，确认后记录 `旧值 → 新值` |
| 数字输入 | 回车 / 失去焦点 | 同上 |
| 滑块 range | mouseup / touchend | 拖动过程不记录，松手时记录 `拖动前值 → 松手值` |
| 下拉 enum | 选中变更 | 选中即记录 |
| 开关 toggle | 点击 | 点击即记录 |
| 颜色选择器 | 关闭选择器 | 拾色过程不记录，关闭时记录 |
| 标签 tags | 添加/删除一个标签 | 每次增删为一条记录 |
| 日期 date | 选中变更 | 选中即记录 |
| 结构体 struct | 内部子组件各自按规则触发 | 每个子字段独立产生记录 |
| 列表 array | 添加/删除元素、元素内编辑 | 增删各一条，元素内编辑按子组件规则 |

> 滑块从 50 拖到 999，历史中只有一条 `50 → 999`，不会产生中间值的垃圾记录。

---

## 5. .gbdata 文件

`.gbdata` 只存结构定义：`types`、`fields`、`categories`。不存任何实体数据。

### 5.1 新建项目的初始状态

```json
{
    "version": 1,
    "name": "我的游戏数据",
    "types": {},
    "fields": {
        "name":        { "type": "string", "label": "名称",  "required": true, "card_slot": "title" },
        "description": { "type": "string", "label": "描述",  "ui": "textarea" }
    },
    "categories": {}
}
```

- 新项目只有 `name` 和 `description` 两个默认字段
- `_id` 是系统字段，不出现在 fields 中
- types、categories 为空，由用户通过编辑器添加

### 5.2 新建分类的默认行为

新建分类时，默认包含 `name` 和 `description` 字段：

```json
"categories": {
    "characters": {
        "label": "角色",
        "icon": "sword",
        "fields": ["name", "description"],
        "defaultSort": "name"
    }
}
```

用户可以在分类编辑器中添加更多字段、移除 description、调整顺序。

### 5.3 经过用户配置后的示例

随着用户添加类型、字段和分类，`.gbdata` 逐渐丰富：

```json
{
    "version": 1,
    "name": "我的游戏数据",

    "types": {
        "range_int":     { "base": "int",    "label": "范围整数",   "ui": "range", "params": { "min": 0, "max": 100 } },
        "enum_string":   { "base": "string", "label": "选项(文本)", "ui": "enum" },
        "image_path":    { "base": "string", "label": "图片",      "ui": "image", "params": { "accept": ".png,.jpg" } },
        "entity_ref":    { "base": "int",    "label": "实体引用",   "ui": "ref", "default": 0 },
        "hp_value":      { "base": "range_int", "label": "生命值",  "params": { "min": 0, "max": 99999 } },
        "char_class":    { "base": "enum_string", "label": "职业",  "params": { "options": { "warrior": "战士", "mage": "法师" } } },
        "id_num":        { "base": "array",  "label": "ID+数量",   "ui": "struct", "template": [
            { "key": "id",  "label": "引用", "type": "entity_ref", "default": 0 },
            { "key": "num", "label": "数量", "type": "int",        "default": 0 }
        ], "default": [0, 0] }
    },

    "fields": {
        "name":        { "type": "string",     "label": "名称",   "required": true, "card_slot": "title" },
        "description": { "type": "string",     "label": "描述",   "ui": "textarea" },
        "hp":          { "type": "hp_value",   "label": "生命值", "default": 100, "card_slot": "info" },
        "class":       { "type": "char_class", "label": "职业",   "card_slot": "subtitle" },
        "portrait":    { "type": "image_path", "label": "头像",   "card_slot": "thumbnail" },
        "drops":       { "type": "array[id_num]", "label": "掉落" }
    },

    "categories": {
        "characters": {
            "label": "角色",
            "icon": "sword",
            "fields": ["name", "class", { "key": "hp", "default": 100 }, "portrait", "drops", "description"],
            "defaultSort": "name"
        },
        "items": {
            "label": "道具",
            "icon": "backpack",
            "fields": ["name", "description"],
            "defaultSort": "name"
        }
    }
}
```

### 5.4 文件系统结构

```
my_game/
├── my_game.gbdata                          ← 只有结构定义
├── .gbdata.cache                           ← 未保存变更缓存（.gitignore）
├── characters/                             ← 实体数据（由编辑器/AI 创建）
│   ├── 7284619482734592_goblin.json
│   └── 7284619482831104_knight.json
└── items/
    └── 7284619483012096_sword.json
```

所有实体数据（无论测试还是正式）都是分类子目录下的 JSON 文件。系统不硬编码任何假想数据。

---

## 6. 技术架构

### 6.1 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| 前端框架 | **React 18 + TypeScript** | 类型安全，生态丰富 |
| 构建工具 | **Vite** | 极快的 HMR，开箱即用 |
| 面板系统 | **Dockview** (`dockview-react`) | 零依赖核心，拖拽停靠/Tab/浮动/布局序列化 |
| 状态管理 | **Zustand** | 轻量，适合中等复杂度 |
| 样式 | **CSS Modules + CSS 变量** | 组件隔离 + 全局主题 |
| 后端 | **Python FastAPI** | REST API + WebSocket + 文件监听 |
| 文件监听 | **watchfiles** | 异步原生，跨平台 |
| AI 通信 | **各 Provider 官方 SDK / OpenAI 兼容格式** | 后端代理转发 |

### 6.2 架构图

```
.gbdata 文件 (双击启动)
        │
        ▼
┌───────────────────┐       HTTP/WS       ┌───────────────────────┐
│  Python 后端       │ ◄────────────────► │  React 前端 (Vite)      │
│  (FastAPI)         │                     │                        │
│  • REST API        │                     │  ┌─── Dockview ──────┐ │
│  • 文件读写         │   WebSocket推送     │  │ 分类 │ 卡片 │ 属性  │ │
│  • Schema校验      │ ─────────────────► │  ├──────────────────┤ │
│  • 文件监听         │   文件变更事件       │  │ AI对话│变更审查│历史│ │
│  • AI代理转发       │                     │  └──────────────────┘ │
└───────────────────┘                     └───────────────────────┘
```

### 6.3 后端 API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/project` | 返回 .gbdata 完整内容 |
| PUT | `/api/project` | 更新 .gbdata |
| GET | `/api/categories/{key}/entities` | 列出分类下所有实体 |
| GET | `/api/categories/{key}/entities/{id}` | 获取单个实体 |
| PUT | `/api/categories/{key}/entities/{id}` | 保存实体（含校验） |
| POST | `/api/categories/{key}/entities` | 新建实体 |
| DELETE | `/api/categories/{key}/entities/{id}` | 删除实体 |
| GET | `/api/files/{path}` | 读取资源文件（图片、2dani 等） |
| POST | `/api/ai/chat` | AI 对话（流式响应，SSE） |
| GET | `/api/ai/providers` | 获取可用的 AI Provider 列表 |
| WS | `/ws` | 文件变更通知 |

### 6.4 WebSocket 消息

```json
{ "type": "entity_changed",  "category": "characters", "id": 123, "data": {...} }
{ "type": "entity_created",  "category": "characters", "id": 456, "data": {...} }
{ "type": "entity_deleted",  "category": "characters", "id": 789 }
{ "type": "project_changed", "data": { ... } }
```

### 6.5 校验规则

1. 实体必须包含 `_id`（int64），全局唯一
2. 字段 key 必须在分类的 `fields` 列表中（`_id` 除外）
3. `required` 字段必须存在且非空
4. 值的基础类型必须匹配数据类型定义（结构体类型的值必须是数组且长度匹配）
5. UI 组件参数约束（min/max/options 等）必须满足

### 6.6 项目文件结构

```
gbox_data_editor/
│
├── server.py                           # FastAPI 后端入口
├── requirements.txt                    # fastapi, uvicorn, watchfiles
│
├── src/                                # ── React 前端（Vite + TypeScript）──
│   ├── main.tsx                        # 入口
│   ├── App.tsx                         # 根组件（Dockview 布局容器）
│   ├── theme.css                       # 全局主题（CSS 变量：色板、间距、圆角、阴影）
│   │
│   ├── core/                           # ── 纯逻辑层（无 UI）──
│   │   ├── builtins.ts                 # ★ 所有内置定义（基础类型、UI组件声明、槽位）
│   │   ├── types.ts                    # TypeScript 类型定义
│   │   ├── typeResolver.ts             # 类型覆盖链解析（沿 base 递归合并）
│   │   ├── api.ts                      # 后端 REST API 封装
│   │   ├── ws.ts                       # WebSocket 连接管理 + 自动重连
│   │   ├── store.ts                    # Zustand 全局状态
│   │   ├── history.ts                  # Undo/Redo 操作栈 + 防抖策略
│   │   ├── cache.ts                    # localStorage 缓存（崩溃恢复）
│   │   ├── validator.ts                # 字段值校验
│   │   └── id.ts                       # genId() 函数
│   │
│   ├── common/                         # ── 可复用 UI 基础组件 ──
│   │   ├── Modal.tsx                   # 通用弹窗容器
│   │   ├── Toast.tsx                   # 消息提示
│   │   ├── ConfirmDialog.tsx           # 确认对话框
│   │   ├── SearchBar.tsx               # 搜索输入框（带防抖）
│   │   ├── DragList.tsx                # 可拖拽排序列表
│   │   ├── FieldLabel.tsx              # 字段标签（label + 星号 + tooltip）
│   │   ├── ModeToggle.tsx              # [⊞] 快捷/原始模式切换按钮
│   │   └── IconPicker.tsx              # 图标选择器
│   │
│   ├── panels/                         # ── 可停靠面板（每个面板一个文件）──
│   │   ├── SidebarPanel.tsx            # 分类导航
│   │   ├── CardGridPanel.tsx           # 卡片网格
│   │   ├── PropertyPanel.tsx           # 属性编辑面板
│   │   ├── AIChatPanel.tsx             # AI 对话面板
│   │   ├── ChangeReviewPanel.tsx       # 变更审查面板
│   │   ├── HistoryPanel.tsx            # 操作历史面板
│   │   ├── SettingsPanel.tsx           # 设置面板（含 AI 配置）
│   │   ├── TypeManagerPanel.tsx        # 类型管理
│   │   ├── FieldManagerPanel.tsx       # 字段管理
│   │   └── CategoryManagerPanel.tsx    # 分类管理
│   │
│   ├── cards/                          # ── 卡片相关组件 ──
│   │   ├── CardItem.tsx                # 单张卡片（槽位渲染）
│   │   └── CardSlot.tsx                # 卡片槽位渲染器
│   │
│   ├── fields/                         # ── 字段编辑行 ──
│   │   ├── FieldRow.tsx                # 单个字段行（label + widget + [⊞]）
│   │   └── RawEditor.tsx               # 原始编辑模式（基础类型文本框）
│   │
│   ├── widgets/                        # ── UI 数据组件（每个一个文件）──
│   │   ├── registry.ts                 # 组件注册表
│   │   ├── InputWidget.tsx             # input (int/float/string)
│   │   ├── TextareaWidget.tsx          # textarea (string)
│   │   ├── RangeWidget.tsx             # range slider (int/float)
│   │   ├── EnumWidget.tsx              # enum dropdown (int/string)
│   │   ├── ToggleWidget.tsx            # toggle switch (int)
│   │   ├── ColorWidget.tsx             # color picker (int)
│   │   ├── TagsWidget.tsx              # tags multi-select (array)
│   │   ├── ImageWidget.tsx             # image preview + picker (string)
│   │   ├── AudioWidget.tsx             # audio player + picker (string)
│   │   ├── FileWidget.tsx              # file path picker (string)
│   │   ├── RefWidget.tsx               # entity reference (int)
│   │   ├── DateWidget.tsx              # date picker (string)
│   │   ├── ListWidget.tsx              # list editor (array)
│   │   ├── StructWidget.tsx            # struct container (array + template)
│   │   ├── Ani2dWidget.tsx             # 2dani canvas preview (string)
│   │   ├── IsometricWidget.tsx         # isometric grid editor (array)
│   │   └── JsonWidget.tsx              # fallback JSON text editor (any)
│   │
│   └── ai/                             # ── AI 集成 ──
│       ├── AIService.ts                # AI Provider 抽象层
│       ├── ChangeSet.ts                # 变更集数据结构 + diff 计算
│       └── PromptBuilder.ts            # 构建 AI 上下文（.gbdata schema + 当前实体）
│
├── vite.config.ts
├── tsconfig.json
└── package.json
```

**目录职责划分：**

| 目录 | 职责 | 原则 |
|------|------|------|
| `core/` | 纯逻辑，无 UI | 状态、类型解析、API、历史、校验。不 import React |
| `common/` | 可复用 UI 基础组件 | 不含业务逻辑，纯通用 UI 积木 |
| `panels/` | 可停靠面板 | 每个面板一个文件，注册到 Dockview |
| `cards/` | 卡片渲染 | 卡片 + 槽位渲染逻辑 |
| `fields/` | 字段编辑行 | FieldRow + 原始编辑器 |
| `widgets/` | 数据编辑组件 | 每个 UI 组件一个文件，实现三态协议 |
| `ai/` | AI 集成 | Provider 抽象、变更集、Prompt 构建 |

**扩展路径：**

- 加内置定义 → 改 `core/builtins.ts`
- 加 UI 数据组件 → 在 `widgets/` 加文件 + `registry.ts` 注册
- 加通用 UI 组件 → 在 `common/` 加文件
- 加新面板 → 在 `panels/` 加文件 + 注册到 Dockview
- 加 AI Provider → 在 `ai/AIService.ts` 中添加

---

## 7. ID 系统

### 7.1 ID 结构（int64）

```
┌──────────────────────────────┬──────────────────┐
│  时间戳 (48 bit)              │  随机数 (16 bit)  │
│  毫秒级，可用约 8900 年        │  0 - 65535       │
└──────────────────────────────┴──────────────────┘
```

与分类完全无关，实体可自由在分类间移动。

### 7.2 生成算法

```python
import time, random

def gen_id() -> int:
    ts = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand = random.randint(0, 0xFFFF)
    return (ts << 16) | rand
```

```javascript
function genId() {
    const ts = BigInt(Date.now()) & 0xFFFFFFFFFFFFn;
    const rand = BigInt(Math.floor(Math.random() * 0x10000));
    return Number((ts << 16n) | rand);
}
```

### 7.3 使用规则

- 每个实体必须包含 `_id`，创建时自动生成，不可修改
- 编辑器启动时建立 `_id → 实体` 的 HashMap
- 保存时校验 ID 唯一性
- 同一毫秒碰撞概率 1/65536，编辑器兜底检测

---

## 8. AI 集成

### 8.1 AI 对话面板

底部面板，支持与 AI 模型对话，AI 可直接操作游戏数据。

**功能：**
- 文本对话输入，支持 Markdown 渲染
- 拖入文件作为上下文（图片、JSON 等）
- 模型选择下拉（根据设置中配置的 Provider 列出可用模型）
- 流式响应（SSE），实时显示 AI 回复
- AI 操作数据后自动生成变更集，跳转到变更审查面板

**AI 上下文构建（PromptBuilder）：**

AI 发起请求时，自动注入以下上下文：
1. `.gbdata` 中的 types、fields、categories 定义
2. 当前选中的分类和实体（如有）
3. 用户拖入的附件
4. gen_id() 函数说明（让 AI 知道如何生成 ID）

### 8.2 AI 设置

设置面板中的 AI 标签页，配置 Provider 和模型：

```json
{
    "ai": {
        "providers": [
            {
                "name": "Anthropic",
                "type": "anthropic",
                "apiKey": "sk-ant-...",
                "baseUrl": "https://api.anthropic.com",
                "models": ["claude-sonnet-4-20250514", "claude-opus-4-20250514"]
            },
            {
                "name": "OpenAI",
                "type": "openai",
                "apiKey": "sk-...",
                "baseUrl": "https://api.openai.com/v1",
                "models": ["gpt-4o", "gpt-4o-mini"]
            },
            {
                "name": "本地模型",
                "type": "openai",
                "apiKey": "",
                "baseUrl": "http://localhost:11434/v1",
                "models": ["llama3", "qwen2"]
            }
        ],
        "defaultProvider": "Anthropic",
        "defaultModel": "claude-sonnet-4-20250514"
    }
}
```

- AI 配置存在 localStorage（不进 .gbdata，因为含 API Key）
- 支持 OpenAI 兼容格式（Ollama、vLLM 等本地模型直接可用）
- 后端作为代理转发请求（避免前端暴露 API Key）

### 8.3 变更审查系统

**核心原则：AI 不直接写文件，所有修改先生成变更集（Changeset），用户审查后才落盘。**

**变更集数据结构：**

```typescript
interface Changeset {
    id: string;                    // 变更集 ID
    source: string;                // 来源（"ai" | "user"）
    timestamp: number;
    description: string;           // AI 的操作描述
    changes: Change[];
}

interface Change {
    category: string;              // 分类 key
    entityId: number;              // _id
    entityName: string;            // 显示名（方便人看）
    action: "create" | "modify" | "delete";
    before: Record<string, any> | null;   // 修改前的值（create 时为 null）
    after: Record<string, any> | null;    // 修改后的值（delete 时为 null）
    fieldDiffs: FieldDiff[];       // 字段级别的具体差异
}

interface FieldDiff {
    field: string;                 // 字段 key
    label: string;                 // 字段显示名
    oldValue: any;
    newValue: any;
}
```

**变更审查面板 UI：**

```
┌──────────────────────────────────────────────────────────────┐
│  变更审查: "把所有角色hp提升20%"         [全部接受] [全部拒绝]  │
├──────────────────────────────────────────────────────────────┤
│  ☑ 🟡 goblin — 哥布林 (修改 2 个字段)                    [展开]│
│     hp:  50 → 60                                             │
│     atk: 8 → 10                                              │
│  ☑ 🟡 knight — 骑士 (修改 1 个字段)                      [展开]│
│     hp:  200 → 240                                           │
│  ☑ 🟢 elf_archer — 精灵弓手 (新建)                       [展开]│
│     name: "精灵弓手", hp: 120, class: "rogue", ...           │
│  ☐ 🔴 old_sword — 旧剑 (删除)                            [展开]│
│     （取消勾选 = 拒绝此删除）                                  │
├──────────────────────────────────────────────────────────────┤
│  已选 3/4 项                          [接受选中] [拒绝选中]    │
└──────────────────────────────────────────────────────────────┘
```

**交互流程：**

1. AI 对话中，AI 分析用户需求，生成修改方案
2. 后端执行 AI 的修改指令，但**不写入文件**，而是生成 Changeset
3. 前端自动切换到变更审查面板，展示变更集
4. 用户可以：
   - **逐条勾选/取消** — 细粒度控制接受哪些修改
   - **展开查看 diff** — 每个实体的每个字段变化一目了然
   - **全部接受** — 一键应用所有变更
   - **全部拒绝** — 丢弃整个变更集
5. 点击「接受选中」→ 被勾选的变更写入文件，卡片刷新
6. 被拒绝的变更丢弃

**变更历史：**

所有已接受和已拒绝的变更集都保留在历史记录中：

```
┌──────────────────────────────────────────────────────────────┐
│  变更历史                                                     │
├──────────────────────────────────────────────────────────────┤
│  15:30 [AI] "把所有角色hp提升20%" — 接受 3/4 项              │
│  15:25 [手动] 修改 goblin.name — 已保存                      │
│  15:20 [AI] "新建3个道具" — 全部接受                          │
│  15:10 [手动] 新建分类 "buildings" — 已保存                   │
└──────────────────────────────────────────────────────────────┘
```

点击任一历史条目可以查看当时的变更详情，已接受的变更可以选择回退（生成逆向变更集）。

### 8.4 外部 AI 协作（文件监听模式）

除了内置 AI 对话，编辑器也支持外部 AI（如 Claude Code CLI）直接修改文件：

1. 外部 AI 读取 `.gbdata` 了解结构
2. 外部 AI 直接写入/修改实体 JSON 文件
3. 编辑器通过文件监听检测到变更 → WebSocket 推送
4. 编辑器自动生成变更集，进入变更审查流程（和内置 AI 一样的审查体验）
5. 或者：非编辑中的实体静默刷新，编辑中的提示冲突

可以在设置中配置外部变更的处理模式：
- **自动接受** — 外部修改直接生效（信任外部 AI）
- **审查模式** — 外部修改也进入变更审查面板
- **提示模式** — 弹出提示让用户选择（默认）

---

## 9. 分阶段实施

### Phase 1 — 基础骨架

- Vite + React + TypeScript 项目搭建
- FastAPI 后端：.gbdata 读写、实体 CRUD、校验
- Dockview 面板布局（默认布局 + 拖拽 + Tab + 布局持久化）
- 面板：分类导航、卡片网格（槽位渲染）、属性面板
- 基础 widgets：input, textarea, range, enum, toggle, tags, json
- 组件三态：只读、快捷编辑、原始编辑
- 类型/字段/分类管理面板
- 文件监听 + WebSocket 自动刷新
- Undo/Redo + 操作历史面板 + 防抖策略
- 缓存与崩溃恢复
- 暗色主题，专业 UI

### Phase 2 — 媒体与高级组件

- image widget：预览 + 文件选择
- 2dani widget：Canvas 渲染预览
- audio widget：播放器
- color widget：ARGB 拾色器
- ref widget：跨分类引用 + 跳转
- 卡片缩略图渲染

### Phase 3 — AI 集成

- AI 对话面板（底部 Tab）
- AI 设置面板（Provider / 模型配置）
- 后端 AI 代理（SSE 流式响应）
- 变更审查面板（逐条勾选、字段级 diff、接受/拒绝）
- 变更历史（回溯、逆向回退）
- 外部 AI 文件监听模式

### Phase 4 — 高级交互

- isometric widget：菱形网格编辑
- 2dani widget：中心点拖拽、缩放
- list / struct widget 完善
- 搜索、筛选、批量操作
- CSV 导入导出
- 快捷键
- 实体跨分类移动（拖拽）
