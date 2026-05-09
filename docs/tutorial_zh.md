# Manalyzer 使用教程

本文档面向第一次接触本仓库的使用者和维护者，目标是说明 Manalyzer 解决的问题、仓库结构、运行环境、端到端流程、输出文件、WebUI、Benchmark 与烟测方法。文档尽量使用逐步说明，但保持专业表述。

## 1. 项目概览

Manalyzer 是一个面向自动化 Meta-analysis 的多智能体系统。传统 Meta-analysis 通常需要人工完成以下工作：

1. 明确研究主题和目标数据字段。
2. 检索相关论文。
3. 下载论文 PDF。
4. 阅读论文并判断是否与研究主题相关。
5. 从正文、表格、图像或图表中抽取数据。
6. 将不同论文中的数据合并为统一表格。
7. 对合并后的数据做统计分析和可视化。
8. 写出包含方法、结果、图表和参考文献的 Meta-analysis 报告。

Manalyzer 将上述流程拆成多个阶段，每个阶段由一个 Agent 或工具模块负责。整体流程不是单个模型一次性完成，而是通过多个角色分工、工具调用和反馈检查机制串联起来。

## 2. 适合的使用场景

Manalyzer 适合用于探索性或半自动化 Meta-analysis 工作流，例如：

- 根据一个科学主题检索论文并下载 PDF。
- 从论文中的表格、图表和正文中抽取结构化数据。
- 将不同论文的数据整理到同一 Markdown 表格模板中。
- 生成合并 CSV、基础可视化图和 Markdown 报告。
- 复现实验中的数据抽取 benchmark。

需要注意的是，Manalyzer 依赖 LLM、PDF 解析服务和外部学术搜索/下载接口。它不能替代人工最终审稿，也不应在没有人工核验的情况下直接用于高风险科研结论或正式发表结果。

## 3. 仓库结构

仓库根目录中的主要内容如下：

```text
Manalyzer/
├── agents/       # 多智能体核心逻辑
├── assets/       # README 中使用的图片资源
├── benchmark/    # 数据抽取 benchmark 脚本和答案
├── data/         # 本地运行产物，通常不提交
├── docs/         # 教程文档
├── tests/        # 标准库 unittest 烟测
├── tools/        # 学术搜索、PDF 下载、Sci-Hub 工具
├── utils/        # 日志、读取、清洗、评价等辅助函数
├── webui/        # Flask WebUI
├── workflow/     # 命令行和 WebUI 主流程入口
├── requirements.txt # Python 依赖安装入口
└── README.md     # 项目介绍与论文信息
```

初学者阅读代码时，建议按以下顺序：

1. 先读 `README.md`，理解论文与方法概览。
2. 再读 `workflow/main.py`，理解主流程串联方式。
3. 再读 `agents/` 中的各阶段实现。
4. 最后读 `tools/`、`utils/`、`benchmark/` 和 `webui/`。

## 4. 环境准备

### 4.1 Python 环境

仓库提供 `requirements.txt` 作为统一的 Python 依赖入口。建议使用独立虚拟环境，避免污染系统 Python。

示例：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4.2 依赖清单说明

`requirements.txt` 覆盖当前源码需要的主要运行依赖，包括：

- LLM 和评测接口：`structai`、`openai`。
- 学术检索和网络请求：`requests`、`arxiv`、`urllib3`。
- Markdown 和 HTML 解析：`beautifulsoup4`、`markdown`。
- 数据处理和可视化：`pandas`、`numpy`、`scikit-learn`、`matplotlib`、`Pillow`、`python-Levenshtein`。
- WebUI 和 benchmark：`flask`、`flask-cors`、`datasets`。
- 进度显示：`tqdm`。

其中 `structai` 是主流程的关键依赖。它不在当前仓库中定义，但主流程大量使用它：

- `structai.LLMAgent`
- `structai.multi_thread`
- `structai.read_pdf`
- `structai.save_file`
- `structai.get_all_file_paths`

如果当前环境没有 `structai`，主流程无法真正运行。烟测中的部分测试会使用 fake `structai`，因此烟测可以在缺少真实 API 环境时覆盖一些静态和局部行为，但不能替代完整运行。

### 4.3 API 环境变量

