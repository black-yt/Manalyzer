import os
import json
from utils.logger import create_logger
from structai import read_pdf, save_file, get_all_file_paths


class PaperParser:
    def __init__(self, save_dir: str):
        with open(os.path.join(save_dir, '0_paper_info.json'), 'r', encoding='utf-8') as file:
            self.paper_info_dict = json.load(file)
        self.content_list_info_path = os.path.join(save_dir, f'1_content_list_info.json')

        self.logger = create_logger('PaperParser', os.path.join(save_dir, 'log'))
        self.logger.info(f'{len(self.paper_info_dict)} PDFs to be processed')
    

    def __call__(self):
        pdf_paths = []
        for paper_idx, paper_info in self.paper_info_dict.items():
            pdf_paths.append(paper_info['pdf_path'])
        read_pdf(pdf_paths)

        for paper_idx, paper_info in self.paper_info_dict.items():
            content_list_file_name = os.path.basename(get_all_file_paths(paper_info['pdf_path'].replace(".pdf", ""), "_content_list.json")[0])
            paper_info['content_list_path'] = paper_info['pdf_path'].replace(".pdf", f"/{content_list_file_name}")
            paper_info['md_path'] = paper_info['pdf_path'].replace(".pdf", "/full.md")
        
        save_file(self.paper_info_dict, self.content_list_info_path)
        self.logger.info(f'{len(self.paper_info_dict)} PDFs processed')
        self.logger.info(f'Saved content list info in {self.content_list_info_path}')


if __name__ == "__main__":
    paper_parser = PaperParser('data/environment/2025_0402_170228')
    paper_parser()