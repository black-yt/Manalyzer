# Manalyzer Tutorial

This tutorial is written for first-time users and maintainers of this repository. It explains what Manalyzer does, how the repository is organized, how to prepare the environment, how the end-to-end workflow runs, what files are produced, how to use the WebUI and benchmark scripts, and how to run the smoke tests.

The tutorial intentionally uses a detailed and professional style. Manalyzer is research code, so the correct way to use it is to understand the workflow, verify intermediate outputs, and manually review final results.

## 1. Project Overview

Manalyzer is a multi-agent system for automated Meta-analysis. A traditional Meta-analysis workflow usually requires the following steps:

1. Define the research topic and target data fields.
2. Search for relevant papers.
3. Download PDF files.
4. Read papers and decide whether they are relevant.
5. Extract data from text, tables, figures, and charts.
6. Merge data from different papers into a unified table.
7. Analyze and visualize the merged data.
8. Write a Meta-analysis report with methods, results, figures, and references.

Manalyzer decomposes this process into multiple stages. Each stage is handled by a dedicated agent or tool module. The system does not rely on a single large prompt; instead, it uses staged processing, tool calls, and feedback checking.

## 2. Suitable Use Cases

Manalyzer is suitable for exploratory or semi-automated Meta-analysis workflows, such as:

- Searching and downloading papers for a scientific topic.
- Extracting structured data from tables, figures, charts, and paper text.
- Converting extracted information into a user-provided Markdown table schema.
- Producing a merged CSV file, basic visualizations, and a Markdown report.
- Running the Manalyzer benchmark extraction and scoring scripts.

Manalyzer depends on LLM services, PDF parsing services, academic search APIs, and paper download tools. It does not replace expert review. Final tables, visualizations, and reports should always be manually checked before being used for formal research conclusions.

## 3. Repository Structure

The main directories are:

```text
Manalyzer/
├── agents/       # Core multi-agent logic
├── assets/       # Images used by README
├── benchmark/    # Benchmark extraction and scoring scripts
├── data/         # Local runtime outputs, usually not committed
├── docs/         # Tutorial documentation
├── tests/        # Lightweight unittest smoke tests
├── tools/        # Academic search, PDF download, Sci-Hub utilities
├── utils/        # Logging, reading, cleaning, evaluation helpers
├── webui/        # Flask WebUI
├── workflow/     # Main command-line and WebUI workflow entry points
├── requirements.txt # Python dependency entry point
└── README.md     # Project overview and paper information
```

Recommended reading order:

1. Read `README.md` to understand the method and paper context.
2. Read `workflow/main.py` to understand the full workflow.
3. Read the agent implementations in `agents/`.
4. Then inspect `tools/`, `utils/`, `benchmark/`, and `webui/`.

## 4. Environment Setup

### 4.1 Python Environment

The repository provides `requirements.txt` as the unified Python dependency entry point.

Use an isolated virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4.2 Dependency List

`requirements.txt` covers the main runtime dependencies used by the current source code:

- LLM and evaluation interfaces: `structai`, `openai`.
- Academic search and network requests: `requests`, `arxiv`, `urllib3`.
- Markdown and HTML parsing: `beautifulsoup4`, `markdown`.
- Data processing and visualization: `pandas`, `numpy`, `scikit-learn`, `matplotlib`, `Pillow`, `python-Levenshtein`.
- WebUI and benchmark support: `flask`, `flask-cors`, `datasets`.
- Progress display: `tqdm`.

The key dependency is `structai`. This package is not defined inside the repository, but the workflow uses it heavily:

- `structai.LLMAgent`
- `structai.multi_thread`
- `structai.read_pdf`
- `structai.save_file`
- `structai.get_all_file_paths`

If `structai` is missing, the full workflow cannot run. Some smoke tests use fake `structai` objects so that static and local behavior can still be tested without a real API environment.

### 4.3 API Environment Variables

