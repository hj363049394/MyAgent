# Hermes Agent 深度调研：自进化 AI Agent 的真相与实践

> 资料来源：爆火出圈的Hermes Agent深度调研：自进化AI Agent的真相与实践（CSDN，2026-04-12 原创 / 2026-07-13 推荐）
> 原文链接：https://blog.csdn.net/weixin_41645817/article/details/160073929

---

## 一、Hermes Agent 核心简介：一款"会成长"的自主 Agent

Hermes Agent 是由 **Nous Research**（知名 AI 研究实验室，背后打造了 Hermes、Nomos、Psyche 等知名模型）于 **2026 年 2 月底** 开源的自我改进型 AI Agent 框架，其核心口号是 **"The agent that grows with you"**（与你一起成长的 Agent）。

凭借独特的自进化理念，该项目上线后爆发力惊人，**短短不到两个月，GitHub 星标从零飙升至近 6 万**，成为 OpenClaw 上线以来第一个真正意义上的强有力竞争对手，彻底打破了 Agent 领域的格局。

与传统 Agent 框架"被动接收指令、机械执行任务"的模式不同，Hermes Agent 的核心竞争力是内置了完整的学习闭环——它不仅能完成用户下达的任务，更能从任务经验中自主沉淀能力、优化行为，主动推动知识持久化，并在多轮会话中不断深化对用户的理解，真正实现"越用越智能"。

### 1.1 核心亮点：自进化学习闭环（最大卖点）

这是 Hermes Agent 最具辨识度的技术特色，也是其"成长能力"的核心来源。它在完成复杂任务后，会自动执行以下四个关键动作，形成完整的学习闭环：

- **自动抽象方法论**：将成功完成任务的完整工作流，封装为可复用的 Skill（技能），避免重复劳动，实现能力沉淀
- **持续迭代优化**：在后续执行同类任务时，会基于实际反馈不断改进已有的 Skill，优化执行效率与效果
- **主动知识持久化**：通过 FTS5 全文检索技术结合 LLM 总结，实现跨会话的记忆召回，不会"用完就忘"
- **构建用户模型**：通过多轮交互，逐渐理解用户的代码风格、技术偏好、使用习惯，提供个性化的任务执行方案

### 1.2 三大核心组件支撑学习闭环

#### Skills System（技能系统）

Skill 是 Hermes Agent 能力沉淀的核心载体，本质是可复用的 Python 工具，其核心特点：

- Agent 可自主创建新 Skill：无需用户手动编写，完成复杂任务后自动抽象生成
- 便捷管理：通过 `hermes skills` 命令即可完成 Skill 的查看、启用、禁用等操作
- 开放兼容：完全兼容 agentskills.io 开放标准，支持社区贡献的 Skill 共享与复用
- 自动沉淀：成功的工作流会被自动抽象为可复用的 Skill，形成个人专属技能库

#### Persistent Memory（持久化记忆）

记忆系统是 Hermes Agent"成长"的基础，负责存储长期事实与用户画像，核心设计：

- 存储载体：通过 `MEMORY.md`（存储长期事实）和 `USER.md`（存储用户画像）两个文件管理记忆
- 初始化配置：通过 `SOUL.md` 文件播种 Agent 的基础人格与行为准则
- 检索能力：基于 SQLite FTS5 全文检索技术，实现跨会话的记忆快速召回，让 Agent 记住用户的偏好与历史交互细节

#### Honcho Integration（用户建模）

Hermes Agent 通过集成 honcho-ai 包，实现 AI 原生的记忆管理与用户建模：

- 可通过 `hermes honcho` 命令访问用户建模相关功能
- 基于多轮交互数据，逐渐理解用户的代码风格、技术栈、任务偏好，实现个性化任务执行

> **实测验证**：给 Hermes Agent 下达模糊指令（如"写一个抓取数据并生成可视化的脚本"），它能自主完成任务拆解、工具选择、代码生成、调试优化的完整流程；当再次使用同一个 Skill 执行同类任务时，速度提升约 40%，充分体现了其"持续成长"的特性。

### 1.3 其他核心特性（加分项）

