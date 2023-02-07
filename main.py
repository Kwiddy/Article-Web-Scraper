# NOTE: Also need to pip install lxml
import pandas as pd
import urllib.request
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
from tqdm import tqdm
from collections import defaultdict


MIN_P_SIZE = 100
MIN_ARTICLE_SIZE = 1000
AUTO_ACCEPT_PDF = True
OPTIONS = { "A": "https://dgap.org/en/publications",
            "B": "https://climateandsecurity.org/reports/",
            "C": "https://ip-quarterly.com"}


def retrieve_body_length(soup_response):
    ''' Estimate the length of the main article content '''
    parents = defaultdict(list)
    content_xml = soup_response.find_all("p")
    for item in content_xml:
        item_txt = ' '.join([r.text.strip() for r in item])
        word_count = len(item_txt.split())
        if word_count >= MIN_P_SIZE:
                parents[item.parent].append(item)

    max_len_found = 0
    for children in parents.values():
        children_length = sum([len(child.text.strip()) for child in children])
        if children_length > max_len_found:
            max_len_found = children_length
    
    return max_len_found
    


def article_classifier(lengths):
    ''' Determine if link is an article or not based on given criteria and content size '''
    # print(lengths) # Uncomment with debugging to give a better indication of which links are ranked articles and which are not

    seen = set()
    article_found = False

    preds = []
    for link, val in lengths.items():
        pred = {"Article": link}
        if link not in seen:
            seen.add(link)
            if link.endswith('.pdf') and AUTO_ACCEPT_PDF:
                pred["is_article"] = True
                article_found = True
            else:
                if val < MIN_ARTICLE_SIZE:
                    pred["is_article"] = False
                else:
                    pred["is_article"] = True
                    article_found = True
        preds.append(pred)

    if not article_found:
        print("NO ARTICLES FOUND - Try changing the system parameters to less strict values")

    return preds


def output_to_csv(article_df):
    ''' Output resulting article links to CSV file '''
    article_df.to_csv('articles.csv', mode='w+')
    print()
    print("SAVED: The article links have been saved to the articles.csv file in this directory")


def get_soup(url):
    ''' Scrape a given URL '''
    resp = urllib.request.urlopen(url)
    soup = BeautifulSoup(resp.read(), "lxml")
    return soup


def output_to_cli(article_df):
    ''' Allow user to view resultant articles in CLI '''
    print()
    valid_inp = False
    while not valid_inp:
        yn = input("Would you also like to display the found article links here? [Y/N]: ")
        if yn.upper() == "Y":
            print(article_df)
            valid_inp = True
        elif yn.upper() == "N":
            valid_inp = True


def scrape_url():
    ''' Take chosen URL input and scrape '''

    for code,url in OPTIONS.items():
        print(f"[{code}] - {url}")

    valid_inp = False

    while not valid_inp:
        selection = input("Please select a URL above, or enter URL of your choice: ")
        if selection.upper() in OPTIONS:
            try:
                soup = get_soup(OPTIONS[selection.upper()])
                valid_inp = True
                print()
                return OPTIONS[selection.upper()], soup
            except (URLError, HTTPError) as err:
                if err.code == 403:
                    print(f"ERROR - Unable to access URL ({err}) - Please see Notes")
                else:
                    print(f"ERROR - Unable to access URL ({err})")
        else:
            try:
                soup = get_soup(selection)
                valid_inp = True
                print()
                return selection, soup
            except (URLError, HTTPError) as err:
                if err.code == 403:
                    print(f"ERROR - Unable to access URL ({err}) - Please see Notes")
                else:
                    print(f"ERROR - Unable to access URL ({err})")
            except ValueError as err2:
                print(f"ERROR - Invalid URL ({err2})")


def main():
    ''' Main pipeline '''
    source, soup = scrape_url()

    found_links = [link["href"] for link in soup.find_all("a", href=True)]

    lengths = {}
    for link in tqdm(found_links, desc="Detecting articles from links..."):
        try:
            if link[0] in ["#", "/", "?"]:
                link = source + link
            try:
                soup = get_soup(link)
                link_body_length = retrieve_body_length(soup)
                lengths[link] = link_body_length
            except (HTTPError, URLError) as err2:
                pass 
        except IndexError as err:
            pass

    predictions = article_classifier(lengths)

    article_df = pd.DataFrame.from_dict(predictions)
    article_df = article_df[article_df["is_article"] == True].reset_index()
    article_df = article_df.drop(['is_article', 'index'], axis=1)

    output_to_csv(article_df)
    output_to_cli(article_df)


if __name__ == "__main__":
    main()