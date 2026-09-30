"""Wiki Feud: a Family Feud style guessing game built from a Wikipedia article.

Pick a topic, and the game finds the closest Wikipedia page, counts its most
common words (ignoring stop words), and challenges you to guess them.
"""

import re
from collections import Counter

import requests
from bs4 import BeautifulSoup

API_URL = "https://en.wikipedia.org/w/api.php"
# Wikipedia asks API clients to identify themselves with a User-Agent.
HEADERS = {"User-Agent": "WikiFeud/1.0 (educational Python game)"}

BOARD_SIZE = 8
MAX_STRIKES = 3

STOP_WORDS = set("""
a about above after again against all almost also although always am among an
and another any anyone anything are aren't around as at be became because become
becomes been before being below between both but by can can't cannot could
couldn't did didn't do does doesn't doing don't down during each either else
even ever every few first for from further had hadn't has hasn't have haven't
having he he'd he'll he's her here here's hers herself him himself his how how's
however i i'd i'll i'm i've if in into is isn't it it's its itself just last
later least less let's like made make many may me might more most much must
mustn't my myself near neither never new no nor not now of off often on once one
only onto or other others ought our ours ourselves out over own per perhaps
rather same several shan't she she'd she'll she's should shouldn't since so some
such than that that's the their theirs them themselves then there there's these
they they'd they'll they're they've this those though through thus to too two
under until up upon us use used using very via was wasn't we we'd we'll we're
we've well were weren't what what's when when's where where's whether which while
who who's whom whose why why's will with within without won't would wouldn't yet
you you'd you'll you're you've your yours yourself yourselves
also known called include including includes included within throughout among
one two three four five six seven eight nine ten first second third
""".split())


def find_article(topic):
    """Return the title of the Wikipedia article that best matches `topic`."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": topic,
        "srlimit": 1,
        "format": "json",
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
    response.raise_for_status()
    results = response.json()["query"]["search"]
    return results[0]["title"] if results else None


def scrape_article(title):
    """Download the article and return its body text (paragraphs only)."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "redirects": 1,
        "format": "json",
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
    response.raise_for_status()
    html = response.json()["parse"]["text"]["*"]

    soup = BeautifulSoup(html, "html.parser")
    # Drop footnote markers like [1] and inline styles before grabbing text.
    for tag in soup.select("sup.reference, style, .mw-editsection"):
        tag.decompose()
    return " ".join(p.get_text(" ") for p in soup.find_all("p"))


def count_words(text):
    """Count word frequencies, skipping stop words, numbers and tiny words."""
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())
    counts = Counter()
    for word in words:
        if word.endswith("'s"):
            word = word[:-2]
        if len(word) < 3 or word in STOP_WORDS:
            continue
        counts[word] += 1

    # Fold simple plurals into their singular ("pizzas" -> "pizza") when both appear.
    for word in list(counts):
        for suffix in ("es", "s"):
            singular = word[: -len(suffix)]
            if word.endswith(suffix) and singular in counts:
                counts[singular] += counts.pop(word)
                break
    return counts


def matches(guess, word):
    """Accept an exact match, or a simple singular/plural variant."""
    return guess in (word, word + "s", word + "es") or word in (guess + "s", guess + "es")


def show_board(answers, revealed):
    print()
    print("=" * 40)
    for rank, (word, count) in enumerate(answers, start=1):
        if word in revealed:
            print(f" {rank}. {word.upper():<28}{count:>4}")
        else:
            print(f" {rank}. {'_' * 28}{'??':>4}")
    print("=" * 40)


def play(title, counts):
    answers = counts.most_common(BOARD_SIZE)
    revealed = set()
    guessed = set()
    strikes = 0
    score = 0

    print(f'\nSurvey says... we scraped "{title}"!')
    print(f"Guess the {len(answers)} most common words in the article.")
    print(f"You get {MAX_STRIKES} strikes. Type 'quit' to give up.")

    while strikes < MAX_STRIKES and len(revealed) < len(answers):
        show_board(answers, revealed)
        print(f"Score: {score}   Strikes: {'X ' * strikes}")
        guess = input("Your guess: ").strip().lower()

        if not guess:
            continue
        if guess == "quit":
            break
        if guess in guessed:
            print("You already guessed that one!")
            continue
        guessed.add(guess)

        hit = next((w for w, _ in answers if w not in revealed and matches(guess, w)), None)
        if hit:
            points = counts[hit]
            revealed.add(hit)
            score += points
            print(f"Survey says... DING! '{hit}' is on the board for {points} points!")
        else:
            strikes += 1
            appearances = counts.get(guess, 0)
            note = f" (it appears {appearances} times, but not in the top {len(answers)})" if appearances else ""
            print(f"Survey says... BZZZT! X{note}")

    if len(revealed) == len(answers):
        print("\nYou cleared the board!")
    elif strikes >= MAX_STRIKES:
        print("\nThree strikes, you're out!")

    print("\nHere's the full board:")
    show_board(answers, {w for w, _ in answers})
    print(f"Final score: {score} out of a possible {sum(c for _, c in answers)}")


def main():
    print("Welcome to WIKI FEUD!")
    while True:
        topic = input("\nPick a topic (or press Enter to quit): ").strip()
        if not topic:
            print("Thanks for playing!")
            return

        try:
            title = find_article(topic)
            if title is None:
                print("Couldn't find a Wikipedia article for that. Try another topic.")
                continue
            print(f"Closest Wikipedia article: {title}")
            counts = count_words(scrape_article(title))
        except requests.RequestException as err:
            print(f"Trouble reaching Wikipedia: {err}")
            continue

        if len(counts) < BOARD_SIZE:
            print("That article is too short to play with. Try another topic.")
            continue

        play(title, counts)


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nThanks for playing!")
