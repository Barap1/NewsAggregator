import requests
from bs4 import BeautifulSoup
import re
import google.generativeai as genai

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
        if len(articles) >= 5:  # Limit to 5 articles
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
    genai.configure(api_key="AIzaSyBnFqmZ1ygrYSfbVRtYSkxujOhVW3pT-Ow")
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

if __name__ == "__main__":
    keyword = "tech" #input("Enter keyword to search on Google News: ")
    google_results = scan_google_news_live(keyword)
    filtered_results = filter_headlines_with_gemini(google_results, keyword)
    for article in filtered_results:
        print(article)


