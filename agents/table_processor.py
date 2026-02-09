import os
from structai import LLMAgent, multi_thread
from utils.logger import create_logger
import json
import base64


def get_image_info(x, image_path_prefix):
    """
    {
        "type": "image",
        "img_path": "nwp_predictions/mmearth/meta_data/v0/md/images/f5def6d72e7dbfe47ada87d0bc9084997c67f989011db77a255d1817a33fe86b.jpg",
        "img_caption": [
            "FIG. 1. Geological map indicating fault zones and locked segments in Himalaya. "
        ],
        "img_footnote": [],
        "page_idx": 1
    },
    """
    if x['type'] == 'image':
        return {
            'path': os.path.join(image_path_prefix, x['img_path']),
            'caption': ' '.join(x['image_caption']),
            'footnote': ' '.join(x['image_footnote']),
            'in_type': 'chart',
        }

    if x['type'] == 'table':
        return {
            'path': os.path.join(image_path_prefix, x['img_path']),
            'caption': ' '.join(x['table_caption']),
            'footnote': ' '.join(x['table_footnote']),
            'in_type': 'table',
        }


def get_table_image_list(content_list, image_path_prefix):
    clean_list = []
    for part_idx, part in enumerate(content_list):
        if part['type'] == 'text' or part['type'] == 'equation' or 'img_path' not in part or len(part['img_path']) == 0:
            continue
        image_info = get_image_info(part, image_path_prefix)
        # context
        image_info['context'] = ''
        i = part_idx - 1
        j = part_idx + 1
        while i >= 0:
            if content_list[i]['type'] == 'text' and len(content_list[i]['text']) > 10:
                image_info['context'] = content_list[i]['text'] + image_info['context'] + '\n'
                break
            i -= 1
        
        while j < len(content_list):
            if content_list[j]['type'] == 'text' and len(content_list[j]['text']) > 10:
                image_info['context'] = image_info['context'] + '\n' + content_list[j]['text']
                break
            j += 1
        
        for k, v in image_info.items():
            if len(v.strip()) == 0:
                image_info[k] = None

        clean_list.append(image_info)
    
    return clean_list


system_prompt_table = """
You are an expert in the field of <INPUT1>, and you are good at converting the table in the paper from the image format to markdown text. 
Please convert the following jpg table into markdown text.

When replying, please strictly follow the following rules:
1. Ensure that the converted data matches the original data in both values and units, clearly indicating the units.
2. Preserve the original format of the table.
3. If there are multiple tables in the image, convert each one separately.
4. For each table, give its title to reflect the content of the table.
5. For each table, provide a footnote describing the full name of each row and column.
"""


system_prompt_chart = """
You are an expert in the field of <INPUT1> and are good at converting charts in papers from image format to markdown table text.
Please convert the following jpg chart into markdown table text.

When replying, please strictly follow the following rules:
1. Ensure that the converted data matches the original data in both values and units, clearly indicating the units.
2. If there are multiple charts in the image, please convert them into multiple tables respectively.
3. If there are multiple data in one chart, please list them in the corresponding table respectively.
4. For each table, give its title to reflect the content of the table.
5. For each table, provide a footnote describing the full name of each row and column.
"""

query_prompt_table = """
Below is the relevant information of a table from a paper. Please convert this table to text.

<INPUT1>

<INPUT2>

<INPUT3>

Note that your reply only needs three parts: the markdown table, the title, and the footnote.
Example:
```markdown
| Date       | Precipitation (mm)  | Type          |
|------------|---------------------|---------------|
| 2023-01-01 | 5.0                 | Rain          |
| 2023-01-02 | 12.3                | Rain          |
| 2023-01-03 | 0.0                 | None          |
| 2023-01-04 | 8.5                 | Rain          |
| 2023-01-05 | 15.0                | Snow/Rain Mix |
```

[The Start of Title]
Precipitation Records in the New York Area. 
[The End of Title]

[The Start of Footnote]
Date: The date when the precipitation was recorded, in the format of YYYY-MM-DD (year-month-day).
Precipitation (mm): The amount of precipitation on this date, in millimeters. The amount of precipitation reflects the intensity of the precipitation.
Type: The type of precipitation, describing the nature of the precipitation on this date, such as rain, snow, or mixed precipitation.
[The End of Footnote]
"""


query_prompt_chart = """
Below is the relevant information of a chart from a paper. Please convert this chart to text.

<INPUT1>

<INPUT2>

<INPUT3>

Note that your reply only needs three parts: the markdown table, the title, and the footnote.
Example 1:
[The Start of Table]
```markdown
| Date       | Precipitation (mm)  | Type          |
|------------|---------------------|---------------|
| 2023-01-01 | 5.0                 | Rain          |
| 2023-01-02 | 12.3                | Rain          |
| 2023-01-03 | 0.0                 | None          |
| 2023-01-04 | 8.5                 | Rain          |
| 2023-01-05 | 15.0                | Snow/Rain Mix |
```
[The End of Table]

[The Start of Title]
Precipitation Records in the New York Area. 
[The End of Title]

[The Start of Footnote]
Date: The date when the precipitation was recorded, in the format of YYYY-MM-DD (year-month-day).
Precipitation (mm): The amount of precipitation on this date, in millimeters. The amount of precipitation reflects the intensity of the precipitation.
Type: The type of precipitation, describing the nature of the precipitation on this date, such as rain, snow, or mixed precipitation.
[The End of Footnote]


Please convert images into markdown tables if possible. If the image cannot be converted to a markdown table, please describe the contents of the picture point by point.
Start with "1. xxx" directly, without any other text.
Example 2:
1. The Nainital region is marked on the map and may be an important geological sampling site.
2. There is a small inset in the upper right corner of the map showing the larger geographic location in relation to Nainital.
3. xxx
"""