The README shows the following environment variables:

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
export MINERU_TOKEN="your-mineru-api-key"
```

Their roles are:

- `LLM_API_KEY`: API key for the LLM service.
- `LLM_BASE_URL`: Base URL for the LLM service.
- `MINERU_TOKEN`: Token for the MinerU PDF parsing service.

The exact behavior may depend on your installed `structai` version. Before running the full workflow, verify that your `structai` installation is compatible with this repository.

## 5. Core Concepts

### 5.1 Field, Topic, and Table Template

A Manalyzer task is defined by three main inputs:

- `field`: the research field, such as `environment`, `agriculture`, or `atmosphere`.
- `topic_of_interest`: the specific research question, such as `River pollutants`.
- `table_template`: the target table schema for extracted data.

In `workflow/main.py`, these values are currently hard-coded:

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

Note that the variable is named `filed`, not `field`. This is a historical typo. It is part of the current workflow contract and should not be renamed only for style.

### 5.2 Role of the Table Template

The table template tells the model what fields should appear in the final integrated table. Example rows also provide formatting guidance.

A good template should:

- Use clear column names.
- Put units in column names, for example `Content (µg/L)`.
- Include short and realistic example rows.
- Avoid mixing multiple meanings in a single column.

Example:

```markdown
| River | Location | Heavy metals | Content (µg/L) |
|---|---|---|---|
| Tigris River | Turkey | Cu | 40 |
```

This template means that each output row should describe the concentration of one heavy metal in one river location.

## 6. Pipeline Stage Details

`workflow/main.py` runs nine stages in order. Understanding these stages helps debug the full pipeline and identify which module produced each output file.

### 6.1 PaperCollector: Paper Search and Download

File: `agents/paper_collector.py`

Responsibilities:

1. Generate search keyword groups from the user topic.
2. Search papers through arXiv or Crossref.
3. Download PDF files.
4. Write `0_paper_info.json`.

The default search engine is `arxiv`. If `crossref` is used, DOI-based downloading may use the Sci-Hub path. That path depends on external website availability and may have compliance implications. Users should evaluate it before use.

Typical output:

```text
data/<field>/<timestamp>/
├── 0_pdf/
└── 0_paper_info.json
```

Example `0_paper_info.json`:

```json
{
  "00000": {
    "title": "Example Paper Title",
    "url": "https://arxiv.org/pdf/xxxx.xxxxx",
    "pdf_path": "data/environment/2026_0209_185427/0_pdf/00000.pdf"
  }
}
```

### 6.2 PaperParser: PDF Parsing

File: `agents/paper_parser.py`

Responsibilities:

1. Read `0_paper_info.json`.
2. Call `structai.read_pdf(pdf_paths)`.
3. Locate each paper's `*_content_list.json` and `full.md`.
4. Write `1_content_list_info.json`.

This stage depends on PDF parsing support from MinerU or `structai`. If `MINERU_TOKEN` is not configured or the service is unavailable, this stage may fail.

### 6.3 PaperReviewer: Paper Screening

File: `agents/paper_reviewer.py`

Responsibilities:

1. Read each paper's Markdown text.
2. Clean short and invalid content.
3. Score each paper independently:
   - `Topic Relevance`
   - `Feasibility`
4. Score relative relevance within batches:
   - `Relative Score`
5. Compute:
   - `Final Score = (Topic Relevance + Feasibility) * Relative Score`

Output files:

```text
2_paper_score.json
3_selected_paper.json
```

`select_paper(save_dir, 10)` selects the top 10 papers by final score. If fewer papers exist, all available papers may be retained.

### 6.4 TableProcessor: Table and Figure Conversion

File: `agents/table_processor.py`

Responsibilities:

1. Read `3_selected_paper.json`.
2. Traverse each paper's content list.
3. Identify tables, images, and charts.
4. Use a vision LLM to convert tables to Markdown or images to textual descriptions.
5. Write `2_text/<paper_idx>.json` and `4_converted_paper.json`.

This stage strongly affects later extraction quality. If table conversion is inaccurate, the final extracted data will also be less reliable.

### 6.5 DataExtratorWithChecker: Extraction and Feedback Checking

File: `agents/data_extrator_checker.py`

Responsibilities:

1. Collect candidate information from table and text paths.
2. First-level filtering: decide whether each table or section may contain relevant data.
3. Second-level integration: convert relevant data into the user-provided table schema.
4. Check the result using:
   - `Data Accuracy`
   - `Semantic Consistency`
   - `Data Completeness`
   - `Overall Score`
5. If the checker rejects the answer, regenerate the extraction using feedback.

Output files:

```text
3_integrated_table/<paper_idx>.json
5_integrated_table_info.json
```

Each paper usually has two extraction paths:

```json
{
  "table": "...",
  "text": "..."
}
```

If no usable data is found, a value may be `"None"`.

### 6.6 DataMerger: Cross-Paper Data Merge

File: `agents/data_merger.py`

Responsibilities:

1. Read all extracted paper-level tables.
2. Parse Markdown tables.
3. Map extracted columns to the standard columns in the user template.
4. Add a `Reference` column to record the source paper.
5. Use an LLM to normalize numerical fields, for example:
   - Remove thousand separators.
   - Convert percentages to decimals.
   - Average numerical ranges.
   - Convert unprocessable values to `None`.

Output file:

```text
meta_analysis.csv
```

This CSV file is the main structured dataset for later analysis and reporting.

### 6.7 DataAnalyst: Analysis and Visualization

File: `agents/data_analyst.py`

Responsibilities:

1. Read `meta_analysis.csv`.
2. Drop the `Reference` column.
3. Ask the LLM to generate three visualization functions:
   - `clustering(data)`
   - `classification(data)`
   - `regression(data)`
4. Execute the generated code and save figures.

Output files:

```text
4_visualization/clustering.png
4_visualization/classification.png
4_visualization/regression.png
```

Important note: this stage uses `exec(code)` to run LLM-generated Python code. In production-like settings, use restricted permissions, a trusted model, and an isolated runtime.

### 6.8 Reporter: Report Generation

File: `agents/reporter.py`

Responsibilities:

1. Read `meta_analysis.csv`.
2. Read visualization images.
3. Read paper titles as references.
4. Ask the LLM to generate a Markdown Meta-analysis report.

Output file:

```text
meta_analysis_report.md
```

The report attempts to include methods, results, figures, and references.

## 7. Full Run: Command-Line Mode

This section explains how to run the complete Manalyzer pipeline directly through `workflow/main.py`. Command-line mode does not use browser interaction, and is suitable for servers, remote terminals, batch experiments, and one-off debugging.

### 7.1 Direct Run Commands

If dependencies are installed and the task inputs in `workflow/main.py` have already been edited, including `filed`, `topic_of_interest`, and `table_template`, run the following commands from the repository root:

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
export MINERU_TOKEN="your-mineru-api-key"

python workflow/main.py
```

