import requests
from bs4 import BeautifulSoup
import re
import google.generativeai as genai
import time
import os
import threading
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue


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

def filter_headlines_with_gemini(headlines, keyword):
    genai.configure(api_key=get_api_key())
    model = genai.GenerativeModel("models/gemini-2.5-flash-lite-preview-06-17")

    prompt = (
        f"Given the following list of news headlines, return only those that are clearly related to the keyword '{keyword}'. "
        "Return the result as a JSON list of objects with 'headline' and 'link' fields, using only the original entries. append to start of each headline.\n\n"
        "Here is the list:\n"
        f"{headlines}"
    )

    response = model.generate_content(prompt)
    import json
    try:
        filtered = json.loads(response.text)
    except Exception:
        filtered = json.loads(response.text.strip('` \n').replace('json', ''))
    return filtered

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
        print(f"error from {url}: {str(e)}")
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

def multithreaded_fetch_article_content(articles_list):
    """
    Fetch article content with thread pool limited to 10 threads max,
    domain-based rate limiting, and thread-safe operations.
    """
    MAX_THREADS = 10
    DOMAIN_DELAY = 0.5  # 500ms delay between requests to same domain
    
    # Thread-safe data structures
    results = queue.Queue()
    domain_locks = {}
    domain_last_access = {}
    lock_dict_lock = threading.Lock()
    
    def get_domain_lock(url):
        """Get or create a lock for a domain in a thread-safe manner"""
        try:
            domain = urlparse(url).netloc.lower()
        except:
            domain = "unknown"
            
        with lock_dict_lock:
            if domain not in domain_locks:
                domain_locks[domain] = threading.Lock()
                domain_last_access[domain] = 0
            return domain_locks[domain], domain
    
    def fetch_with_rate_limit(article):
        """Fetch article content with domain-based rate limiting"""
        url = article['link']
        domain_lock, domain = get_domain_lock(url)
        
        with domain_lock:
            # Check if we need to wait before accessing this domain
            current_time = time.time()
            time_since_last_access = current_time - domain_last_access[domain]
            
            if time_since_last_access < DOMAIN_DELAY:
                sleep_time = DOMAIN_DELAY - time_since_last_access
                time.sleep(sleep_time)
            
            # Update last access time
            domain_last_access[domain] = time.time()
            
            # Fetch the content
            content = fetch_article_content(url)
            
            # Put result in thread-safe queue
            result = {
                'headline': article['headline'],
                'link': article['link'],
                'content': content
            }
            results.put(result)
            
            return result
    
    print(f"Fetching content using max {MAX_THREADS} threads with domain rate limiting...")
    
    # Use ThreadPoolExecutor to limit concurrent threads
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Submit all tasks
        future_to_article = {
            executor.submit(fetch_with_rate_limit, article): article 
            for article in articles_list
        }
        
        # Process completed tasks
        completed_count = 0
        for future in as_completed(future_to_article):
            completed_count += 1
            article = future_to_article[future]
            try:
                result = future.result()
                print(f"  [{completed_count}/{len(articles_list)}] Fetched: {article['headline'][:50]}...")
            except Exception as e:
                print(f"  Error fetching {article['headline'][:50]}: {e}")
                # Put error result in queue
                results.put({
                    'headline': article['headline'],
                    'link': article['link'],
                    'content': ""
                })
    
    # Convert queue to list (thread-safe)
    results_list = []
    while not results.empty():
        try:
            results_list.append(results.get_nowait())
        except queue.Empty:
            break
    
    print(f"Completed fetching {len(results_list)} articles")
    return results_list

if __name__ == "__main__":
    start_time = time.time()
    try:
        keyword = input("??: ")
        
        print(f"searching for '{keyword}' on gnews")
        google_results = scan_google_news_live(keyword)
        print(f"before {len(google_results)}")
        
        print("filtering articles")
        filtered_results = filter_headlines_with_gemini(google_results, keyword)
        print(f"after {len(filtered_results)} ")

        print("\n fetching contents")
        articles_with_content = multithreaded_fetch_article_content(filtered_results)
        
        print("\ncreating summary")
        summary = summarize_articles_with_gemini(articles_with_content, keyword)
      
        print(f"""
              NEWS SUMMARY FOR '{keyword.upper()}'
              """)
        print(summary)
        
        save_summary_to_file(summary, keyword)

    except Exception as e:
        print(f"error {e}")
    
    elapsed_time = time.time() - start_time
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