README 中给出的基本环境变量如下：

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
export MINERU_TOKEN="your-mineru-api-key"
```

含义：

- `LLM_API_KEY`：LLM 服务的 API key。
- `LLM_BASE_URL`：LLM 服务的 base URL。
- `MINERU_TOKEN`：PDF 解析服务 MinerU 的 token。

不同 `structai` 配置方式可能会影响这些变量的读取方式。正式运行前应确认本地 `structai` 版本与项目代码兼容。

## 5. 核心概念

### 5.1 研究领域、研究主题和表格模板

Manalyzer 的一个任务通常由三个输入定义：

- `field`：研究领域，例如 `environment`、`agriculture`、`atmosphere`。
- `topic_of_interest`：用户关心的具体问题，例如 `River pollutants`。
- `table_template`：希望抽取和整合出来的目标表格结构。

在 `workflow/main.py` 中，这三个输入目前是硬编码的：

```python
filed = 'environment'
topic_of_interest = 'River pollutants'
table_template = """
| River        | Location | Heavy metals | Content (µg/L) |
|--------------|----------|--------------|----------------|
| Tigris River | Turkey   | Cu           | 40             |
| Tigris River | Turkey   | Co           | 10             |
| Tiete River  | Brazil   | Fe           | 915            |
"""
```

注意：代码中变量名是 `filed`，不是 `field`。这是历史拼写问题，已经成为当前流程的一部分，不建议为了命名美观单独修改。

### 5.2 表格模板的作用

表格模板告诉模型最终需要什么字段。模板中的示例行也会为模型提供格式参考。一个好的模板应满足以下要求：

- 列名清晰，避免含糊表达。
- 单位写在列名中，例如 `Content (µg/L)`。
- 示例行真实、简短、格式一致。
- 不要把多个含义混在同一列中。

例如：

```markdown
| River | Location | Heavy metals | Content (µg/L) |
|---|---|---|---|
| Tigris River | Turkey | Cu | 40 |
```

这个模板表示：每一行应描述某条河流在某地某种重金属的含量。

## 6. Pipeline 阶段详解

`workflow/main.py` 按顺序执行 9 个阶段。理解这些阶段有助于调试完整 Pipeline，也有助于判断某个输出文件由哪个模块生成。

### 6.1 PaperCollector：论文检索与下载

位置：`agents/paper_collector.py`

作用：

1. 根据用户主题生成多组搜索关键词。
2. 使用 arXiv 或 Crossref 搜索论文。
3. 下载 PDF。
4. 写出 `0_paper_info.json`。

默认搜索引擎是 `arxiv`。如果使用 `crossref`，下载 DOI 论文会经过 Sci-Hub 相关路径。该路径依赖外部站点可用性，也可能涉及合规风险，使用前应自行确认。

典型输出：

```text
data/<field>/<timestamp>/
├── 0_pdf/
└── 0_paper_info.json
```

`0_paper_info.json` 中通常包含：

```json
{
  "00000": {
    "title": "Example Paper Title",
    "url": "https://arxiv.org/pdf/xxxx.xxxxx",
    "pdf_path": "data/environment/2026_0209_185427/0_pdf/00000.pdf"
  }
}
```

### 6.2 PaperParser：PDF 解析

位置：`agents/paper_parser.py`

作用：

1. 读取 `0_paper_info.json`。
2. 调用 `structai.read_pdf(pdf_paths)` 解析 PDF。
3. 定位每篇论文解析出的 `*_content_list.json` 和 `full.md`。
4. 写出 `1_content_list_info.json`。

此阶段依赖 MinerU 或 `structai` 内部的 PDF 解析能力。若 `MINERU_TOKEN` 未配置或解析服务不可用，此阶段可能失败。

### 6.3 PaperReviewer：论文筛选

位置：`agents/paper_reviewer.py`

作用：

1. 读取每篇论文的 Markdown 全文。
2. 清理短文本和无效内容。
3. 对每篇论文做独立评分：
   - `Topic Relevance`
   - `Feasibility`
4. 对一批论文做相对相关性评分：
   - `Relative Score`
5. 计算：
   - `Final Score = (Topic Relevance + Feasibility) * Relative Score`

输出文件：

```text
2_paper_score.json
3_selected_paper.json
```

`select_paper(save_dir, 10)` 会按最终分数选择 Top 10。若论文数量少于 10，则会保留已有论文。

### 6.4 TableProcessor：表格和图像转写

位置：`agents/table_processor.py`

作用：

1. 读取 `3_selected_paper.json`。
2. 遍历每篇论文的 content list。
3. 找出表格、图片、图表。
4. 调用视觉 LLM 将表格转为 Markdown，或将图像转为文字描述。
5. 写出 `2_text/<paper_idx>.json` 和 `4_converted_paper.json`。

此阶段的输出对后续数据抽取非常重要。如果图表转写质量差，后续抽取质量也会下降。

### 6.5 DataExtratorWithChecker：数据抽取与自检

位置：`agents/data_extrator_checker.py`

作用：

1. 从表格和正文两路收集候选信息。
2. 第一级过滤：判断每个表格或正文 section 是否可能含有相关数据。
3. 第二级整合：把相关数据转换为用户给定表格模板。
4. 检查器评分：
   - `Data Accuracy`
   - `Semantic Consistency`
   - `Data Completeness`
   - `Overall Score`
5. 如果检查器拒绝结果，则根据建议重新抽取。

输出文件：

```text
3_integrated_table/<paper_idx>.json
5_integrated_table_info.json
```

每篇论文的抽取结果通常分为：

```json
{
  "table": "...",
  "text": "..."
}
```

如果没有找到可用数据，可能为 `"None"`。

### 6.6 DataMerger：跨论文数据合并

位置：`agents/data_merger.py`

作用：

1. 读取所有论文的抽取结果。
2. 解析其中的 Markdown 表格。
3. 将列名映射到用户模板中的标准列。
4. 追加 `Reference` 列标记数据来源论文。
5. 调用 LLM 标准化数值字段，例如：
   - 去掉千分位符号。
   - 百分比转小数。
   - 数值范围取平均。
   - 无法转换的值设为 `None`。

输出文件：

```text
meta_analysis.csv
```

该文件是后续分析和报告生成的核心数据表。

### 6.7 DataAnalyst：数据分析与可视化

位置：`agents/data_analyst.py`

作用：

1. 读取 `meta_analysis.csv`。
2. 删除 `Reference` 列。
3. 让 LLM 生成三个可视化函数：
   - `clustering(data)`
   - `classification(data)`
   - `regression(data)`
4. 执行生成的代码并保存图片。

输出文件：

```text
4_visualization/clustering.png
4_visualization/classification.png
4_visualization/regression.png
```

重要说明：该阶段使用 `exec(code)` 执行 LLM 生成代码。正式环境中应使用受限权限、可信模型和隔离环境。

### 6.8 Reporter：报告生成

位置：`agents/reporter.py`

作用：

1. 读取 `meta_analysis.csv`。
2. 读取可视化图片。
3. 读取论文标题作为参考文献。
4. 让 LLM 生成 Markdown 格式的 Meta-analysis 报告。

输出文件：

```text
meta_analysis_report.md
```

报告会尝试包含方法、结果、图表和参考文献。

## 7. 完整运行：命令行模式

本节说明如何通过 `workflow/main.py` 直接串行运行完整 Manalyzer Pipeline。命令行模式不经过浏览器交互，适合服务器、远程终端、批处理实验和单次任务调试。

### 7.1 直接运行命令

如果已经安装依赖，并且已经在 `workflow/main.py` 中改好 `filed`、`topic_of_interest`、`table_template` 等任务输入，可以在仓库根目录直接执行：

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
export MINERU_TOKEN="your-mineru-api-key"

python workflow/main.py
```

