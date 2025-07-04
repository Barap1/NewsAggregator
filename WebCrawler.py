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

def disallow_links(url):
    try:
        response = requests.get(f'{url}/robots.txt', timeout=2)
        response.raise_for_status()
        for line in response.text.splitlines():
            if line.startswith('Disallow:'):
                path = line.split(':', 1)[1].strip()
                disallow.append(url + path)
    except:
        print(f"error checking robots.txt for: {url}")
    
links=['https://www.caltech.edu']
disallow=[]
browse_limit = 30
delay_amt = .5

disallow_links('https://www.caltech.edu')
print(disallow)


print(f"starting with browse limit: {browse_limit} and delay amount: {delay_amt} sec on {links}")
visit(links)