- **跨平台部署**：可运行在 Linux、macOS、WSL2、Android（Termux）等多种环境，支持本地、Docker、SSH、Daytona 等 6 种终端后端，甚至可部署在 5 美元的 VPS 或 GPU 集群上，serverless 模式下闲置时成本几乎为零
- **多渠道交互**：支持 CLI、Telegram、Discord、Slack、WhatsApp 等 14+ 种交互平台，用户可随时随地与 Agent 沟通，无需依赖电脑
- **模型无关**：兼容 Nous Portal、OpenRouter（200+ 模型）、OpenAI、Kimi 等多种 LLM 提供商，可通过 `hermes model` 命令切换模型，无锁死风险
- **丰富工具集**：内置 47 种工具，支持网页搜索、图像生成、TTS 等全场景需求，还可通过 MCP 集成扩展工具能力
- **OpenClaw 迁移支持**：提供 `hermes claw migrate` 命令，可自动导入 OpenClaw 的设置、记忆、技能和 API 密钥，降低用户迁移成本

---

## 二、深度挖掘：自进化引擎 —— hermes-agent-self-evolution

调研过程中发现一个关键信息：**Hermes Agent 的自进化能力并非框架原生内置，而是依赖一个独立的子项目 —— hermes-agent-self-evolution**。该项目是 Hermes 自进化能力的核心引擎，通过 DSPy + GEPA 框架实现，专门负责 Agent 技能、工具、提示词的自动进化与优化。

### 2.1 核心定位与技术栈

hermes-agent-self-evolution 的核心目标是：通过反射式进化搜索，自动优化 Hermes Agent 的技能、工具描述、系统提示词和代码，生成性能更优的变体，且**无需 GPU 训练**，全程通过 API 调用完成，**单次优化成本仅 2-10 美元**。

其核心技术栈由三大组件构成，各司其职、协同工作：

- **DSPy**：声明式提示词优化框架，负责将 Skill、工具描述等文本组件包装为可优化的模块，是进化的基础载体
- **GEPA**：全称为 Genetic-Pareto Prompt Evolution（反射式提示优化器，ICLR 2026 Oral 论文成果），核心能力是读取执行轨迹、诊断失败原因，生成针对性的优化变体，而非随机变异
- **Darwinian Evolver**：来自 imbue-ai/darwinian_evolver 的代码进化引擎，负责后续代码层面的进化，采用 Git-based 有机体设计，目前暂未实现

### 2.2 五阶段进化规划（核心设计）

hermes-agent-self-evolution 规划了五阶段进化路线，从基础的 Skill 优化到完整的自动化进化闭环，逐步实现 Hermes Agent 的全维度自进化：

1. **Phase 1: Skill 进化**：优化 SKILL.md 文档，提升 Agent 执行技能的效果
2. **Phase 2: 工具描述进化**：改进工具的 description 字段及参数描述，让 Agent 更准确地选择和使用工具
3. **Phase 3: 系统提示词进化**：分段优化系统提示词（身份、能力、响应风格、行为约束），规范 Agent 行为
4. **Phase 4: 代码进化**：通过 Darwinian Evolver 实现工具代码的自动进化，提升代码质量与性能
5. **Phase 5: 持续监控循环**：构建自动化进化 pipeline，实时监控 Agent 性能，自动触发进化任务并完成部署

---

## 三、关键发现：项目现状与未实现功能

经过深入研读 hermes-agent-self-evolution 的源码，发现一个重要事实：**目前该项目的五阶段进化规划，仅实现了 Phase 1（Skill 进化），Phase 2-5 均处于空壳状态**，仅包含基础的 `__init__.py` 文件，未实现任何核心逻辑。

| 阶段 | 对应目录 | 状态 |
|---|---|---|
| Phase 1: Skill 进化 | `evolution/skills/` | ✅ 完整实现 |
| Phase 2: 工具描述进化 | `evolution/tools/` | ❌ 仅 `__init__.py` |
| Phase 3: 系统提示词进化 | `evolution/prompts/` | ❌ 仅 `__init__.py` |
| Phase 4: 代码进化 | `evolution/code/` | ❌ 仅 `__init__.py` |
| Phase 5: 持续监控循环 | `evolution/monitor/` | ❌ 仅 `__init__.py` |

