import os
import json
from utils.eval import EvaluationModel, field_dict
from structai import multi_thread
from datasets import load_dataset


api_key = os.environ.get("LLM_API_KEY")
base_url = os.environ.get("LLM_BASE_URL")

# field = "atmosphere"
field = "agriculture"
# field = "environment"

# model = 'gpt-4o'
# model = 'gemini-1.5-pro'
# model = 'gemini-2.0-flash'
# model = 'google/gemini-2.5-pro-preview-03-25'
# model = 'claude-3-5-haiku-20241022'
# model = 'claude-3-7-sonnet-20250219'
# model = 'llama-3.2-11b-vision-instruct'
# model = 'Qwen/Qwen2.5-VL-32B-Instruct'#'Qwen2.5-VL-32B-Instruct'
# model = 'Qwen/Qwen2.5-VL-72B-Instruct'#qwen2.5-vl-72b-instruct
# model = 'deepseek-ai/deepseek-vl2'
model = 'grok-3'
# model = 'gpt-4-vision-preview'

save_dir = 'benchmark/results'

os.makedirs(os.path.join(save_dir, model.split('/')[-1], field), exist_ok=True)

field_info = field_dict[field]
for k, v in field_info.items():
    print(f'{k}\n{v}\n')

eval_model = EvaluationModel(field_info['field'], field_info['topic_of_interest'], field_info['required_data'], api_key=api_key, base_url=base_url, model=model)

ds = load_dataset("CoCoOne/Manalyzer", split=field)

def save_result(idx, total, **kwargs):
    save_path = os.path.join(save_dir, model.split('/')[-1], field, f'{idx+1:04}_of_{total:04}.json')
    if os.path.exists(save_path):
        return
    try:
        prompts = eval_model.get_prompt(kwargs['text_or_caption'])
        extracted_data = eval_model.get_response(**prompts, image=kwargs['table_or_image'])
        if extracted_data == 'Error in response':
            print(f"Error in response for index {idx}")
            return
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump({'paper_idx': kwargs['paper_idx'], 'extracted_data': extracted_data}, f, ensure_ascii=False, indent=4)
        return
    except Exception as e:
        print(f"Error processing index {idx}: {e}")
        return

mp_inp_list = []
for idx, item in enumerate(ds):
    mp_inp_list.append({'idx': idx, 'total': len(ds), 'text_or_caption': item['text_or_caption'], 'table_or_image': item['table_or_image'], 'paper_idx': item['paper_idx']})

print(f'start evaluating {model}...')
multi_thread(mp_inp_list, save_result)