import os
from structai import LLMAgent
from tools.academic_search import search_crossref, search_arxiv
from tools.pdf_downloader import download_pdf_with_doi, download_pdf
from utils.logger import create_logger
from datetime import datetime
import time
from tqdm import tqdm
import json


system_prompt = """
You are an expert academic researcher in <INPUT1> with extensive experience in literature search and systematic reviews. When given a research topic or area of interest, generate a comprehensive set of search keywords organized by conceptual categories. 

For each input topic:
1. Analyze the core concepts and related subfields
2. Identify technical terms, synonyms, and variant phrasings
3. Include broader and narrower terms to ensure search flexibility
4. Group keywords thematically into logical clusters

Output format requirements:
- Provide only a list of lists (no explanations or headers)
- Each sublist should contain closely related terms
- Include 15-30 total keywords for most topics
- Order terms from most to least central within each group
- Use standardized academic terminology

Example for "neural networks in medical imaging":
[["Deep Learning", "Convolutional Neural Networks", "CNN", "AI Diagnostics"], 
["Medical Imaging", "Radiology", "MRI", "CT Scan", "Ultrasound"],
["Image Segmentation", "Feature Extraction", "Classification", "Computer-Aided Diagnosis"]]
"""

query_prompt = """
[The Start of Research Areas of Interest to Users]
<INPUT1>
[The End of Research Areas of Interest to Users]
"""

class PaperCollector(LLMAgent):
    def __init__(self,
                api_key = None,
                api_base = None,
                model_version = 'gemini-3-flash-preview-nothinking',
                system_prompt = system_prompt,
                max_tokens = 4096,
                temperature = 0,
                http_client = None,
                headers = None,
                time_limit = 5*60,
                max_try = 1,
                use_responses_api = False,
                field = 'science',
                save_dir = 'data',
                search_engine = 'arxiv' # 'crossref'
                ):
        assert search_engine in ['crossref', 'arxiv'], "Please select 'crossref' or 'arxiv'"
        super().__init__(api_key, api_base, model_version, system_prompt, max_tokens, temperature, http_client, headers, time_limit, max_try, use_responses_api)
        self.system_prompt = self.system_prompt.replace('<INPUT1>', field)
        self.field = field

        # path
        current_time = datetime.now().strftime("%Y_%m%d_%H%M%S")
        self.save_dir = os.path.join(save_dir, field.replace(' ', '_'), current_time)
        self.pdf_save_dir = os.path.join(self.save_dir, '0_pdf')
        self.log_save_dir = os.path.join(self.save_dir, 'log')
        self.paper_info_path = os.path.join(self.save_dir, '0_paper_info.json')
        os.makedirs(self.pdf_save_dir, exist_ok=True)
        os.makedirs(self.log_save_dir, exist_ok=True)

        self.search_engine = search_engine
        if search_engine == 'crossref':
            self.search = search_crossref
            self.download = download_pdf_with_doi
        elif self.search_engine == 'arxiv':
            self.search = search_arxiv
            self.download = download_pdf
        self.logger = create_logger('PaperCollector', self.log_save_dir)
        self.logger.info(f"PDF directory created at {self.pdf_save_dir}")
    
    def get_save_dir(self):
        return self.save_dir
    
    def __call__(self, topic_of_interest, paper_list: list=None, doi_list:list=None, paper_search_num=2, max_down_try=3):
        paper_list_all = []
        if paper_list is not None:
            for paper_title in paper_list:
                self.logger.info(f'Search title: {paper_title}')
                paper_info = self.search(paper_title, 1)[0]
                if paper_info not in paper_list_all:
                    paper_list_all.append(paper_info)
        
        if paper_search_num > 0:
            query = query_prompt.replace('<INPUT1>', topic_of_interest)
            keywords_list = self.safe_api(query, return_example=[[]])
            
            for keywords in keywords_list:
                keywords_str = ', '.join(keywords)
                self.logger.info(f'Search using keywords: {keywords_str}')
                try:
                    paper_list = self.search(keywords_str, paper_search_num)
                    for paper_info in paper_list:
                        if paper_info not in paper_list_all:
                            paper_list_all.append(paper_info)
                except:
                    self.logger.error(f'Search failed')
        
        if doi_list is not None:
            for doi in doi_list:
                paper_list_all.append({'title': doi, 'doi': doi})

        self.logger.info(f'{len(paper_list_all)} papers found')
        self.logger.info(f'Start downloading ...')
        paper_info_dict = {}
        for paper_info in tqdm(paper_list_all):
            paper_idx_str = f'{len(paper_info_dict):05}'
            if self.search_engine == 'crossref':
                url = paper_info['doi']
            elif self.search_engine == 'arxiv':
                url = paper_info['url']
            pdf_name = paper_idx_str+'.pdf'
            for down_try in range(max_down_try):
                if self.download(url, self.pdf_save_dir, pdf_name):
                    paper_info['pdf_path'] = os.path.join(self.pdf_save_dir, pdf_name)
                    paper_info_dict[paper_idx_str] = paper_info
                    with open(self.paper_info_path, 'w', encoding='utf-8') as f:
                        json.dump(paper_info_dict, f, ensure_ascii=False, indent=4)
                    break
                if down_try < max_down_try-1:
                    time.sleep(1)
        
        self.logger.info(f'{len(paper_info_dict)} papers downloaded in {self.pdf_save_dir}')
        self.logger.info(f'Saved paper information in {self.paper_info_path}')


if __name__ == '__main__':
    paper_collector = PaperCollector(field='environment')
    paper_collector('River pollutants', paper_list=['EU-wide survey of polar organic persistent pollutants in European river waters'], doi_list=['10.1007/s10661-008-0688-5'], paper_search_num=1)
