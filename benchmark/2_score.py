import json
from tqdm import tqdm
from utils.file_name import get_all_file_paths

def load_results(all_file_paths):
    results_dict = {}
    for path in tqdm(all_file_paths, desc='Loading results'):
        with open(path, 'r', encoding='utf-8') as file:
            result = json.load(file)
        paper_idx = result['paper_idx']
        extracted_data = result['extracted_data']
        model = path.split('/')[-3]
        field = path.split('/')[-2]
        if model not in results_dict:
            results_dict[model] = {}
        if field not in results_dict[model]:
            results_dict[model][field] = {}
        if paper_idx not in results_dict[model][field]:
            results_dict[model][field][paper_idx] = ''
        
        results_dict[model][field][paper_idx] += (extracted_data + '\n')

    return results_dict

def evaluation_scores(results_dict, answer_dict):
    scores = {}
    for model, fields in results_dict.items():
        scores[model] = {}
        for field, papers in fields.items():
            scores[model][field] = {'level_1': {'hit': 0, 'total': 0}, 'level_2': {'hit': 0, 'total': 0}, 'level_3': {'hit': 0, 'total': 0}}
            for paper_idx, extracted_data in papers.items():
                answer = answer_dict[paper_idx]
                for level in ['level_1', 'level_2', 'level_3']:
                    # if level in answer:
                    scores[model][field][level]['total'] += len(answer[level])
                    for num in answer[level]:
                        if num in extracted_data:
                            scores[model][field][level]['hit'] += 1
            for level in ['level_1', 'level_2', 'level_3']:
                scores[model][field][level]['hit_rate'] = f"{scores[model][field][level]['hit']/scores[model][field][level]['total']*100:05.2f}%"
    return scores

def print_scores(scores):
    print('|                                        |           atmosphere           |          agriculture           |          environment           |')
    print('|model                                   |level_1   |level_2   |level_3   |level_1   |level_2   |level_3   |level_1   |level_2   |level_3   |')
    print('|----------------------------------------|----------|----------|----------|----------|----------|----------|----------|----------|----------|')
    for model, fields in scores.items():
        row = '|'+f"{model:<40}" + '|'
        for field in ['atmosphere', 'agriculture', 'environment']:
            for level in ['level_1', 'level_2', 'level_3']:
                if field in fields:
                    row += f"{fields[field][level]['hit_rate']:<10}"
                else:
                    row += f"{'N/A':<10}"
                row += '|'
        print(row)

result_dir = 'benchmark/results'
all_file_paths = get_all_file_paths(result_dir, suffix='.json')
results_dict = load_results(all_file_paths)

answer_path = 'benchmark/answer.json'

with open(answer_path, 'r', encoding='utf-8') as file:
    answer_dict = json.load(file)

scores = evaluation_scores(results_dict, answer_dict)

print_scores(scores)