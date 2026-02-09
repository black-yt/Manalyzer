import os
chat_dir = 'webui/data/'
os.makedirs(chat_dir, exist_ok=True)
if os.path.exists(os.path.join(chat_dir, "user_input.json")):
    os.remove(os.path.join(chat_dir, "user_input.json"))
with open(os.path.join(chat_dir, "chat.log"), 'w', encoding='utf-8') as file:
    file.write("Activity Log\n")
if os.path.exists(os.path.join(chat_dir, "save_info.json")):
    os.remove(os.path.join(chat_dir, "save_info.json"))
print("Cleaned up previous files.")

from agents.paper_collector import PaperCollector
from agents.paper_parser import PaperParser
from agents.paper_reviewer import PaperReviewer, select_paper
from agents.table_processor import TableProcessor
from agents.data_extrator_checker import DataExtratorWithChecker
from agents.data_merger import DataMerger
from agents.data_analyst import DataAnalyst
from agents.reporter import Reporter
import json
import time


if __name__ == '__main__':
    paper_collector = PaperCollector(field='chat')
    save_dir = paper_collector.get_save_dir()

    with open(os.path.join(chat_dir, "save_info.json"), 'w', encoding='utf-8') as f:
        json.dump([save_dir], f, ensure_ascii=False, indent=4)
    print(f"save_dir: {save_dir}")

    user_input_path = os.path.join(chat_dir, 'user_input.json')
    user_input = None
    while True:
        try:
            with open(user_input_path, 'r', encoding='utf-8') as file:
                user_input = json.load(file)
        except:
            pass
        
        if isinstance(user_input, dict) and 'filed' in user_input and 'topic_of_interest' in user_input and 'table_template' in user_input:
            break
        print(f"Waiting for user input..., {user_input}")
        time.sleep(3)

    filed = user_input['filed']
    topic_of_interest = user_input['topic_of_interest']
    table_template = user_input['table_template']

    paper_collector(topic_of_interest, paper_search_num=2)

    paper_parser = PaperParser(save_dir=save_dir, max_workers=2)
    paper_parser()

    paper_reviewer = PaperReviewer(save_dir=save_dir, field=filed)
    paper_reviewer(topic_of_interest)

    select_paper(save_dir, 10)

    table_processor = TableProcessor(save_dir=save_dir, field=filed)
    table_processor()


    data_extrator_with_checker = DataExtratorWithChecker(save_dir=save_dir, field=filed)
    data_extrator_with_checker(topic_of_interest=topic_of_interest, table_template=table_template)

    data_merger = DataMerger(save_dir=save_dir)
    data_merger(table_template)

    data_analyst = DataAnalyst(save_dir=save_dir, field=filed)
    data_analyst()

    reporter = Reporter(save_dir=save_dir, field=filed)
    reporter(topic_of_interest)