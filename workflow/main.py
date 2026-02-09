import sys
sys.path.append(".")
from agents.paper_collector import PaperCollector
from agents.paper_parser import PaperParser
from agents.paper_reviewer import PaperReviewer, select_paper
from agents.table_processor import TableProcessor
from agents.data_extrator_checker import DataExtratorWithChecker
from agents.data_merger import DataMerger
from agents.data_analyst import DataAnalyst
from agents.reporter import Reporter


if __name__ == '__main__':
    filed = 'environment'
    topic_of_interest = 'River pollutants'
    table_template = """
| River        | Location | Heavy metals | Content (µg/L) |
|--------------|----------|--------------|----------------|
| Tigris River | Turkey   | Cu           | 40             |
| Tigris River | Turkey   | Co           | 10             |
| Tiete River  | Brazil   | Fe           | 915            |
"""

    paper_collector = PaperCollector(field=filed)
    paper_collector(topic_of_interest, paper_list=['EU-wide survey of polar organic persistent pollutants in European river waters'], paper_search_num=1)
    save_dir = paper_collector.get_save_dir()

    paper_parser = PaperParser(save_dir=save_dir)
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