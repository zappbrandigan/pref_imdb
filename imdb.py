import requests
import json
import re
import urllib.parse
import sys
import header

def construct_query(q_data: str, is_title: bool = False) -> dict:
    """
    Converts request data into required API  query format.

    :param q_data: value to search (title, or imdb id)
    :param is_title: is a title search (boolean)
    :returns: dictionary, required api format
    """

    return {'q': q_data} if is_title else {'tconst': q_data}


def request_imdb_data(qString: str, url: str, headers: dict) -> dict:
    """
    Requests data from imdb API url using title or imdb id and converts to dict.

    :param qString: search data (title or imdb id)
    :param url: api specific url
    :param headers: api specific headers
    :returns: api response data as dict
    """

    response = requests.request("GET", url, headers=headers, params=qString)
    return json.loads(response.text)


def request_lang_detection(title: str) -> str:
    """
    Requests a language detection from API.

    :param title: title of production 
    :returns: language code
    """
    payload = f"q={urllib.parse.quote(title)}"
    response = requests.request("POST", header.urls['detect_lang'], data=payload, headers=header.headers_google)
    data = json.loads(response.text)
    return data['data']['detections'][0][0]['language'].upper()


def display_search_results(titles: list, display: int = 3) -> str:
    """
    Displays top hits from title search.

    :param titles: list of titles matching search
    :param display: number of results to display
    :returns: list of results as formatted string
    """
    
    results = "" 
    for index in range(display):
        results += f"{index + 1}= Type: {titles[index].get('titleType', 'AKA'):<15}"
        results += f"Title: {titles[index].get('title', titles[index].get('name', 'Not Found')):<25}\n"
    return results


def get_user_selection(result_count: int) -> int:
    """
    Gets user selection from display title search results.

    :param result_count: the number of results displayed
    :returns: user selection as index
    """
    
    user_selection = None
    while user_selection not in range(result_count+1):
        user_selection = input("Enter title number: ")
        try:
            user_selection = int(user_selection)
            if user_selection not in range(1, result_count+1):
                raise ValueError
            user_selection -= 1     # adjusts to index
        except ValueError:
            print('Invalid Entry.')

    return user_selection  


def display_title_credits(title: dict, imdb_id: str) -> str:
    """
    Collects results from title to display

    :param title: api dict from selected title
    :param imdb_id: imdb id formatted for PREF
    :returns: formatted results string
    """
    base = title['base']
    cast = title['cast']
    director = title['crew']['director'][0]

    results = f"{'*' * 15} Production Details {'*' * 15}\n"
    results += f"Title: {base.get('title', base.get('name', 'NA'))}\n"
    results += f"Type: {base.get('titleType', 'NA')}\n"
    results += f"Year: {base.get('year', 'Unavailable')}\n"
    results += f"IMDb: {imdb_id} \t(formatted for PREF)\n\n"

    results += f"{cast[0].get('category', 'NA').title()}: {cast[0].get('legacyNameText', cast[0].get('name', 'NA'))}\n"
    results += f"{cast[1].get('category', 'NA').title()}: {cast[1].get('legacyNameText', cast[1].get('name', 'NA'))}\n"
    results += f"{cast[2].get('category', 'NA').title()}: {cast[2].get('legacyNameText', cast[2].get('name', 'NA'))}\n"
    
    results += f"Director: {director.get('legacyNameText', director.get('name', 'NA'))}\n"

    return results


def display_alternate_titles(titles: dict) -> str:
    """
    Display alternate titles. Calls request_lang_detection.

    :param titles: dictionary from api call
    :returns: formatted result string with alternate titles and language codes.
    """
    repeats = set()
    results = f"\n{'*' * 16} Alternate Titles {'*' * 16}\n"

    for entry in titles["alternateTitles"]:
        title = entry.get('title', 'NA')
        if title not in repeats:
            language = request_lang_detection(title)
            results += f"Language: {language:<5}\tTitle: {title:<30}\n"
        
        repeats.add(entry.get('title', 'NA'))
    
    return results


def convert_imdb_id(imdb_id: str) -> str:
    """
    Formats IMDb id for entry into PREF by deleting first 't' if string is longer than 9.

    :param imdb_id: string imdb title id
    :returns: formatted id string
    """
    return imdb_id[1:] if len(imdb_id) > 9 else imdb_id


def main():
    RESULT_COUNT = 3    # default num of search results to display
    imdb_id = None
    qString = None

    search_options = {
        'title': 1,
        'id': 2
    }

    print(f"\nSEARCH TYPE:\n\n{search_options['title']}=Search by Title\n{search_options['id']}=Search by IMDb ID\n")
    search_type = input("Enter Search Type: ")

    try:
        search_type = int(search_type)
        if search_type not in search_options.values():
            raise ValueError 
    except ValueError:
        print('Invalid Selecton.')
        sys.exit()

    if search_type is search_options['title']:
        search_text = input("\nEnter production title: ")

        qString = construct_query(search_text, True)

        # Search for production title and display top hits
        title_list = request_imdb_data(qString, header.urls['title_search'], header.headers_imdb)
        print(display_search_results(title_list['results'], RESULT_COUNT))

        # Get search result index value for detailed credits
        user_selection = get_user_selection(RESULT_COUNT)
    
        selected_title = title_list['results'][user_selection]
        imdb_id = selected_title['id'].split('/')[2] #tt id

    elif search_type is search_options['id']:
        imdb_id = input("\nEnter IMDb ID: ")
        if not re.search(r"^tt[0-9]{7,8}$", imdb_id):
            print("Invalid ID.")
            sys.exit()

    qString = construct_query(imdb_id)

    credits = request_imdb_data(qString, header.urls['get_credits'], header.headers_imdb)
    print(display_title_credits(credits, convert_imdb_id(imdb_id)))

    alternate_titles = request_imdb_data(qString, header.urls['get_versions'], header.headers_imdb)
    print("\n Detecting Title Languages ...")
    print(display_alternate_titles(alternate_titles))


main()