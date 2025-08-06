import serpapi
from serpapi import GoogleSearch
import os
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langchain_core.tools import tool
from typing import TypedDict
import requests
from bs4 import BeautifulSoup


load_dotenv()


api_key = os.getenv("SERPAPI_KEY")
# client = serpapi.Client(api_key=api_key) #wasnt working

# asking the use what they would like to search
print("Welcome to Google Search Assistant! Type anything you want information on(question, person, etc.) and "
      "we will give you an answer!\nType 'quit' to exit.\n")



# blocking certain sites
from urllib.parse import urlparse

BLOCKED_DOMAINS = [  "quora.com",# user-generated and opinionated
    "reddit.com",         # noisy, unstructured
    "youtube.com",        # video content, hard to scrape
    "facebook.com",       # login required
    "x.com",
    "twitter.com",        # login required + API protected
    "tiktok.com",         # video platform
    "pinterest.com",      # low text, image-based
    "medium.com",         # variable quality, often gated
    "linkedin.com",       # login required
    "instagram.com",      # images only, not useful for scraping
    "tumblr.com",         # blog-style, often noisy
    "imdb.com",           # mostly structured data, gated
    "stackexchange.com",  # Q&A format, sometimes useful but inconsistent
    "stackoverflow.com",  # developer-specific
    "fandom.com",         # user-generated fan content
    "tripadvisor.com",    # opinion-heavy reviews
    "amazon.com",         # shopping, not informational
    "ebay.com",           # shopping, not useful for general info
    "change.org",         # petition-based
    "crunchbase.com",      # i got banned
]

def is_allowed(url):
    domain = urlparse(url).netloc  # Extracts the domain part of the URL (e.g., 'www.reddit.com')
    domain = domain.replace("www.", "")
    for blocked in BLOCKED_DOMAINS:
        if blocked in domain:
            return False
    return True

def pick_allowed_sites(websites, n):
    allowed = []
    for url in websites:
        if is_allowed(url):
            allowed.append(url)
        if len(allowed) == n:
            break
    return allowed



headers = {"User-Agent": "Mozilla/5.0"}




llm = OllamaLLM(model="qwen3:4b")

prompt = f"""
    You are an AI assistant that gets fed information scraped from the web based on a user's question and the message
    history.
    Your job is to understand the information and with that knowledge, answer the users question or give them information
    on what they said. Use context clues. State your answer clearly, and then in a new line, add a horizontal rule. The
    line after the horizontal rule should contain your reasoning. Also, always make sure everything is sent in a readable
    manner. Make sure to be consistent with how you structure your answers.
    """



if __name__ == "__main__":

    messages = []

    while True:
        # Dictionary to store content from each site
        alldata = {}


        query = input(">  ")

        if query.lower() == "quit":
            print("\n----------------------------------------------------\nThank you for using Google Search Assistant!")
            break

        search = GoogleSearch({
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "location": "Frisco, Texas",
            "hl": "en",
            "gl": "us"
        })

        try:
            result = search.get_dict()
        except Exception as e:
            print(f"Search failed: {e}")
            continue

        sites = []


        # iterating through the first 10 results and getting the links
        if "organic_results" not in result:
            print("No results found or blocked by SerpAPI.")
            continue

        for item in result["organic_results"][:10]:
            sites.append(item["link"])

        allowed_sites = pick_allowed_sites(sites, 5)

        # Loop through each allowed site and extract <p> text
        for i, url in enumerate(allowed_sites, start=1):
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()  # Raise error for bad status codes

                soup = BeautifulSoup(response.content, 'html.parser')

                site_text = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))

                alldata[f"site_{i}"] = site_text

            except Exception as e:
                print(f"Failed to fetch or parse site {url}: {e}")
                alldata[f"site_{i}"] = ""  # Still include the key, even if empty



        messages.append(f"User: {query}")

        full_prompt = prompt

        for i, key in enumerate(alldata.keys(), start=1):
            full_prompt += f"\n\nSite {i}: {alldata[key]}\n--------------------------------------\n"

        full_prompt += "\n\n" + "\n".join(messages) + "\nAI:"
        # turns all the messages into one long message with a new line for each message
        response = llm.invoke(full_prompt)

        print(f"{response}\n-----------------------------------------------------------------\n")

        messages.append(f"AI: {response}")
