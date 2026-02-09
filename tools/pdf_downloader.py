import os
import requests
import re
import urllib.request
from tools.scihub import SciHub

sh = SciHub()

def download_pdf(url, dir='./', name=None):
    if name is None:
        name = url.split('/')[-1]+'.pdf'
    os.makedirs(dir, exist_ok=True)
    save_path = os.path.join(dir, name)
    
    try:
        if 'arxiv' in url:
            response = requests.get(url)
            response.raise_for_status()

            with open(save_path, 'wb') as file:
                file.write(response.content)

            # print(f"download to {save_path}")
            return True
        else:
            result = sh.download(url, path=save_path)
            if 'err' in result:
                # print(f"download wrong {result['err']}")
                return False
            else:
                return True
    except Exception as e:
        # print(f"download wrong {e}")
        return False



def download_pdf_with_doi(doi:str, dir='./', name=None):
    # https://blog.51cto.com/u_12877374/4935132
    sci_Hub_Url = "https://sci-hub.ren/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36',
    }

    paper_url = sci_Hub_Url + doi

    pattern = r'https://.*?\.pdf'
    # pattern = '/.*?.pdf'

    if name is None:
        name = doi.replace('/', '_')+'.pdf'
    os.makedirs(dir, exist_ok=True)
    save_path = os.path.join(dir, name)

    content = requests.get(paper_url, headers=headers)
    # print(content)
    download_url = re.findall(pattern, content.text)
    # print(download_url)
    for url in download_url:
        try:
            req = urllib.request.Request(url, headers=headers)
            u = urllib.request.urlopen(req, timeout=5)

            f = open(save_path, 'wb')

            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break
                f.write(buffer)
            f.close()
            # print(f"download to {save_path}")
            return True
        except Exception as e:
            # print(f"download wrong {e}")
            if 'Too Many Requests' in str(e):
                return None
    
    return False


if __name__ == '__main__':
    # python -m tools.pdf_downloader
    download_pdf('http://arxiv.org/pdf/1909.03550v1', 'test')
    download_pdf_with_doi('10.1016/s0360-3199(98)00107-4', 'test')
