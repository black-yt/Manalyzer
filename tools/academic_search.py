import requests
import arxiv
from tools.scihub import SciHub

sh = SciHub()
arxiv_client = arxiv.Client()
email = 'rosalinagibboneyreg98@gmail.com'

def search_scihub(query, rows=5):
    r = sh.search(query, limit=rows)
    results = []
    for paper in r['papers']:
        results.append({
            'title': paper['name'],
            'url': paper['url']
        })
    return results

def search_crossref(query, rows=5):
    url = 'https://api.crossref.org/works'
    params = {
        'query': query,
        'rows': rows,
        'mailto': email
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        result = []
        for item in data['message']['items']:
            title = item.get('title', ['No title'])[0]
            # authors = ', '.join([f"{author['given']} {author['family']}" for author in item.get('author', [])])
            doi = item.get('DOI', 'No DOI')
            result.append({
                'title': title,
                # 'authors': authors,
                'doi': doi
            })
        return result
    else:
        # print(f'Error: {response.status_code}')
        return None


def search_semantic_scholar(query, rows=5):
    url = f'https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={rows}'
    response = requests.get(url)
    
    if response.status_code == 200:
        papers = response.json().get('data', [])
        result = []
        for paper in papers:
            title = paper.get('title')
            authors = ', '.join([author['name'] for author in paper.get('authors', [])])
            paper_url = paper.get('url')
            pdf_url = paper.get('paperId')
            result.append({
                'title': title,
                'authors': authors,
                'url': paper_url,
                'pdf': f'https://www.semanticscholar.org/paper/{pdf_url}'
            })
        return result
    else:
        # print(f'Error: {response.status_code}')
        return None


def search_arxiv(query, rows=5):
    search = arxiv.Search(
        query=query,
        max_results=rows
    )

    results = arxiv_client.results(search)
    result_list = []
    for x in results:
        result_list.append({
            'title': x.title,
            'url': x.pdf_url,
        })
    return result_list


if __name__ == '__main__':
    # result = search_scihub('machine learning')
    # print(result)

    # result = search_crossref('machine learning')
    # print(result)

    # result = search_semantic_scholar('machine learning')
    # print(result)
    
    result = search_arxiv('machine learning')
    # print(result)