这意味着，当前 Hermes Agent 的自进化能力，仅能实现 Skill 文档的优化，距离"全维度自进化"还有较长的路要走。但 Phase 1 的实现已经非常完整，具备实际使用价值。

---

## 四、Phase 1: Skill 进化 ✅ 已完整实现

### 核心目标
优化 SKILL.md 文档的内容，让 Agent 在执行该技能时，准确率、效率更优，更贴合用户需求。

### 完整实现流程（基于源码梳理）

```
1. 加载 Skill 文件
   ├─ find_skill() 在 hermes-agent/skills/ 中找到目标 SKILL.md
   └─ load_skill() 解析 YAML frontmatter + markdown body

2. 构建评估数据集（三种来源，可灵活选择）
   ├─ A) 合成生成（SyntheticDatasetBuilder）
   │   └─ LLM 读取 skill 文本，生成 (task_input, expected_behavior) 测试用例
   ├─ B) SessionDB 挖掘（external_importers.py）
   │   ├─ Claude Code (~/.claude/history.jsonl) — 提取用户输入
   │   ├─ Copilot (~/.copilot/session-state/) — 提取完整对话
   │   └─ Hermes (~/.hermes/sessions/) — 提取用户+助手+工具上下文
   └─ C) Golden 数据集 — 人工标注的 JSONL 测试文件

3. 包装为 DSPy 模块
   ├─ SkillModule(skill_text) 将 skill body 作为可优化参数
   └─ forward(task_input) → 用 skill 指令完成任务 → 返回 output

4. 运行 GEPA 优化
   ├─ 配置 DSPy LM（指定优化所用的 LLM 模型）
   ├─ 创建 baseline_module = SkillModule(原始 skill body)（基准模型）
   ├─ 准备 trainset / valset（转换为 DSPy Example 格式）
   └─ optimizer = dspy.GEPA(metric=skill_fitness_metric, max_steps=N)
       ├─ optimized_module = optimizer.compile(baseline_module, trainset, valset)
       └─ 若 GEPA 不可用，自动降级到 MIPROv2 优化器

5. 约束验证（ConstraintValidator）—— 确保优化后的 Skill 符合规范
   ├─ 大小限制（max_skill_size: 15KB）
   ├─ 增长限制（max_prompt_growth: 20%，避免过度膨胀）
   ├─ 非空检查（确保核心内容不缺失）
   ├─ 结构完整性（必须包含 YAML frontmatter + name + description）
   └─ 测试套件（可选：运行 pytest，确保 Skill 可正常使用）

6. Holdout 评估 — 对比优化效果
   ├─ 在 holdout 测试集上分别运行基准模型（baseline）和优化后模型（evolved）
   ├─ 计算 skill_fitness_metric 平均分（评估优化效果）
   └─ 生成对比报告，明确优化提升点

7. 保存输出 — 留存优化结果
   ├─ output/<skill>/<timestamp>/evolved_skill.md（优化后的 Skill 文件）
   ├─ output/<skill>/<timestamp>/baseline_skill.md（原始 Skill 文件，用于对比）
   └─ output/<skill>/<timestamp>/metrics.json（评估指标数据）
```

### 实际使用方式（可直接复制运行）

```bash
python -m evolution.skills.evolve_skill \
  --skill github-code-review \        # 目标 Skill 名称
  --iterations 10 \                    # 进化迭代次数
  --eval-source synthetic \            # 评估数据集来源（synthetic/session/golden）
  --optimizer-model openai/gpt-4.1 \   # 优化所用 LLM 模型
  --eval-model openai/gpt-4.1-mini     # 评估所用 LLM 模型
```

---

## 五、Phase 2-5: 未实现阶段设计思路梳理

虽然 Phase 2-5 目前未实现，但结合项目 PLAN.md 和源码注释，可梳理出其核心设计思路：

### Phase 2: 工具描述进化 ❌ 未实现

