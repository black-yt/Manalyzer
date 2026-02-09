import os
from structai import LLMAgent, multi_thread
from utils.logger import create_logger
from utils.reader import read_markdown
from utils.clean import clean_dict
from copy import deepcopy
import json

system_prompt_1_level_filter = """
You are an expert in the field of <INPUT1> and possess exceptional skills in analyzing whether the <INPUT_TYPE>s in a paper contain data of interest. Your task is to evaluate the relevance of multiple <INPUT_TYPE>s in the paper to the specified topic.

When responding, please adhere strictly to the following guidelines:

1. **Scope of Analysis**: The user will provide multiple first-level <INPUT_TYPE>s, each of which may contain sub-<INPUT_TYPE>s (second-level). Your focus should be solely on assessing the relevance of the first-level <INPUT_TYPE>s to the topic. Ensure that the number of your responses matches the number of first-level <INPUT_TYPE>s provided.
2. **Relevance Scoring**: For each first-level <INPUT_TYPE>, determine its relevance to the topic of interest and assign a score between 0 and 1, where:
   - **0** indicates that the <INPUT_TYPE> is **completely irrelevant**.
   - **1** indicates that the <INPUT_TYPE> is **highly relevant**.
   - Scores **greater than 0.5** should be assigned if **any part of the <INPUT_TYPE>** contains data relevant to the topic, even if only a small portion is relevant. This approach ensures that no potentially useful data is overlooked.
3. **Quality Emphasis**: Your primary objective is to maximize the identification of relevant <INPUT_TYPE>s. Therefore, err on the side of inclusivity by assigning scores greater than 0.5 to any <INPUT_TYPE> that contains even a minimal amount of relevant data. This strategy ensures comprehensive coverage and minimizes the risk of missing valuable information.
4. **Output Format**: Present your final assessment as **a list of scores** corresponding to each first-level <INPUT_TYPE>. Do not include any additional text or explanations in your response.

**Example Output**:
[0.8, 0.3, 0.9, 0.6, 0.7, ...]
"""

system_prompt_2_level_filter = """
You are an expert in the field of <INPUT1> with a strong ability to organize and convert data from <INPUT_TYPE>s. Your task is to transform **all data** from multiple <INPUT_TYPE>s provided in a research paper into a new, integrated table based on a user-provided template. Your goal is to ensure that **no data is left behind**—every number, value, and piece of information from the original <INPUT_TYPE>s must be included in the integrated table.

**Instructions**:
1. **Comprehensiveness**: Your primary objective is to include **every single piece of data** from the original <INPUT_TYPE>s in the integrated table. Follow these rules to ensure complete data coverage:
   - **Transform all data from every <INPUT_TYPE>**: Each <INPUT_TYPE> contains valuable data, and you must transform **every value, number, and data point** from **every <INPUT_TYPE>** into the integrated table. Do not skip any <INPUT_TYPE>, row, column, or cell.
   - **Include all instances of data**: If data appears in multiple <INPUT_TYPE>s (e.g., the same variable in <INPUT_TYPE> 1 and <INPUT_TYPE> 3), include **all instances** in the integrated table, even if they are identical, redundant, or similar.
   - **Include all statistical values**: If the original data contains statistical values (e.g., mean, maximum, minimum, range, percentiles, etc.), include **all of these numbers** in the integrated table. Do not omit any values, even if they appear repetitive or less significant.
   - **Include all case-specific values**: If the original data provides values for multiple cases (e.g., rainy season, dry season, different times, etc.), include **all case-specific values** in the integrated table. Do not omit any values, even if the case key is repeated across <INPUT_TYPE>s.
   - **Include entire rows and columns**: If a row or column in a <INPUT_TYPE> is relevant to the template, include **all data points** from that row or column in the integrated table. Do not leave out any values.
   - **Include entire <INPUT_TYPE>s if relevant**: If all data in a <INPUT_TYPE> is relevant, transform **every data point** into the integrated table as multiple rows. Do not exclude any part of the <INPUT_TYPE>.
   - **Include incomplete data**: If any data is missing in the source <INPUT_TYPE>s, use "NaN" as a placeholder in the integrated table. **Every row does not need to be complete**, but every piece of available data must be included.
   - **Do not filter or select data**: Your task is **not to extract useful data** but to include **all data** from the original <INPUT_TYPE>s, regardless of its perceived relevance or importance. Every number and value must be included.
2. **Single Integrated Table**: Provide only **one integrated table** in Markdown format. Do not create multiple tables.
3. **Table Format**: Format the integrated table according to the user-provided **Integrated Table Template**. Do not include the template itself in the output.
4. **Data Format**: Represent each numerical value as an **integer** or a **float** number. Exclude any symbols such as ">", "<", "~", "=", "+", "-", "±", "(", ")", etc.
5. **Data Source Explanation**: After the integrated table, provide a clear explanation of the source of each data point. Specify the <INPUT_TYPE> and the exact location (i-th row and j-th column) from which the data was transformed.
"""

