import sys, time, re
import wikipediaapi
import requests
from urllib.parse import urlparse, urlunparse, quote
from bs4 import BeautifulSoup
from markdownify import markdownify as md

CONTACT_EMAIL = 'your_email_here@example.com'
USER_AGENT = f"turk_lib.py/0.7 ({CONTACT_EMAIL})"
wiki_wiki = wikipediaapi.Wikipedia(
    language = 'en',
    extract_format = wikipediaapi.ExtractFormat.WIKI,
    user_agent = USER_AGENT )

def print_log(log_string = '',log_to_file=True, noStdOut = True):
    LOG_FILENAME = sys.argv[0].split('.')[0] + '.log'

    timestamp = time.strftime("%m/%d/%y  %H:%M:%S", time.localtime(time.time()))
    if not noStdOut: print(f"[ {timestamp} ] {log_string}")

    if(log_to_file):
        with open(LOG_FILENAME, "a") as file:
            file.write(f"[ {timestamp} ] {log_string}\n")   

# Precomputed lists
ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
TEENS = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "ten", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
TEEN_REPLACEMENTS = {TEENS[i]: ONES[i] for i in range(1, 10)}

def replace_tens_teens_with_ones(input_string: str) -> str:
    for teen, replacement in TEEN_REPLACEMENTS.items():
        input_string = input_string.replace(teen, replacement)

    for i in range(2, 10):
        input_string = input_string.replace(TENS[i], ONES[i])

    return input_string

def convert_to_words(number) -> str:
    if number == 0:
        return "zero"
    
    if_negative = 'minus ' if number < 0 else ''
    number = abs(number)

    def convert_chunk(n):
        if n < 10:
            return ONES[n]
        if n < 20:
            return TEENS[n - 10]
        if n < 100:
            return TENS[n // 10] + (" " + ONES[n % 10] if n % 10 != 0 else "")
        return ONES[n // 100] + " hundred" + (" " + convert_chunk(n % 100) if n % 100 != 0 else "")

    # Handling large numbers (trillion and above) with direct computation
    if number >= 1000000000000:
        exponent = len(str(number)) - 1
        mantissa = round(number / 10**exponent, 2)
        high, low = divmod(int(mantissa * 100), 100)
        return f"{if_negative}{convert_chunk(high)}{('' if mantissa == round(mantissa) else ' point ' + convert_chunk(low))} times ten to the power of {convert_chunk(exponent)}"

    parts = []
    for divisor, name in [(1000000000, "billion"), (1000000, "million"), (1000, "thousand")]:
        if number >= divisor:
            parts.append(convert_chunk(number // divisor) + " " + name)
            number %= divisor
    parts.append(convert_chunk(number))

    return ' '.join(parts)

def number_to_words(input_str: str) -> str:
    # if_negative = 'minus ' if input_str.startswith('-') else ''

    # Handle negatives
    if input_str.startswith('-'):
        if_negative = 'minus '
        input_str = input_str.lstrip('-')
    else:
        # Not negative; handle possible years
        if_negative = ''
        if ',' not in input_str and '.' not in input_str and len(input_str) == 4:
            # Might be a year
            year = int(input_str)
            if year < 2000 or year > 2009:
                return number_to_words(input_str[:2]) + ' ' + number_to_words(input_str[-2:])

    parts = input_str.replace(',', '').split('.')
    integer_part = int(parts[0])
    words = if_negative + convert_to_words(integer_part)

    if len(parts) > 1:
        decimal_digits = [ONES[int(digit)] if digit != '0' else 'zero' for digit in parts[1]]
        words += ' point ' + ' '.join(decimal_digits)

    return words

def convert_complete_number_string(number_string: str) -> str:
    number_regex = r'(?<!\d)-?\d+(?:,\d{3})*(?:\.\d+)?|\b-?\d*\.\d+\b'

    def replace_match(match):
        number_value = match.group(0)
        return number_to_words(number_value)

    return re.sub(number_regex, replace_match, number_string)

def fetch_wikipedia_article(article_name: str, only_summary: bool = True):
    wiki_page = wiki_wiki.page(article_name)
    if not wiki_page.exists(): 
        return f"No such article [{article_name}]"
    else:
        return wiki_page.summary

def wiki_search(search_query: str, number_of_results: int = 3):
    endpoint_url = 'https://api.wikimedia.org/core/v1/wikipedia/en/search/page'
    parameters = {'q': search_query, 'limit': number_of_results} if number_of_results > 0 else {'q': search_query}
    response = requests.get(endpoint_url, headers={'User-Agent': USER_AGENT}, params=parameters)
    pages = data = response.json()['pages']
    results = []
    for page in pages:
        results.append(page.get('key'))

    return results

def web_search(query_string: str) -> str:
    url = 'https://www.google.com/search?q=' + quote(query_string)
    return f"[TOOL_RESULT]{markdown_browser(url)}[/TOOL_RESULT]"

def markdown_browser(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html5lib')
        for bad_tag in soup(["script", "style", "svg", "img"]): 
            bad_tag.decompose()
        markdown = md(str(soup.body.prettify()))
        markdown = re.sub(r'(> +)+', '> ', markdown) # Remove superfluous blockquote markers from markdownify result

        result = ''
        for line in markdown.split('\n'):
            new_line = line.replace('>','').rstrip() 
            if new_line: 
                result += line + '\n'

        return result

    except (requests.exceptions.RequestException, AttributeError):
        print(Exception)
        return f"<!-- Unable to retrieve ({url}): {Exception} -->"

if __name__ == '__main__':
    # print(fetch_wikipedia_article('Python_(programming_language)'))
    articles = wiki_search('api', 0)
    for article in articles:
        print(f"{article.upper()}:\n{fetch_wikipedia_article(article)}\n")
