import requests
from bs4 import BeautifulSoup

response = requests.get ("https://paulohm.com")
soup = BeautifulSoup(response.text, 'html.parser')

a = 1 
b = 2 
print 

for link in soup.find_all('a'):
    print(link.get('href'))