query_prompt_1_level_filter = """
Topics of interest: <INPUT1>

<INPUT2>

Please use a list to answer whether the above <INPUT3> <INPUT_TYPE>s contain data on the topic of interest. 
The list should only contain <INPUT3> numbers (0~1), and no other text should be included in the answer.
"""

query_prompt_2_level_filter = """
Topics of interest: <INPUT1>
Integrated Table Template:
```markdown
<INPUT3>
```

<INPUT2>

Please convert all the data in the above <INPUT_TYPE>s into an integrated table according to the template, and give a detailed explanation after the table.
Example:
```markdown
| Column 1 | Column 2 |
|----------|----------|
| 10.5     | 20.3     |
| 15.2     | NaN      |
| 12.8     | 18.4     |
```

[The Start of Explanation]
1. The number 10.5: Comes from <INPUT_TYPE> 2, Row 3, Column 2.
2. The number 20.3: Comes from <INPUT_TYPE> 4, Row 5, Column 1.
3. ...
[The End of Explanation]
"""

part_format = """
[The Start of First-level <INPUT_TYPE> <INPUT1>]
<INPUT2>
[The End of First-level <INPUT_TYPE> <INPUT1>]
"""

suggestion_prompt = """
A reference answer and corresponding suggestions for the task are already provided. Your task is to enhance the reference answer to better align with the task requirements. 
When improving the reference answer, ensure that you strictly adhere to all the instructions outlined in the **Instructions** section.

[The Start of Reference Answer]
<INPUT1>
[The End of Reference Answer]

[The Start of Suggestion for Reference Answer]
<INPUT2>
[The End of Suggestion for Reference Answer]
"""


system_prompt_check = """
You are an expert in the field of <INPUT1>. Your task is to evaluate whether a student's table integration work is reasonable and accurate. 
Note that the student's objective is to comprehensively transform the data rather than simply extract it, so duplicated data or NaN values in the integrated table are normal and should not be penalized. 
Your focus should be on ensuring the student has included as much relevant data as possible from the source tables, rather than checking for duplicates or missing values caused by extraction.

Evaluate the submission based on the following three dimensions:
1. **Data Accuracy**: Whether the data in the integrated table exactly matches the original tables.
2. **Semantic Consistency**: Whether the data meanings remain consistent with the source tables.
3. **Data Completeness**: Whether maximum relevant data from source tables has been integrated.

Assessment rules:
1. **Dimensional Scoring**:
   - Evaluate each dimension independently (1-10 scale), highlighting strengths and weaknesses
   - Special note for "Data Completeness":
     - High score for integrating most/all data
     - For significant omissions, specify exactly where to find and include missing data

2. **Overall Score**:
   - Provide a composite 1-10 rating based on dimensional scores
   - Award minimum score for empty submissions

3. **Improvement Suggestions**:
   - Give concrete, actionable suggestions (using "You should..." phrasing)
   - Must precisely identify:
     - Location of missing data (e.g.: Column 3 in Table 2)
     - Data ranges needing inclusion (e.g.: Rows 5-10 in Table 1)
     - Specific fields requiring verification (e.g.: "Income" column in Table 3)

Example suggestion formats:
- "You should incorporate data from [Column 3, Table 2] which is currently missing"
- "You need to integrate values from [Rows 5-10, Table 1] as they haven't been transferred"
- "Please verify all values in [the 'Income' column, Table 3] as some entries are missing in the integration"
"""