class TableProcessor(LLMAgent):
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
                field = 'science',
                ):
        super().__init__(api_key, api_base, model_version, system_prompt, max_tokens, temperature, http_client, headers, time_limit, max_try, use_responses_api)
        self.system_prompt_table = system_prompt_table.replace('<INPUT1>', field)
        self.system_prompt_chart = system_prompt_chart.replace('<INPUT1>', field)

        self.logger = create_logger('TableProcessor', os.path.join(save_dir, 'log'))
        self.converted_text_save_dir = os.path.join(save_dir, '2_text')
        os.makedirs(self.converted_text_save_dir, exist_ok=True)

        with open(os.path.join(save_dir, '3_selected_paper.json'), 'r', encoding='utf-8') as file:
            self.paper_info_dict = json.load(file)
        
        self.converted_paper_info_path = os.path.join(save_dir, '4_converted_paper.json')
        
        self.table_image_list = []
        for paper_idx, paper_info in self.paper_info_dict.items():
            image_path_prefix = os.path.dirname(paper_info['content_list_path'])
            with open(paper_info['content_list_path'], 'r', encoding='utf-8') as file:
                paper_content_list = json.load(file)
            self.table_image_list = self.table_image_list + get_table_image_list(paper_content_list, image_path_prefix)
        self.logger.info(f'{len(self.table_image_list)} tables (or images) from {len(self.paper_info_dict)} papers need to be processed')
    
    def convert_to_markdown(self, path, caption:str=None, footnote:str=None, in_type:str=None, context:str=None):
        if in_type == 'table':
            system_prompt = self.system_prompt_table
            query = query_prompt_table

        elif in_type == 'chart':
            system_prompt = self.system_prompt_chart
            query = query_prompt_chart

        if caption is not None:
            caption_text = f'[The Start of Caption]\n' + caption + f'\n[The End of Caption]'
            query = query.replace('<INPUT1>', caption_text)
        else:
            query = query.replace('<INPUT1>', '')
        
        if footnote is not None:
            footnote_text = f'[The Start of Footnote]\n' + footnote + f'\n[The End of Footnote]'
            query = query.replace('<INPUT2>', footnote_text)
        else:
            query = query.replace('<INPUT2>', '')

        if context is not None:
            context_text = f'[The Start of Context]\n' + context + f'\n[The End of Context]'
            query = query.replace('<INPUT3>', context_text)
        else:
            query = query.replace('<INPUT3>', '')
        
        # print(path)
        # print(system_prompt)
        # print(query)
        # print()
        table_md = self.safe_api(query, system_prompt=system_prompt, return_dict=False, image_paths=[path])
        assert table_md is not None, f"[===ERROR===][TableManager][Failed to convert images to markdown][{path}]"
        if 'markdown' in table_md:
            return {
                'in_type': in_type,
                'out_type': 'markdown',
                'output': table_md
            }
        else:
            return {
                'in_type': in_type,
                'out_type': 'text',
                'output': table_md
            }
    

    def __call__(self):
        self.logger.info('Start converting tables or images to markdown')
        self.markdown_list = multi_thread(self.table_image_list, self.convert_to_markdown)
        
        self.path2markdown_dict = {}
        for table_image_idx, table_image_info in enumerate(self.table_image_list):
            self.path2markdown_dict[table_image_info['path']] = self.markdown_list[table_image_idx]
        
        for paper_idx, paper_info in self.paper_info_dict.items():
            image_path_prefix = os.path.dirname(paper_info['content_list_path'])
            with open(paper_info['content_list_path'], 'r', encoding='utf-8') as file:
                paper_content_list = json.load(file)
            paper_content_list_converted = []
            for content in paper_content_list:
                include_tag = True
                if 'img_path' in content and len(content['img_path']) > 0:
                    image_path = os.path.join(image_path_prefix, content['img_path'])
                    if image_path not in self.path2markdown_dict:
                        include_tag = False # image_path为""的情况是不会处理的，因此也不在 path2markdown_dict 中
                    else:
                        convert_to_markdown_output = self.path2markdown_dict[image_path]
                        if isinstance(convert_to_markdown_output, dict) and 'out_type' in convert_to_markdown_output and 'output' in convert_to_markdown_output:
                            content['converted_type'] = convert_to_markdown_output['out_type']
                            content['converted_content'] = convert_to_markdown_output['output']
                        else:
                            include_tag = False # 一些情况下，图片无法转换成markdown，或者image_path为""（可能是MinerU的问题），此时self.path2markdown_dict[image_path]为None，不要放入
                if include_tag:
                    paper_content_list_converted.append(content)
            
            converted_text_path = os.path.join(self.converted_text_save_dir, f'{paper_idx}.json')
            self.paper_info_dict[paper_idx]['converted_text_path'] = converted_text_path
            with open(self.converted_paper_info_path, 'w', encoding='utf-8') as f:
                json.dump(self.paper_info_dict, f, ensure_ascii=False, indent=4)
            with open(converted_text_path, 'w', encoding='utf-8') as f:
                json.dump(paper_content_list_converted, f, ensure_ascii=False, indent=4)
        
        self.logger.info(f'Saved converted paper info in {self.converted_paper_info_path}')
        self.logger.info(f'Saved converted text in {self.converted_text_save_dir}')


if __name__ == '__main__':
    save_dir = 'data/environment/2025_0402_170228'
    table_processor = TableProcessor(save_dir)
    table_processor()