Before a real run, it is recommended to execute the fast smoke tests:

```bash
python -m unittest discover -s tests
python -m compileall -q agents tools utils workflow benchmark webui tests
```

After the run finishes, outputs are written to:

```text
data/<field>/<timestamp>/
```

For example, the current sample task may generate:

```text
data/environment/2026_0209_185427/
```

Use the following command to inspect the latest run directory:

```bash
ls -td data/*/* | head -1
```

The complete command-line sequence is:

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

If you only want to verify that the repository has no obvious static issues without calling external APIs, run only:

```bash
python -m unittest discover -s tests
```

### 7.2 Confirm Runtime Requirements

Before running the full pipeline, check the following requirements:

1. Required dependencies have been installed with `python -m pip install -r requirements.txt`.
2. LLM environment variables are configured:

```bash
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="your-api-base-url"
```

3. The PDF parsing token is configured:

```bash
export MINERU_TOKEN="your-mineru-api-key"
```

4. The current working directory is the repository root. A simple check is:

```bash
pwd
```

The path should look like:

```text
/path/to/Manalyzer
```

5. The selected search and download sources are reachable. The default workflow uses arXiv, so arXiv access is required.

### 7.3 Edit Task Inputs

In command-line mode, task inputs are defined in `workflow/main.py`. Open that file and edit three main parts.

The first input is the research field:

```python
filed = 'environment'
```

This value is used to:

- Create the output directory `data/<field>/<timestamp>/`.
- Fill domain placeholders in multiple agent prompts.
- Identify the field of logs and outputs.

The second input is the research topic:

```python
topic_of_interest = 'River pollutants'
```

This topic is used to:

- Generate search keywords.
- Judge paper relevance.
- Judge whether tables, figures, and text sections contain target data.
- Guide final report generation.

The third input is the target table template:

```python
table_template = """
| River        | Location | Heavy metals | Content (µg/L) |
|--------------|----------|--------------|----------------|
| Tigris River | Turkey   | Cu           | 40             |
| Tigris River | Turkey   | Co           | 10             |
| Tiete River  | Brazil   | Fe           | 915            |
"""
```

The template defines the column structure of the final `meta_analysis.csv`. When editing it, keep the Markdown table complete: header row, separator row, and at least one example row.

### 7.4 Edit Paper Sources and Search Size

The paper collection call in `workflow/main.py` is:

```python
paper_collector(topic_of_interest, paper_list=['EU-wide survey of polar organic persistent pollutants in European river waters'], paper_search_num=1)
```

The arguments mean:

