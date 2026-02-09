import os
from structai import LLMAgent, multi_thread
from utils.logger import create_logger
import json
import pandas as pd
from io import StringIO
import Levenshtein


system_prompt = """
Please process the following list of dictionaries to standardize numerical data fields according to these specifications:

1. **Numerical Data Transformation Rules**:
   - Remove thousand separators (e.g., convert "1,000" to 1000)
   - Convert percentages to decimal form (e.g., convert "35%" to 0.35)
   - For numerical ranges, compute the average (e.g., convert "10%~15%" to 0.125)
   - For mixed-format entries containing multiple numbers, compute the average (e.g., convert "32%,0.5" to 0.41)
   
   **Critical Requirement**: 
   - Each numerical field must be convertible to a Python float using float() without errors
   - No field should contain multiple numbers or non-numeric characters after processing

2. **Non-Numerical Data Handling**:
   - Preserve all text fields exactly as-is
   - Maintain original dictionary keys without modification
   - Replace non-convertible entries with "None"

3. **Output Specifications**:
   - Return a complete list of dictionaries with identical structure **without any additional text**
   - Process only numerical fields while preserving all other content
   - Include all original entries without omission

4. **Quality Assurance**:
   - Verify that all text fields remain unchanged
   - Ensure dictionary keys are preserved exactly
   - Confirm all processed numerical fields are valid Python floats

**Example Transformation**:

Input:
```python
[
    {'Content (µg/L)': '35%', ...},
    {'Content (µg/L)': '32%,0.5', ...},
    {'Content (µg/L)': '1800-2000 (kg/ha)', ...}
]
```

Output:
```python
[
    {'Content (µg/L)': 0.35, ...},
    {'Content (µg/L)': 0.41, ...},
    {'Content (µg/L)': 1900.0, ...}
]
```

**Special Cases**:
- Convert "declined" to "None"
- Convert empty strings to "None"
- Convert mixed text/number to "None"
- Convert multiple unprocessable numbers to "None"

Please apply these transformations rigorously while maintaining all non-numerical data in its original form. The output must be a complete list of dictionaries with the same structure as the input.
"""

query_prompt = """
[The Start of the List of Dictionaries]
<INPUT>
[The End of the List of Dictionaries]

"""

class DataMerger(LLMAgent):
    def __init__(self,
                save_dir: str,
                api_key = None,
                api_base = None,
                model_version = 'gemini-3-flash-preview-nothinking',
                system_prompt = '',
                max_tokens = 4096,
                temperature = 0,
                http_client = None,
                headers = None,
                time_limit = 5*60,
                max_try = 1,
                use_responses_api = False,
                ):
        super().__init__(api_key, api_base, model_version, system_prompt, max_tokens, temperature, http_client, headers, time_limit, max_try, use_responses_api)
        self.logger = create_logger('DataMerger', os.path.join(save_dir, 'log'))

        with open(os.path.join(save_dir, '5_integrated_table_info.json'), 'r', encoding='utf-8') as file:
            self.paper_info_dict = json.load(file)
        self.merge_table_path = os.path.join(save_dir, 'meta_analysis.csv')
        
        self.integrated_table_list = []
        for paper_id, paper_info in self.paper_info_dict.items():
            with open(paper_info['integrated_table_path'], 'r', encoding='utf-8') as file:
                integrated_table = json.load(file)
            try:
                self.integrated_table_list.append((paper_id, integrated_table['table']['integrated_table']))
            except:
                pass
            try:
                self.integrated_table_list.append((paper_id, integrated_table['text']['integrated_table']))
            except:
                pass
        self.logger.info(f'Loaded {len(self.integrated_table_list)} integrated tables')
    

    def get_merge_integrated_table(self, table_template):
        table_template_pd = pd.read_csv(StringIO(table_template), sep='|', skipinitialspace=True)
        table_template_pd = table_template_pd.iloc[1:, 1:-1]
        table_template_column = []
        for column in table_template_pd.columns.tolist():
            table_template_column.append(column.strip())
        table_template_column.append('Reference')
        merge_df = pd.DataFrame(columns=table_template_column)

        for title, integrated_table in self.integrated_table_list:
            integrated_table = integrated_table[integrated_table.find('|'):integrated_table.rfind('|')+1]
            integrated_table_pd = pd.read_csv(StringIO(integrated_table), sep='|', skipinitialspace=True, engine='python', on_bad_lines='skip')
            integrated_table_pd = integrated_table_pd.iloc[1:, 1:-1]

            column_after_check = []
            column_including = []
            for column_from_extrator in integrated_table_pd.columns.tolist():
                column_from_extrator = column_from_extrator.strip()
                for standard_column in table_template_column:
                    if standard_column == column_from_extrator or len(standard_column) > 5 and Levenshtein.distance(standard_column.lower(), column_from_extrator.lower()) <= 2:
                        column_from_extrator = standard_column
                        column_including.append(standard_column)
                        break
                column_after_check.append(column_from_extrator)
            integrated_table_pd.columns = column_after_check

            integrated_table_pd = integrated_table_pd[column_including]
            integrated_table_pd['Reference'] = title
            merge_df = pd.concat([merge_df, integrated_table_pd], ignore_index=True)

        return merge_df
    

    def refine_table(self, merge_integrated_table, max_try=3):
        merge_integrated_table_dict_list = merge_integrated_table.to_dict(orient='records')
        mp_inp_list = []
        batch_size = 20
        split_list = [merge_integrated_table_dict_list[i:i + batch_size] for i in range(0, len(merge_integrated_table_dict_list), batch_size)]
        for part in split_list:
            query = query_prompt.replace('<INPUT>', json.dumps(part))
            mp_inp_list.append({'query': query, 'system_prompt': system_prompt, 'return_example': []})

        for try_idx in range(max_try):
            try:
                refined_table = multi_thread(mp_inp_list, self.safe_api)
                refined_table = [item for sublist in refined_table for item in sublist]

                merge_integrated_table = pd.DataFrame(refined_table)
                break
            except:
                self.logger.error(f'Error in refining table, try {try_idx + 1}')
                
        return merge_integrated_table


    def __call__(self, table_template):
        merge_integrated_table = self.get_merge_integrated_table(table_template)
        self.logger.info(f'Merged integrated table shape: {merge_integrated_table.shape}')
        
        self.logger.info(f'start refining table')
        merge_integrated_table = self.refine_table(merge_integrated_table)
        self.logger.info(f'Refined integrated table shape: {merge_integrated_table.shape}')

        merge_integrated_table.to_csv(self.merge_table_path, index=False)
        self.logger.info(f'Saved merged integrated table to {self.merge_table_path}')



if __name__ == '__main__':
    save_dir = 'data/environment/2025_0402_170228'
    data_merger = DataMerger(save_dir)
    table_template = """
| River        | Location | Heavy metals | Content (µg/L) |
|--------------|----------|--------------|----------------|
| Tigris River | Turkey   | Cu           | 40             |
| Tigris River | Turkey   | Co           | 10             |
| Tiete River  | Brazil   | Fe           | 915            |
"""
    data_merger(table_template)