import os
import json
from structai import LLMAgent, multi_thread
from utils.logger import create_logger
from utils.reader import read_markdown
from utils.clean import clean_dict
from utils.knapsack import knapsack
from tqdm import tqdm

paragraph_score_system_prompt = """
Please give the following paragraph a score to indicate the value of academic analysis. 
If the content of a paragraph is all general descriptive text, it is considered low value. 
Otherwise, it is given a high score. The score must be an integer from 0 to 10. 
You only need to give a single number without any other text, for example:
8
"""

paragraph_score_query = """
[The Start of the Paragraph]
<INPUT1>
[The End of the Paragraph]

Please rate the academic value of this paragraph and give a single number (0~10)
"""


example_score = {'Topic Relevance': 9, 'Feasibility': 8}

comparative_review_system_prompt = """
You are an expert in the field of <INPUT1> and are good at literature analysis.
Please judge whether the following papers are relevant to the user's topic of interest.

When replying, please strictly follow the following rules:
1. For each paper, please use a real number between 0 and 1 to indicate whether it is relevant to the topic of interest, where 1 means very relevant and 0 means completely irrelevant.
Please do not give other responses.
2. When judging whether it is relevant, please follow every requirement put forward by the user in the topic of interest (including location, time, etc.).
3. Please express the final answer in the form of a list, and **do not use other words to respond**.
Example:
[0.8, 0.9, 0.6, 0.1, ...]
"""

independent_review_system_prompt = """
You are a professional reviewer, your professional field is <INPUT1>, please review the following paper and rate it.
You'll need to assess the response on the following dimensions: Topic Relevance and Feasibility.
Evaluate the paper on different dimensions, pointing out its strengths or weaknesses in each dimension and assigning a score of 1 to 10 for each.

In general, the higher the quality of the paper and the more closely it follows the user requirements, the higher the score will be. Papers that do not meet the user requirements will receive lower scores.

Scoring rules:
Topic Relevance
Scores 1-2 when the paper is not relevant to the user's needs.
Scores 3-4 when the paper belongs to the same field as the topic that the user is interested in, but there is no direct connection.
Scores 5-6 when the paper is related to the topic that the user is concerned about, but does not meet the specific requirements (such as time, place, method).
Scores 7-8 when the paper is closely related to the topic of interest to the user and meets most requirements (such as time, location, and method).
Scores 9-10 when the paper is strongly related to the topic that the user is interested in and meets all requirements (such as time, location, and method).

Feasibility
Scores 1-2 when the paper is not supported by any experiments or data.
Scores 3-4 when the paper has little experimental or data support.
Scores 5-6 when there are some experiments and data in the paper, but they are not complete and sufficient.
Scores 7-8 when the paper provides sufficient experiments and data, and is reproducible.
Scores 9-10 when the experiments and data in the paper are very complete, including experimental details and data descriptions, which can serve as the basis for subsequent work.
"""

comparative_review_query_prompt = """
Topics of interest: <INPUT1>

<INPUT2>

Please use a list to answer the above <INPUT3> papers that are relevant to the topic of interest.
The list should only contain <INPUT3> numbers (0~1), no other text should be included in the answer. \n
"""

independent_review_query_prompt = """
Topics of interest: <INPUT1>

[The Start of the Paper]
<INPUT2>
[The End of the Paper]

**Important Notes**:
   - Just return a dictionary, **don't include any other text**
   - Ensure the scores are integers

**Example Output**:
{'Topic Relevance': 9, 'Feasibility': 8}.\n
"""


text_format = """
Text subtitle: <INPUT1>
Text content: <INPUT2>

"""