- `paper_list`: a list of known paper titles to search explicitly.
- `paper_search_num`: the number of papers returned for each generated keyword group. Larger values increase download volume and LLM cost.
- To use only keyword search, remove `paper_list` or set it to `None`.
- To use DOI-based downloading, pass `doi_list=[...]` in code, but note that DOI downloading may use the Sci-Hub path and should be used carefully.

Example: keyword search only, two papers per keyword group:

```python
paper_collector(topic_of_interest, paper_list=None, paper_search_num=2)
```

Example: one known title plus one paper per keyword group:

```python
paper_collector(
    topic_of_interest,
    paper_list=['A known important paper title'],
    paper_search_num=1,
)
```

### 7.5 Edit the Number of Selected Papers

After paper review, the workflow calls:

```python
select_paper(save_dir, 10)
```

The value `10` means that the top 10 papers by `Final Score` are selected for extraction. To process all downloaded papers, use:

```python
select_paper(save_dir, -1)
```

Processing more papers significantly increases table conversion, extraction, and report-generation cost.

### 7.6 Run the Complete Pipeline

After editing inputs and configuring environment variables, run from the repository root:

```bash
python workflow/main.py
```

The terminal will print stage logs, and each agent also writes logs under `data/<field>/<timestamp>/log/`. Every run creates a new timestamped directory and does not overwrite previous runs.

### 7.7 Track Progress in Serial Mode

Command-line mode has no browser progress bar. The most reliable way to track progress is to check whether stage outputs exist:

1. `0_paper_info.json`: paper search and download finished.
2. `1_content_list_info.json`: PDF parsing finished.
3. `2_paper_score.json` and `3_selected_paper.json`: review and selection finished.
4. `4_converted_paper.json` and `2_text/`: table and image conversion finished.
5. `5_integrated_table_info.json` and `3_integrated_table/`: data extraction finished.
6. `meta_analysis.csv`: cross-paper data merging finished.
7. Images under `4_visualization/`: analysis and visualization finished.
8. `meta_analysis_report.md`: report generation finished.

### 7.8 Recommended Manual Review After a Full Run

After the full pipeline finishes, do not read only the final report. A more reliable review order is:

1. Open `0_paper_info.json` and check whether downloaded papers are relevant.
2. Open `2_paper_score.json` and inspect whether scores are reasonable.
3. Open `3_selected_paper.json` and confirm that selected papers are not obviously off-topic.
4. Sample `2_text/<paper_idx>.json` and check whether tables and figures were converted correctly.
5. Sample `3_integrated_table/<paper_idx>.json` and compare extracted tables with the original paper.
6. Open `meta_analysis.csv` and check columns, units, numeric formats, and the `Reference` source column.
7. Open `4_visualization/*.png` and confirm that figures are not empty or obviously invalid.
8. Finally read `meta_analysis_report.md` and cross-check it with the intermediate files.

### 7.9 Common Failure Points

Common failure points in command-line full runs include:

- Missing `structai`: the workflow cannot import `LLMAgent`, `read_pdf`, and related objects.
- Missing `MINERU_TOKEN`: PDF parsing fails.
- Incorrect LLM API key or base URL: agent calls fail.
- arXiv, Crossref, or Sci-Hub unavailable: search or download fails.
- Invalid Markdown table template: `DataMerger` cannot parse standard columns correctly.
- Retrieved papers weakly related to the topic: later extraction may produce meaningless data.
- Irregular LLM-generated Markdown tables: merge logic may skip rows or columns.

When debugging, inspect the `log/` directory in the run output first, instead of relying only on the last terminal lines.

## 8. Output Directory Example

A run creates a directory similar to:

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

For debugging, check files in stage order:

1. Missing `0_paper_info.json`: search or download failed.
2. Missing `1_content_list_info.json`: PDF parsing failed.
3. Missing `3_selected_paper.json`: review or selection failed.
4. Missing `4_converted_paper.json`: table or image conversion failed.
5. Missing `5_integrated_table_info.json`: data extraction failed.
6. Missing `meta_analysis.csv`: data merging failed.
7. Missing `meta_analysis_report.md`: report generation failed.

## 9. Visual WebUI Run

The visual WebUI run uses the same Manalyzer pipeline as the command-line full run in Section 7. Paper collection, PDF parsing, paper review, table and figure conversion, data extraction, data merging, analysis visualization, and report generation keep the same stage order.

The difference is the interaction layer. In command-line mode, task inputs are edited directly in `workflow/main.py`. In WebUI mode, `Field`, `Topic of Interest`, and `Table Template` are submitted through a browser form, while logs, output files, and stage progress are displayed on the page. In other words, the WebUI adds a frontend interaction layer; it does not introduce a separate analysis pipeline.

