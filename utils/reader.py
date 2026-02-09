import markdown
from bs4 import BeautifulSoup

def read_markdown(file_path, include_img=False):
    with open(file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    html_content = markdown.markdown(md_content)
    soup = BeautifulSoup(html_content, 'html.parser')

    content_dict = {}
    current_header = 'text'  # 默认键，用于存放没有标题的内容
    
    # 检查是否有任何标题
    has_headers = bool(soup.find(['h1', 'h2', 'h3']))
    
    for element in soup.find_all(True):  # 遍历所有标签元素
        if element.name in ['h1', 'h2', 'h3']:
            has_headers = True
            header_text = element.get_text()
            while header_text in content_dict:
                header_text += ' '
            content_dict[header_text] = []
            current_header = header_text
        elif not has_headers and element.name == 'p':
            # 如果没有标题，将所有段落内容收集到 'text' 键下
            if 'text' not in content_dict:
                content_dict['text'] = []
            if include_img and element.find('img'):
                for img in element.find_all('img'):
                    if 'src' in img.attrs:
                        content_dict['text'].append(img['src'])
            content_dict['text'].append(element.get_text())
        elif has_headers and element.name == 'p' and current_header:
            if current_header == 'text' and 'text' not in content_dict:
                content_dict['text'] = []
            # 处理有标题情况下的段落
            if include_img and element.find('img'):
                for img in element.find_all('img'):
                    if 'src' in img.attrs:
                        content_dict[current_header].append(img['src'])
            content_dict[current_header].append(element.get_text())

    return content_dict

if __name__ == '__main__':
    file_path = 'data/agriculture/2025_0407_111544/1_md/00074.md'
    content_dict = read_markdown(file_path, include_img=True)
    for header, content in content_dict.items():
        print(f"{header}: {content}")