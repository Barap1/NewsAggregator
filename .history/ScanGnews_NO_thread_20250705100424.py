import requests
from bs4 import BeautifulSoup
import re
import google.generativeai as genai
import time
import os

def get_api_key():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("key not put")
    return api_key

def scan_google_news_live(keyword):
    base_url = "https://news.google.com/search"
    params = {
        'q': keyword,
        'hl': 'en-US',
        'gl': 'US',
        'ceid': 'US:en'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; NewsAggregatorBot/1.0)'
    }
    response = requests.get(base_url, params=params, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []


    for card in soup.find_all('div', class_='m5k28'):
        if len(articles) >= 20:  # for the sake of me free api limit
            break
        a_tag = card.find('a', class_='JtKRv')
        if not a_tag or not a_tag.has_attr('href'):
            continue
        link = a_tag['href']
        if link.startswith('./'):
            link = 'https://news.google.com' + link[1:]
        headline = a_tag.get_text(strip=True)
        articles.append({
            'headline': headline,
            'link': link
        })
    return articles

def filter_headlines_with_gemini(google_results, keyword):
    genai.configure(api_key=get_api_key())
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite-preview-06-17")
    headlines = [i['headline'] for i in google_results]

    prompt = (
        f"Given the following list of news headlines, return only those that are clearly not related to the keyword '{keyword}'. It is completely fine and likely that there are none. You may also compare the headlines to each other to determine if they are related.\n"
        "Return the result as only the headlines in a separated list, exactly as how it was before. Just the unrelated headlines. If there are none just return nothing\n\n"
        "Here is the list:\n"
        f"{headlines}"
    )

    response = model.generate_content(prompt)
    for removal in response.text.splitlines():
        if removal:
            google_results = [article for article in google_results if article['headline'] != removal]
    return google_results
def fetch_article_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
        
        content = ""
        
        article_selectors = [
            'article', 
            '.article-content', 
            '.post-content', 
            '.entry-content',
            '.content',
            '[role="main"]',
            'main',
            '.story-body',
            '.article-body'
        ]
        
        for selector in article_selectors:
            article_element = soup.select_one(selector)
            if article_element:
                content = article_element.get_text(strip=True)
                break
        
        if not content:
            paragraphs = soup.find_all('p')
            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
        
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        if len(content) > 5000:
            content = content[:5000] + "..."
            
        return content
        
    except Exception as e:
        return ""

def summarize_articles_with_gemini(articles_with_content, keyword):
    genai.configure(api_key=get_api_key())
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite-preview-06-17")
    
    articles_text = ""
    for i, article in enumerate(articles_with_content, 1):
        articles_text += f"\n\n--- Article {i}: {article['headline']} ---\n"
        articles_text += f"Source: {article['link']}\n"
        articles_text += f"Content: {article['content']}\n"
    
    prompt = f"""
    Please analyze and summarize the following {len(articles_with_content)} news articles related to "{keyword}".
    
    Create a comprehensive summary that includes:
    1. A brief overview of the main themes and trends
    2. Key highlights from each article
    3. Important insights or developments
    4. A well-formatted presentation suitable for reading
    
    Please format the response in a clear, professional manner with proper headings and bullet points.
    
    Here are the articles:
    {articles_text}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"{str(e)}"

def save_summary_to_file(summary, keyword):
    filename = f"news_summary_{keyword}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"NEWS SUMMARY FOR '{keyword.upper()}'\n")
            f.write(summary)
        
        print(f"saved to {filename}")
        return filename
    except Exception as e:
        print(f"error {str(e)}")
        return None

if __name__ == "__main__":
    try:
        keyword = input("??: ")
        
        print(f"searching for '{keyword}' on gnews")
        google_results = scan_google_news_live(keyword)
        print(f"before {len(google_results)}")
        print("filtering articles")
        filtered_results = filter_headlines_with_gemini(google_results, keyword)
        print(f"after {len(filtered_results)} ")

        print("\n fetching contents")
        articles_with_content = []
        for i, article in enumerate(filtered_results, 1):
            content = fetch_article_content(article['link'])
            articles_with_content.append({
                'headline': article['headline'],
                'link': article['link'],
                'content': content
            })
            time.sleep(.5)
        
        print("\ncreating summary")
        summary = summarize_articles_with_gemini(articles_with_content, keyword)

        save_summary_to_file(summary, keyword)
    except Exception as e:
        print(f"error {e}")