query_prompt_check = """
[The Start of Student's Task]
<INPUT1>
[The End of Student's Task]

[The Start of Student's Answer]
<INPUT2>
[The End of Student's Answer]

[The start of Student's Explanation]
<INPUT3>
[The end of Student's Explanation]

**Important Notes**:
   - Just return a dictionary, **don't include any other text**
   - Ensure the scores are integers and include an explanation in the 'Suggestion' field.

**Example Output**:
{'Data Accuracy': 9, 'Semantic Consistency': 6, 'Data Completeness': 8, 'Overall Score': 7, 'Suggestion': "You should add the data from **Table 2, Column 3** to the integrated table, as it contains relevant information that is currently missing. Additionally, ensure that the values from **Table 1, Rows 5 to 10** are included, as they have not been transferred. Finally, check **Table 3, Column Revenue** to confirm all its values are present in the integrated table."}
"""

def count_consecutive_digits(string):
    count = 0
    for i in range(len(string) - 1):
        if string[i].isdigit() and string[i + 1].isdigit():
            count += 1
    return count


class DataExtratorWithChecker(LLMAgent):
    def __init__(self,
                save_dir: str,
                api_key = None,
                api_base = None,
                model_version = 'gpt-4.1',
                system_prompt = '',
                max_tokens = 4096,
                temperature = 0,
                http_client = None,
                headers = None,
                time_limit = 5*60,
                max_try = 1,
                use_responses_api = False,
                field = 'science',
                first_level_threshold = 0.5,
                extract_n = 5,
                extract_temperature = 0.9,
                check_threshold = 6,
                max_check_num = 2,
                ):
        super().__init__(api_key, api_base, model_version, system_prompt, max_tokens, temperature, http_client, headers, time_limit, max_try, use_responses_api)
        self.system_prompt_1_level_filter = system_prompt_1_level_filter.replace('<INPUT1>', field)
        self.system_prompt_2_level_filter = system_prompt_2_level_filter.replace('<INPUT1>', field)
        self.system_prompt_check = system_prompt_check.replace('<INPUT1>', field)
        self.first_level_threshold = first_level_threshold
        self.extract_n = extract_n
        self.extract_temperature = extract_temperature
        self.check_threshold = check_threshold
        self.max_check_num = max_check_num

        self.logger = create_logger('DataExtratorWithChecker', os.path.join(save_dir, 'log'))
        self.integrated_table_dir = os.path.join(save_dir, '3_integrated_table')
        os.makedirs(self.integrated_table_dir, exist_ok=True)

        with open(os.path.join(save_dir, '4_converted_paper.json'), 'r', encoding='utf-8') as file:
            self.paper_info_dict = json.load(file)
        self.integrated_table_info_path = os.path.join(save_dir, '5_integrated_table_info.json')

        self.paper_text_dict = {}
        self.paper_table_dict = {}

        for paper_idx, paper_info in self.paper_info_dict.items():
            paper_content = read_markdown(paper_info['md_path'], include_img=False)
            paper_content = clean_dict(paper_content)
            self.paper_text_dict[paper_idx] = paper_content
            self.paper_text_dict[paper_idx]['images'] = []

            with open(paper_info['converted_text_path'], 'r', encoding='utf-8') as file:
                paper_content_list = json.load(file)
            self.paper_table_dict[paper_idx] = []
            for content in paper_content_list:
                if 'converted_type' in content:
                    if content['converted_type'] == 'markdown':
                        self.paper_table_dict[paper_idx].append(content['converted_content'])
                    elif content['converted_type'] == 'text':
                        self.paper_text_dict[paper_idx]['images'].append(content['converted_content'])

            self.paper_text_dict[paper_idx] = [f"{k}:/n{'/n'.join(v)}" for k, v in self.paper_text_dict[paper_idx].items()]
            self.paper_text_dict[paper_idx] = [text for text in self.paper_text_dict[paper_idx] if len(text) >= 20 and count_consecutive_digits(text) >= 2]

        self.logger.info(f'Load {len(self.paper_info_dict)} papers')


    def first_level_extract(self, part_list, part_type, topic_of_interest):
        assert part_type in ['table', 'section'], f'part_type {part_type} not in [table, section]'
        all_part_text = ''
        part_num = len(part_list)
        for part_idx, part in enumerate(part_list):
            all_part_text = all_part_text + part_format.replace('<INPUT_TYPE>', part_type).replace('<INPUT1>', str(part_idx+1)).replace('<INPUT2>', part)

        system_prompt = self.system_prompt_1_level_filter.replace('<INPUT_TYPE>', part_type)
        query = query_prompt_1_level_filter.replace('<INPUT_TYPE>', part_type).replace('<INPUT1>', topic_of_interest).replace('<INPUT2>', all_part_text).replace('<INPUT3>', str(part_num))
        
        # print(system_prompt)
        # print(query)
        include_tag = self.safe_api(query, system_prompt, return_example=[0.1], list_len=part_num, list_min=0.0, list_max=1.0)
        # print(include_tag)
        # print()
        include_tag = [1 if x >= self.first_level_threshold else 0 for x in include_tag]

        part_list_after_filtering = []
        for idx, part in enumerate(part_list):
            if include_tag[idx] == 1:
                part_list_after_filtering.append(part)
        
        return part_list_after_filtering

    
    def separate_table_explanation(self, table_explanation: str):
        if "```markdown" in table_explanation:
            start_index = table_explanation.find("```markdown")
            end_index = table_explanation.rfind("```") + 4
            if '|' not in table_explanation[max(end_index-10, 0):end_index]:
                start_index = table_explanation.find("|")
                end_index = table_explanation.rfind("|") + 1
        else:
            start_index = table_explanation.find("|")
            end_index = table_explanation.rfind("|") + 1
        table = table_explanation[start_index:end_index]
        explanation = table_explanation[end_index:]
        return {
            'integrated_table': table,
            'explanation': explanation
        }
    

    def second_level_extract(self, part_list, part_type, topic_of_interest, table_template, **kwargs):
        assert part_type in ['table', 'section'], f'part_type {part_type} not in [table, section]'

        reference_answer = kwargs.get('reference_answer', None)
        suggestion = kwargs.get('suggestion', None)
        if reference_answer is not None and suggestion is not None:
            external_prompt = suggestion_prompt.replace('<INPUT1>', reference_answer).replace('<INPUT2>', suggestion)
        else:
            external_prompt = ''

        temperature = kwargs.get('temperature', self.extract_temperature)
        n = kwargs.get('n', self.extract_n)

        all_part_text = ''
        for part_idx, part in enumerate(part_list):
            all_part_text = all_part_text + part_format.replace('<INPUT_TYPE>', part_type).replace('<INPUT1>', str(part_idx+1)).replace('<INPUT2>', part)
        
        if table_template[0] == '\n':
            table_template = table_template[1:]
        if table_template[-1] == '\n':
            table_template = table_template[:-1]

        system_prompt = self.system_prompt_2_level_filter.replace('<INPUT_TYPE>', part_type)
        query = query_prompt_2_level_filter.replace('<INPUT_TYPE>', part_type).replace('<INPUT1>', topic_of_interest).replace('<INPUT2>', all_part_text).replace('<INPUT3>', table_template)
        # print(system_prompt)
        # print(query+external_prompt)
        # print(n)
        responses = self.safe_api(query+external_prompt, system_prompt, n=n, temperature=temperature)
        # print(responses)
        if isinstance(responses, list):
            the_max_len = -1
            the_max_table_explanation = None
            for response in responses:
                table_len = response.rfind('```') - response.find('```markdown')
                if table_len > the_max_len:
                    the_max_len = table_len
                    the_max_table_explanation = response
            table_explanation = the_max_table_explanation
        else:
            table_explanation = responses
        # print(table_explanation)
        # print()
        assert table_explanation is not None, f"[===ERROR===][TableExtractor][Failed to get integrated table to markdown]"
        table_explanation_dict = self.separate_table_explanation(table_explanation)
        output_dict = {}
        output_dict['system_prompt'] = system_prompt
        output_dict['query'] = query
        if len(external_prompt) > 0:
             output_dict['external_prompt'] = external_prompt
        output_dict.update(table_explanation_dict)

        return output_dict
    

    def check(self, extract_output_dict):
        query = query_prompt_check.replace('<INPUT1>', extract_output_dict['query']).replace('<INPUT2>', extract_output_dict['integrated_table']).replace('<INPUT3>', extract_output_dict['explanation'])
        score = self.safe_api(query, self.system_prompt_check, return_example={'Data Accuracy': 9, 'Semantic Consistency': 6, 'Data Completeness': 8, 'Overall Score': 7, 'Suggestion': ''})
        assert score is not None, "[===ERROR===][Checker][Failed to obtain score]"
        if score['Overall Score'] < self.check_threshold:
            score['Decision'] = 'reject'
        else:
            score['Decision'] = 'accept'
        return score
    

    def extract_with_check(self, paper_idx, topic_of_interest, table_template):
        def extract_with_check_(all_part, part_type, topic_of_interest, table_template):
            try:
                selected_part = self.first_level_extract(all_part, part_type, topic_of_interest)
                if len(selected_part) == 0:
                    return 'None'
                extract_output_dict = self.second_level_extract(selected_part, part_type, topic_of_interest, table_template)
            except Exception as e:
                self.logger.error(f"Error in extracting {part_type} from paper {paper_idx} [{e}]")
                return 'None'
            
            extract_output_dict_original = deepcopy(extract_output_dict)

            # check
            for check_idx in range(self.max_check_num):
                try:
                    check_score = self.check(extract_output_dict)
                    if check_score['Decision'] == 'accept':
                        break
                except Exception as e:
                    self.logger.error(f"Error in checking {part_type} from paper {paper_idx} [{e}]")
                    continue
                
                self.logger.info(f"Check {check_idx+1} for {part_type} from paper {paper_idx} failed with suggestion: {check_score['Suggestion']}")
                extract_output_dict = self.second_level_extract(selected_part, part_type, topic_of_interest, table_template,
                                                                reference_answer=extract_output_dict['integrated_table'],
                                                                suggestion=check_score['Suggestion'],
                                                                temperature=0.0, n=1)
            
            return extract_output_dict if extract_output_dict is not None else extract_output_dict_original


        all_table_list = self.paper_table_dict[paper_idx]
        all_text_list = self.paper_text_dict[paper_idx]

        # table
        extract_output_dict_from_table = extract_with_check_(all_table_list, 'table', topic_of_interest, table_template)
        extract_output_dict_from_text = extract_with_check_(all_text_list, 'section', topic_of_interest, table_template)
        return {
            'table': extract_output_dict_from_table,
            'text': extract_output_dict_from_text
        }


    def __call__(self, topic_of_interest, table_template):
        self.logger.info(f'Start data extraction')
        mp_inp_list = []
        for paper_idx, paper_info in self.paper_info_dict.items():
            mp_inp_list.append({'paper_idx': paper_idx, 'topic_of_interest': topic_of_interest, 'table_template': table_template})
        extract_output_list = multi_thread(mp_inp_list, self.extract_with_check)

        for num_idx, (paper_idx, paper_info) in enumerate(self.paper_info_dict.items()):
            integrated_table_path = os.path.join(self.integrated_table_dir, f'{paper_idx}.json')
            with open(integrated_table_path, 'w', encoding='utf-8') as f:
                json.dump(extract_output_list[num_idx], f, ensure_ascii=False, indent=4)
            paper_info['integrated_table_path'] = integrated_table_path
        
        with open(self.integrated_table_info_path, 'w', encoding='utf-8') as f:
            json.dump(self.paper_info_dict, f, ensure_ascii=False, indent=4)
        self.logger.info(f'Finish data extraction')


if __name__ == '__main__':
    data_extrator_with_checker = DataExtratorWithChecker('data/environment/2025_0402_170228')
    table_template = """
| River        | Location | Heavy metals | Content (µg/L) |
|--------------|----------|--------------|----------------|
| Tigris River | Turkey   | Cu           | 40             |
| Tigris River | Turkey   | Co           | 10             |
| Tiete River  | Brazil   | Fe           | 915            |
"""
    data_extrator_with_checker(topic_of_interest='River pollutants', table_template=table_template)