- **优化目标**：优化工具的 description 字段（说明工具用途）和参数的 description 字段（说明参数含义），让 Agent 能更准确地判断"什么时候该用这个工具""如何正确使用工具参数"
- **预期流程**：提取 hermes-agent 工具注册表中的工具定义 → 生成评估数据集（围绕"工具使用场景"设计测试用例） → 将工具描述包装为 DSPy 模块 → 用 GEPA 优化 → 约束验证（工具描述 ≤ 500 字符，参数描述 ≤ 200 字符） → 回写到工具定义文件

### Phase 3: 系统提示词进化 ❌ 未实现

- **优化目标**：分段优化系统提示词，避免整体优化导致的语义混乱，同时提升 Agent 的行为规范性
- **预期流程**：将系统提示词拆分为 4 个独立段落（Identity 段：你是谁；Capabilities 段：你能做什么；Response Style 段：怎么说话；Rules 段：行为约束） → 对每段独立进行 GEPA 优化 → 验证段间语义一致性 → 合并优化后的提示词

### Phase 4: 代码进化 ❌ 未实现

- **优化目标**：通过 Darwinian Evolver 实现工具代码的自动进化，提升代码的可读性、性能和稳定性
- **预期流程**：以工具代码为"Organism"（进化实体） → 用 Evaluator 评估代码质量（测试通过率、性能指标） → 用 Mutator（LLM 驱动）生成代码变异体 → 安全门控（100% 测试通过 + 性能不倒退 + 人工审查） → 输出优化后的代码

### Phase 5: 持续监控循环 ❌ 未实现

- **优化目标**：构建端到端的自动化进化闭环，无需人工干预，实现 Agent 的持续自我提升
- **预期流程**：`Production Agent → 收集真实交互数据 → Monitor 检测性能下降 → 触发进化任务 → 执行 Phase 1-4 进化 → Benchmark Gate（质量验证） → 生成 GitHub PR → 自动部署`

---

## 六、调研总结

### 核心优势
- **理念先进**：以"自进化"为核心，贴合 Agent 技术的发展趋势，解决了传统 Agent"不会成长"的痛点
- **落地性强**：Phase 1 的 Skill 进化已完整实现，可直接用于实际场景，提升 Agent 执行效率
- **生态友好**：兼容 OpenClaw 迁移、agentskills.io 标准、多 LLM 模型，降低用户使用和扩展成本
- **部署灵活**：支持多环境、多平台部署，闲置成本低，适合个人开发者和企业级使用

### 局限性
- 目前自进化能力仅实现了 Skill 优化，距离"全维度自进化"还有较大差距
- 项目仍处于快速迭代阶段，部分功能（如 Phase 2-5）尚未落地，稳定性和兼容性仍需进一步验证

### MVP 重构要点

在研读源码后，可借助 AI 辅助完成面向 OpenClaw Skill 的自演进 MVP 版本开发。完整流程从输入到产出可分为 8 个关键步骤：

1. **准备 Skill**：统一输入结构（名称 + 描述 + 正文），从 SkillHub 获取或读取本机 SKILL.md
2. **挖掘 Session 任务**：在本地会话目录中按"最近优先"选取会话文件，解析用户消息构建基础训练数据池
3. **（可选）加入人工金标样本**：JSONL 格式，明确标注"任务是什么、期望助手如何表现"提供硬监督信号
4. **合成补充样本**：让大模型完整阅读目标 Skill，自动生成"用户可能提出的问题 + 对应期望行为"配对样本
5. **合并数据并划分用途**：训练集 / 验证集 / 留出集三段划分，避免"看着答案调参"的自我欺骗
6. **DSPy 优化**：优先 GEPA 强方法，失败自动降级 MIPROv2；评分采用"模型评模型"，金标样本质量决定评分可信度
7. **约束验证**：正文非空、体积限制、增长幅度限制、Markdown 结构规范
8. **Holdout 评估**：在全程不参与优化的留出集上对比 baseline 与 evolved，生成 metrics.json

> **关键提醒**：数据划分是保证优化有效性的核心——若未区分数据用途，后续所谓的"优化提升"将无法验证，无法判断是真实提升还是过拟合导致的虚假效果。
