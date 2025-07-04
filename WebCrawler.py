from time import sleep
import requests
from bs4 import BeautifulSoup

def crawler(url):
    try:
        count=0
        response = requests.get(url, timeout=2)
        response.raise_for_status()         
        soup = BeautifulSoup(response.text, 'html.parser')
        soup_links = soup.find_all('a', href=True)
        for link in soup_links:
            if link['href'].startswith('https://') and 'caltech.edu' in link['href']:
                links.append(link['href'])
                count += 1
        return count
    except:
        print(f"error with: {url}")

def visit(links):
    count=0
    visited = set()
    for url in links:
        if url not in visited and url not in disallow:
            visited.add(url)
            count += 1
            vis = crawler(url)
            print(f"visited #{count}: {url} | found: {vis}")            
            if count >= browse_limit: break
    sleep(delay_amt)
    print(f"total links found: {len(links)-1}")


links=['https://www.caltech.edu']
disallow=[] #if we want it for later
browse_limit = 30
delay_amt = .5
print(f"starting with browse limit: {browse_limit} and delay amount: {delay_amt} sec on {links}")
visit(links)