The WebUI is composed of two cooperating processes:

1. `workflow/main_webui.py` runs the background workflow.
2. `webui/weiui.py` runs the Flask web server.

If dependencies have not been installed yet, first run this command from the repository root:

```bash
python -m pip install -r requirements.txt
```

Use two terminals.

Terminal A:

```bash
python workflow/main_webui.py
```

This process:

1. Clears `webui/data/user_input.json`.
2. Creates `webui/data/chat.log`.
3. Creates `webui/data/save_info.json`.
4. Waits for user input from the WebUI.

Terminal B:

```bash
python webui/weiui.py
```

Then open:

```text
http://127.0.0.1:5000
```

The page provides three inputs:

- `Field`
- `Topic of Interest`
- `Table Template`

After clicking Confirm, the WebUI writes:

```text
webui/data/user_input.json
```

The background process then continues the workflow.

## 10. Benchmark Usage

Benchmark scripts are in `benchmark/`.

### 10.1 Extraction

```bash
python benchmark/1_extractor.py
```

This script:

1. Loads the `CoCoOne/Manalyzer` dataset from Hugging Face.
2. Calls the configured model through `utils.eval.EvaluationModel`.
3. Writes extraction results to:

```text
benchmark/results/<model>/<field>/*.json
```

The default field and model are hard-coded in the script, for example:

```python
field = "agriculture"
model = "grok-3"
```

To change field or model, edit those variables.

### 10.2 Scoring

```bash
python benchmark/2_score.py
```

This script reads:

```text
benchmark/results/**/*.json
benchmark/answer.json
```

It then computes hit rates for `level_1`, `level_2`, and `level_3` numeric values.

## 11. Smoke Tests

The repository includes a lightweight `tests/` directory based on Python's standard `unittest` framework.

Run:

```bash
python -m unittest discover -s tests
```

The smoke tests cover:

- Compilation of all Python files.
- Import behavior for lightweight modules.
- Basic behavior of core `utils` functions.
- Static checks that production code does not use bare `except` or runtime `assert`.
- WebUI path contracts.
- Lazy loading of SciHub wrappers.
- Request timeouts in tool modules.
- Regression coverage for newline handling in `DataExtratorWithChecker`.
- Boundary behavior for `PaperParser` and `DataMerger`.
- `requirements.txt` coverage for the current runtime dependency list.

The smoke tests do not call:

- LLM APIs.
- MinerU PDF parsing.
- arXiv.
- Sci-Hub.
- Hugging Face datasets.

After changing workflow code, run at least:

```bash
python -m compileall -q agents tools utils workflow benchmark webui tests
python -m unittest discover -s tests
```

## 12. Common Questions

### 12.1 Why does the full workflow fail with missing `structai`

This usually means `python -m pip install -r requirements.txt` has not been executed in the current Python environment, or it was executed in a different virtual environment. `structai` is not part of this repository's source code, but it is listed in the dependency file. If it is still missing, first confirm that the `python` used to run Manalyzer is the same interpreter used to install dependencies.

### 12.2 Why are some retrieved papers not highly relevant

The default search engine is arXiv. For fields such as environment, medicine, and agriculture, arXiv coverage may be limited. Keyword search can therefore return weakly related papers. `PaperReviewer` attempts to filter them, but it is not perfect.

### 12.3 Why must the final report be manually checked

The report is generated by an LLM from extracted tables, visualizations, and references. Any mistake in earlier stages can propagate into the final report. Formal use requires manual verification against the original papers.

### 12.4 Why does the WebUI require two processes

The current design separates the background workflow from the Flask server. The workflow waits for `webui/data/user_input.json`, while the Flask server writes that file from the web page.

### 12.5 Why do smoke tests not run the full workflow

The full workflow depends on external APIs, network access, PDF parsing, and LLM calls. Those dependencies are expensive and unstable for quick testing. The smoke tests are intended to catch obvious code-quality and contract regressions quickly.

## 13. Minimal Learning Path

To understand the repository efficiently:

1. Read `README.md`.
2. Read `workflow/main.py`.
3. Read the agent files from `agents/paper_collector.py` to `agents/reporter.py`.
4. Inspect example outputs under `data/environment/2026_0209_185427/`.
5. Run:

```bash
python -m unittest discover -s tests
```

6. After installing dependencies with `requirements.txt` and configuring APIs, try:

```bash
python workflow/main.py
```

This sequence lets you understand the workflow before dealing with real external service calls.