建议在正式运行前先执行一次快速烟测：

```bash
python -m unittest discover -s tests
python -m compileall -q agents tools utils workflow benchmark webui tests
```

运行结束后，结果会写入：

```text
data/<field>/<timestamp>/
```

例如当前示例任务可能生成：

```text
data/environment/2026_0209_185427/
```

可以用下面的命令查看最近一次运行目录：

```bash
ls -td data/*/* | head -1
```

完整命令行流程就是：

```bash
cd /path/to/Manalyzer
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
export MINERU_TOKEN="your-mineru-api-key"
python workflow/main.py
```

如果只是第一次验证仓库代码没有明显静态问题，而不想调用外部 API，则只运行：

```bash
python -m unittest discover -s tests
```

### 7.2 确认运行前条件

在运行完整 Pipeline 之前，应确认以下条件已经满足：

1. 已通过 `python -m pip install -r requirements.txt` 安装项目所需依赖。
2. 已配置 LLM 服务环境变量：

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
```

3. 已配置 PDF 解析服务环境变量：

```bash
export MINERU_TOKEN="your-mineru-api-key"
```

4. 当前工作目录是仓库根目录。推荐先执行：

```bash
pwd
```

确认路径类似：

```text
/path/to/Manalyzer
```

5. 能够访问所选搜索源和下载源。默认流程使用 arXiv 检索和下载，因此需要可访问 arXiv。

### 7.3 修改任务输入

命令行模式的任务输入位于 `workflow/main.py`。打开该文件，重点修改三处。

第一处是研究领域：

```python
filed = 'environment'
```

这里的 `filed` 会用于：

- 创建输出目录 `data/<field>/<timestamp>/`。
- 替换多个 Agent prompt 中的领域占位符。
- 标识日志和结果所属领域。

第二处是研究主题：

```python
topic_of_interest = 'River pollutants'
```

该主题会用于：

- 生成论文检索关键词。
- 判断论文是否相关。
- 判断表格、图像和正文是否包含目标数据。
- 指导最终报告生成。

第三处是目标表格模板：

```python
table_template = """
| River        | Location | Heavy metals | Content (µg/L) |
|--------------|----------|--------------|----------------|
| Tigris River | Turkey   | Cu           | 40             |
| Tigris River | Turkey   | Co           | 10             |
| Tiete River  | Brazil   | Fe           | 915            |
"""
```

模板决定最终 `meta_analysis.csv` 的列结构。修改模板时，应保持 Markdown 表格格式完整，至少包含表头、分隔行和一到数行示例。

### 7.4 修改论文来源和数量

`workflow/main.py` 中的论文收集调用如下：

```python
paper_collector(topic_of_interest, paper_list=['EU-wide survey of polar organic persistent pollutants in European river waters'], paper_search_num=1)
```

含义如下：

- `paper_list`：指定必须检索的论文标题列表。适合已知关键论文的情况。
- `paper_search_num`：每组关键词返回的论文数量。值越大，下载和后续 LLM 调用成本越高。
- 如果希望只使用关键词搜索，可以删除或设为 `paper_list=None`。
- 如果希望从 DOI 下载，可以在代码中传入 `doi_list=[...]`，但 DOI 下载路径可能依赖 Sci-Hub，应谨慎使用。

示例：只做关键词搜索，每组关键词取 2 篇论文：

```python
paper_collector(topic_of_interest, paper_list=None, paper_search_num=2)
```

示例：指定一篇论文标题，同时每组关键词再取 1 篇论文：

```python
paper_collector(
    topic_of_interest,
    paper_list=['A known important paper title'],
    paper_search_num=1,
)
```

### 7.5 修改筛选数量

论文评审后，代码会调用：

```python
select_paper(save_dir, 10)
```

这里的 `10` 表示按 `Final Score` 选择前 10 篇论文进入后续抽取阶段。若希望处理全部已下载论文，可以改为：

```python
select_paper(save_dir, -1)
```

处理更多论文会显著增加图表转写、数据抽取和报告生成的 LLM 调用量。

### 7.6 运行完整 Pipeline

确认输入和环境变量后，在仓库根目录执行：

```bash
python workflow/main.py
```

运行过程中，终端会输出各阶段日志，并在 `data/<field>/<timestamp>/log/` 下写入日志文件。每次运行都会创建新的时间戳目录，不会覆盖之前的运行结果。

### 7.7 串行运行时如何判断进度

命令行模式没有浏览器进度条。判断进度的可靠方式是检查输出目录中是否出现对应阶段文件：

1. `0_paper_info.json` 出现，说明论文检索与下载阶段完成。
2. `1_content_list_info.json` 出现，说明 PDF 解析阶段完成。
3. `2_paper_score.json` 和 `3_selected_paper.json` 出现，说明论文评审与筛选完成。
4. `4_converted_paper.json` 和 `2_text/` 出现，说明图表转写完成。
5. `5_integrated_table_info.json` 和 `3_integrated_table/` 出现，说明数据抽取完成。
6. `meta_analysis.csv` 出现，说明跨论文数据合并完成。
7. `4_visualization/` 中出现图片，说明数据分析可视化完成。
8. `meta_analysis_report.md` 出现，说明报告生成完成。

### 7.8 完整运行后的人工检查顺序

完整 Pipeline 运行结束后，不建议只阅读最终报告。更可靠的检查顺序是：

1. 打开 `0_paper_info.json`，确认下载的论文是否与主题相关。
2. 打开 `2_paper_score.json`，查看评分是否合理。
3. 打开 `3_selected_paper.json`，确认进入抽取阶段的论文没有明显偏题。
4. 抽查 `2_text/<paper_idx>.json`，确认表格和图像转写没有明显错误。
5. 抽查 `3_integrated_table/<paper_idx>.json`，确认抽取表格与原论文内容一致。
6. 打开 `meta_analysis.csv`，确认列名、单位、数值格式和 `Reference` 来源列。
7. 打开 `4_visualization/*.png`，确认图像不是空图或明显错误图。
8. 最后阅读 `meta_analysis_report.md`，并与前面文件交叉核对。

### 7.9 常见失败点

命令行完整 Pipeline 常见失败点包括：

- 缺少 `structai`：主流程无法导入 `LLMAgent`、`read_pdf` 等对象。
- 缺少 `MINERU_TOKEN`：PDF 解析阶段失败。
- LLM API key 或 base URL 配置错误：Agent 调用失败。
- arXiv、Crossref 或 Sci-Hub 网络不可用：论文检索或下载失败。
- 表格模板格式不完整：`DataMerger` 无法正确解析标准列。
- 下载论文与主题弱相关：后续抽取可能生成无意义数据。
- LLM 输出的 Markdown 表格不规范：合并阶段可能跳过行或列。

如果需要定位问题，应优先查看运行目录下的 `log/` 文件，而不是只看终端最后一段输出。

## 8. 输出目录示例

一次运行会创建类似目录：

```text
data/environment/2026_0209_185427/
├── 0_pdf/
├── 0_paper_info.json
├── 1_content_list_info.json
├── 2_paper_score.json
├── 2_text/
├── 3_integrated_table/
├── 3_selected_paper.json
├── 4_converted_paper.json
├── 4_visualization/
├── 5_integrated_table_info.json
├── log/
├── meta_analysis.csv
└── meta_analysis_report.md
```

初学者调试时建议按文件编号检查阶段是否完成：

1. 没有 `0_paper_info.json`：论文检索或下载阶段失败。
2. 没有 `1_content_list_info.json`：PDF 解析阶段失败。
3. 没有 `3_selected_paper.json`：论文评审或筛选阶段失败。
4. 没有 `4_converted_paper.json`：表格/图像转写阶段失败。
5. 没有 `5_integrated_table_info.json`：数据抽取阶段失败。
6. 没有 `meta_analysis.csv`：数据合并阶段失败。
7. 没有 `meta_analysis_report.md`：报告生成阶段失败。

## 9. 可视化 WebUI 运行

可视化 WebUI 运行与第 7 节的命令行完整运行使用同一条 Manalyzer Pipeline。论文收集、PDF 解析、论文评审、图表转写、数据抽取、数据合并、分析可视化和报告生成的阶段顺序保持一致。

二者的区别在于交互方式：命令行模式需要直接修改 `workflow/main.py` 中的任务输入；WebUI 模式通过浏览器表单提交 `Field`、`Topic of Interest` 和 `Table Template`，并在页面中展示日志、输出文件树和阶段进度。也就是说，WebUI 增加的是前端交互层，不是另一套分析逻辑。

WebUI 由两个进程协作：

1. `workflow/main_webui.py` 负责后台流程。
2. `webui/weiui.py` 负责 Flask 页面和 API。

如果尚未安装依赖，应先在仓库根目录执行：

```bash
python -m pip install -r requirements.txt
```

推荐在两个终端中运行。

终端 A：

```bash
python workflow/main_webui.py
```

该进程会：

1. 清理 `webui/data/user_input.json`。
2. 创建 `webui/data/chat.log`。
3. 创建 `webui/data/save_info.json`。
4. 等待 WebUI 写入用户输入。

终端 B：

```bash
python webui/weiui.py
```

然后在浏览器中打开：

```text
http://127.0.0.1:5000
```

页面提供三个输入框：

- `Field`
- `Topic of Interest`
- `Table Template`

点击 Confirm 后，WebUI 会写入：

```text
webui/data/user_input.json
```

后台流程检测到输入后继续运行。

## 10. Benchmark 使用方式

Benchmark 脚本位于 `benchmark/`。

### 10.1 抽取

```bash
python benchmark/1_extractor.py
```

该脚本会：

1. 从 Hugging Face 加载 `CoCoOne/Manalyzer` 数据集。
2. 使用 `utils.eval.EvaluationModel` 调用指定模型。
3. 抽取结果写入：

```text
benchmark/results/<model>/<field>/*.json
```

默认配置在脚本中硬编码，例如：

```python
field = "agriculture"
model = "grok-3"
```

如果需要切换领域或模型，应修改脚本中的对应变量。

### 10.2 评分

```bash
python benchmark/2_score.py
```

该脚本会读取：

```text
benchmark/results/**/*.json
benchmark/answer.json
```

然后统计不同模型在 `level_1`、`level_2`、`level_3` 上的数值命中率。

## 11. 快速烟测

本仓库新增了 `tests/` 目录，用标准库 `unittest` 提供轻量烟测。运行命令：

```bash
python -m unittest discover -s tests
```

当前烟测覆盖：

- 所有 Python 文件可编译。
- 轻依赖模块可导入。
- `utils` 中核心小函数的基本行为。
- 生产代码中不应出现裸 `except` 和运行时 `assert`。
- WebUI 路径约定不应回退到错误的 `data/...`。
- SciHub 应保持懒加载，避免 import 阶段触发网络请求。
- 工具层网络请求应带 timeout。
- `DataExtratorWithChecker` 的正文拼接应使用真实换行。
- `PaperParser` 和 `DataMerger` 的关键边界行为。
- `requirements.txt` 应覆盖当前运行依赖清单。

烟测不是完整集成测试。它不会真实调用：

- LLM API。
- MinerU PDF 解析。
- arXiv。
- Sci-Hub。
- Hugging Face 数据集。

如果修改了流程代码，至少应运行：

```bash
python -m compileall -q agents tools utils workflow benchmark webui tests
python -m unittest discover -s tests
```

## 12. 常见问题

### 12.1 为什么运行主流程时提示缺少 `structai`

原因通常是尚未在当前 Python 环境中执行 `python -m pip install -r requirements.txt`，或者安装命令运行在另一个虚拟环境中。`structai` 不是当前仓库源码的一部分，但已经写入依赖清单；如果仍然缺失，应先确认当前终端使用的 `python` 与安装依赖时使用的是同一个解释器。

### 12.2 为什么论文检索结果和主题不完全相关

默认搜索引擎是 arXiv。对于环境、医学、农业等非 arXiv 强覆盖领域，关键词检索可能返回相关性不高的论文。后续 `PaperReviewer` 会尝试筛选，但不能保证完全正确。

### 12.3 为什么报告内容需要人工复核

报告由 LLM 根据抽取表格、图片和参考文献生成。若前面任一阶段出现误检、漏检或抽取错误，报告也会受到影响。正式使用时必须人工复核原文、表格和最终结论。

### 12.4 为什么 WebUI 需要两个进程

当前设计中，后台流程和 Flask 页面是两个独立脚本。后台流程等待 `webui/data/user_input.json`，Flask 页面负责创建该文件。

### 12.5 为什么测试不直接跑完整主流程

完整主流程依赖外部 API、网络、PDF 解析和 LLM 调用，成本高且不稳定。当前 `tests/` 的目标是快速捕获明显代码问题，而不是验证科研结果质量。

## 13. 最小入门路径

如果只是想理解本仓库，建议按以下路径：

1. 阅读 `README.md`。
2. 阅读 `workflow/main.py`。
3. 阅读 `agents/paper_collector.py` 到 `agents/reporter.py`。
4. 阅读 `data/environment/2026_0209_185427/` 中的示例产物。
5. 运行：

```bash
python -m unittest discover -s tests
```

6. 在通过 `requirements.txt` 安装依赖并配置好 API 后，再尝试运行：

```bash
python workflow/main.py
```

这样可以先理解流程，再进入真实外部调用，降低调试难度。