class PaperReviewer(LLMAgent):
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
                batch_size = 20,
                use_paragraph_score = False,
                max_paragraph_length = 10_000,
                ):
        super().__init__(api_key, api_base, model_version, system_prompt, max_tokens, temperature, http_client, headers, time_limit, max_try, use_responses_api)
        self.comparative_review_system_prompt = comparative_review_system_prompt.replace('<INPUT1>', field)
        self.independent_review_system_prompt = independent_review_system_prompt.replace('<INPUT1>', field)
        self.batch_size = batch_size
        self.use_paragraph_score = use_paragraph_score
        self.max_paragraph_length = max_paragraph_length

        with open(os.path.join(save_dir, '1_content_list_info.json'), 'r', encoding='utf-8') as file:
            self.content_list_info_dict = json.load(file)

        self.score_json_path = os.path.join(save_dir, '2_paper_score.json')
        self.logger = create_logger('PaperReviewer', os.path.join(save_dir, 'log'))
    

    def paragraph_score(self, paragraph):
        query = paragraph_score_query.replace('<INPUT1>', paragraph)
        score = self.safe_api(query, paragraph_score_system_prompt)
        try:
            score = int(score)
        except:
            score = 10
        return score
    
    def paragraph_score_filter(self, paper_dict):
        self.logger.info(f'Filter paragraphs by score, before: {len(paper_dict)}')
        items = []
        for part, paragraph_list in paper_dict.items():
            paragraph = '\n'.join(paragraph_list)
            score = self.paragraph_score(paragraph)
            items.append({'weight': len(paragraph), 'value': score})
        max_value, selected_items = knapsack(items, self.max_paragraph_length)
        paper_dict_selected = {}
        for paer_idx, (part, paragraph_list) in enumerate(paper_dict.items()):
            if selected_items[paer_idx] == 1:
                paper_dict_selected[part] = paragraph_list
        self.logger.info(f'Filter paragraphs by score, after: {len(paper_dict_selected)}')
        return paper_dict_selected

    def paper2text(self, paper_dict: dict, abstract_max_len=10000, intro_max_len=10000, max_len=50000, max_part=-1, use_paragraph_score=False):
        if self.use_paragraph_score and use_paragraph_score:
            paper_dict = self.paragraph_score_filter(paper_dict)

        if max_part == -1:
            max_part = len(paper_dict)
        part_max_len = max_len // max_part
        paper_text = ''
        for part_idx, (part, paragraph_list) in enumerate(paper_dict.items()):
            if (part_idx+1) > max_part:
                break

            if 'reference' in part.lower() or 'acknowledgement' in part.lower():
                continue
            
            paragraph_list_wo_img = []
            for p in paragraph_list:
                if '.jpg' not in p:
                    paragraph_list_wo_img.append(p)
            paragraph = '\n'.join(paragraph_list_wo_img)
            if 'abstract' in part.replace(" ", "").lower():
                paragraph_select = paragraph[:abstract_max_len]
            elif 'intro' in part.replace(" ", "").lower():
                paragraph_select = paragraph[:intro_max_len]
            else:
                paragraph_select = paragraph[:part_max_len]

            paper_text = paper_text + text_format.replace('<INPUT1>', part).replace('<INPUT2>', paragraph_select)
        return paper_text
    

    def comparative_review(self, paper_list, topic_of_interest):
        paper_list_text = ''
        for paper_idx, paper_dict in enumerate(paper_list):
            paper_text = self.paper2text(paper_dict, abstract_max_len=5000, intro_max_len=1000, max_len=3000, max_part=3)
            paper_text = f'[The Start of the Paper {paper_idx+1}]\n' + paper_text + f'\n[The End of the Paper {paper_idx+1}]\n\n'
            paper_list_text = paper_list_text + paper_text
        query = comparative_review_query_prompt.replace('<INPUT1>', topic_of_interest).replace('<INPUT2>', paper_list_text).replace('<INPUT3>', str(len(paper_list)))
        # print(query)
        scores = self.safe_api(query, self.comparative_review_system_prompt, return_example=[0.8], list_len=len(paper_list), list_min=0.0, list_max=1.0)
        if scores is None:
            self.logger.error('Failed to obtain comparative score')
            raise Exception('Failed to obtain comparative score')
        return scores


    def independent_review(self, paper_dict, topic_of_interest):
        paper_text = self.paper2text(paper_dict, use_paragraph_score=True)
        query = independent_review_query_prompt.replace('<INPUT1>', topic_of_interest).replace('<INPUT2>', paper_text)
        # print(query)
        score = self.safe_api(query, self.independent_review_system_prompt, return_example=example_score)
        if score is None:
            self.logger.error('Failed to obtain independent score')
            raise Exception('Failed to obtain independent score')
        return score
    

    def __call__(self, topic_of_interest):
        paper_content_dict = {}
        for paper_idx, paper_info in self.content_list_info_dict.items():
            paper_content = read_markdown(paper_info['md_path'], include_img=True)
            paper_content = clean_dict(paper_content)
            paper_content_dict[paper_idx] = paper_content
        self.logger.info(f'Read {len(paper_content_dict)} papers')
        
        paper_score_dict = {}
        
        # independent review
        self.logger.info(f'Start independent review')
        mp_inp_list = []
        for paper_idx, paper_content in paper_content_dict.items():
            mp_inp_list.append({'paper_dict': paper_content, 'topic_of_interest': topic_of_interest})
        scores = multi_thread(mp_inp_list, self.independent_review)
        for num_idx, (paper_idx, paper_content) in enumerate(paper_content_dict.items()):
            paper_score_dict[paper_idx] = scores[num_idx] 
        
        # comparative review
        self.logger.info(f'Start comparative review')
        batch_paper_idx = []
        batch_paper_content = []
        for num_idx, (paper_idx, paper_content) in enumerate(tqdm(paper_content_dict.items())):
            batch_paper_idx.append(paper_idx)
            batch_paper_content.append(paper_content)
            if len(batch_paper_idx) >= self.batch_size or num_idx == len(paper_content_dict) - 1:
                scores = self.comparative_review(batch_paper_content, topic_of_interest)
                for i in range(len(batch_paper_idx)):
                    paper_idx = batch_paper_idx[i]
                    paper_score_dict[paper_idx]['Relative Score'] = scores[i]
                batch_paper_idx = []
                batch_paper_content = []
        
        for paper_idx, paper_score in paper_score_dict.items():
            paper_score_dict[paper_idx]['Final Score'] = (sum(paper_score.values()) - paper_score['Relative Score'])*paper_score['Relative Score']
        
        for paper_idx, paper_score in paper_score_dict.items():
            paper_score_dict[paper_idx].update(self.content_list_info_dict[paper_idx])
            
        with open(self.score_json_path, 'w', encoding='utf-8') as f:
            json.dump(paper_score_dict, f, ensure_ascii=False, indent=4)
        self.logger.info(f'Reviewed {len(paper_score_dict)} papers')


def select_paper(save_dir, paper_num=-1):
    paper_score_path = os.path.join(save_dir, '2_paper_score.json')
    selected_paper_save_path = os.path.join(save_dir, '3_selected_paper.json')

    with open(paper_score_path, 'r', encoding='utf-8') as file:
        paper_score = json.load(file)

    if paper_num == -1:
        selected_paper = paper_score
    else:
        final_score = sorted([v['Final Score'] for k, v in paper_score.items()], reverse=True)
        final_score_th = final_score[paper_num-1] if paper_num <= len(final_score) else final_score[-1]
        selected_paper = {}
        for k, v in paper_score.items():
            if v['Final Score'] >= final_score_th:
                selected_paper[k] = v

    with open(selected_paper_save_path, 'w', encoding='utf-8') as f:
        json.dump(selected_paper, f, ensure_ascii=False, indent=4)
    return selected_paper


if __name__ == '__main__':
    save_dir = 'data/environment/2025_0402_170228'
    paper_reviewer = PaperReviewer(save_dir)
    paper_reviewer('River pollutants')

    select_paper(save_dir, 10)