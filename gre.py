import json
import sys
import tty
import termios
import arrow
import random
import os
import eggshell
import requests
from xtermcolor import colorize

alphabet = 'abcdefghijklmnopqrstuvwxyz'
main_menu = """Select mode:

(1) All words, ranked
(2) All words, unranked
(3) Only one starting letter, ranked
(4) Only one starting letter, unranked
(5) From word list, ranked
(6) From word list, unranked

(R)esults
re(L)oad dictionary
Toggle (W)ordsAPI
(Q)uit

> """

quiz_menu = """
Quiz mode options:

(M)ain menu
(Q)uit
(S)peak word
(H)elp (or ?)
"""

words_api_enabled = False
words_api_token = ''

def words_api_definitions(word):
    r = requests.get('https://www.wordsapi.com/words/{word}?accessToken={token}'.format(
        word=word,
        token=words_api_token
    ))
    j = json.loads(r.text)
    definitions = j['results']
    print('\n{}'.format(colorize('WordsAPI Definitions:', ansi=9)))
    for i, definition in enumerate(definitions):
        print('  {}.  ({}) {}'.format(i+1, colorize(definition['partOfSpeech'] if 'partOfSpeech' in definition else 'N/A', ansi=6), definition['definition']))
    print('')

def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    print(ch)
    return ch

def get_words():
    words = {}
    with open('words.txt') as fp:
        for line in fp.read().split('\n'):
            line = line.strip()
            if len(line) > 0:
                (word, definition) = line.split(' - ')
                words[word.lower().strip()] = definition.strip()
    return words

def prompt(question, choices, incorrect=None):
    while True:
        sys.stdout.write(question)
        sys.stdout.flush()
        ch = getch().lower()
        if ch in choices or ord(ch) in choices:
            return ch
        if incorrect is not None:
            print(incorrect)

def parse_entry(entry):
    date = arrow.get(entry[:19], 'YYYY-MM-DD HH:mm:ss')
    parts = entry[20:].split(',')
    word = parts[0].replace('word=', '')
    correct = True if parts[1].replace('correct=', '') == 'y' else False
    return (date, word, correct)

def results():
    with open('results.txt') as fp:
        entries = list(map(parse_entry, filter(lambda x: len(x), fp.read().split('\n'))))
    count = {
      'correct': 0,
      'incorrect': 0,
      'total': len(entries)
    }
    cards_by_date = {}
    for (date, word, correct) in entries:
        if correct: count['correct'] += 1
        if not correct: count['incorrect'] += 1
        if date.format('YYYY-MM-DD') not in cards_by_date:
            cards_by_date[date.format('YYYY-MM-DD')] = 1
        else:
            cards_by_date[date.format('YYYY-MM-DD')] += 1
    print('Total flash cards: {}'.format(count['total']))
    print('Correct: {}'.format(count['correct']))
    print('Incorrect: {}'.format(count['incorrect']))
    print('Flash cards today: {}'.format(cards_by_date[arrow.now('US/Eastern').format('YYYY-MM-DD')]))

def get_quiz_words(dictionary, number):
    if number != -1:
        all_words = list(dictionary.keys())
        words = []
        random.seed()
        for i in range(number):
            word = random.choice(all_words)
            all_words.remove(word)
            words.append(word)
        return words
    else:
        return list(dictionary.keys())

def quiz(dictionary, number, ranked=False):
    quiz_words = get_quiz_words(dictionary, number)
    quiz_words_iteration = []
    if len(quiz_words) == 0:
      sys.exit('No words to quiz')
    print(quiz_menu)
    print(colorize('Set contains {} words:'.format(len(quiz_words)), ansi=4))
    print(', '.join(quiz_words))
    while True:
        if len(quiz_words_iteration) == 0:
            quiz_words_iteration = list(quiz_words) # Copy
            print(colorize("Reloading words", ansi=4))
        word = random.choice(quiz_words_iteration)
        quiz_words_iteration.remove(word)
        while True:
            number = len(quiz_words) - len(quiz_words_iteration)
            question = "{}. {} [enter/q/m/h/s] ".format(number, colorize(word, ansi=1))
            ch = prompt(question, ['q', 'm', 'h', 's', 13])
            if ch == 'q':
                sys.exit(0)
            elif ch == 'h':
                print(quiz_menu)
                continue
            elif ch == 'm':
                return
            elif ch == 's':
                (rc, out, err) = eggshell.run('say {}'.format(word))
                continue
            elif ord(ch) == 13:
                print(colorize(dictionary[word], ansi=2))
                if words_api_enabled:
                    words_api_definitions(word)
            break
        if ranked:
            correct = prompt("Correct? [y/n/s] ", ['y', 'n', 's'])
            if correct != 's':
                now = arrow.now('US/Eastern')
                with open('results.txt', 'a') as fp:
                    fp.write('{} word={},correct={}\n'.format(now.format('YYYY-MM-DD HH:mm:ss'), word, correct))
    print(json.dumps(words, indent=4))
    print(ranked)

def menu():
    while True:
        words = get_words()
        sys.stdout.write(main_menu)
        sys.stdout.flush()
        ch = getch().lower()

        if ch in list('34'):
            letter = prompt("Which letter? ", list(alphabet))
            subset_words = {word: definition for word, definition in words.items() if word[0] == letter.lower()}

        if ch in list('56'):
            lists = [x for x in os.listdir('.') if x.endswith('.list')]
            for i, word_list  in enumerate(lists):
                print('({}) {}'.format(i+1, word_list))
            index = prompt("Which list? ", list(map(str, list(range(1, len(lists) + 1)))))
            with open(lists[int(index) - 1]) as fp:
                list_words = [x.lower().strip() for x in fp.read().split('\n') if len(x.strip()) > 0]
            for word in list_words:
                if word not in words:
                    print(colorize("{} is not in the dictionary".format(word), ansi=1))
            subset_words = {word: definition for word, definition in words.items() if word in list_words}

        if ch in list('123456'):
            number = input("How many words to quiz? [all] ").strip()
            try:
                number = int(number) if len(number) else -1
            except ValueError:
                print(colorize("Must be numeric", ansi=1))
                continue

        if ch == '1':
            quiz(words, number, ranked=True)
        elif ch == '2':
            quiz(words, number, ranked=False)
        elif ch == '3':
            quiz(subset_words, number, ranked=True)
        elif ch == '4':
            quiz(subset_words, number, ranked=False)
        elif ch == '5':
            quiz(subset_words, number, ranked=True)
        elif ch == '6':
            quiz(subset_words, number, ranked=False)
        elif ch == 'r':
            results()
            prompt('[enter]', [13])
        elif ch == 'l':
            words = get_words()
            print(colorize('Dictionary reloaded.', ansi=4))
        elif ch == 'w':
            global words_api_enabled, words_api_token
            words_api_enabled = not words_api_enabled
            print(colorize('WordsAPI {}'.format('Enabled' if words_api_enabled else 'Disabled'), ansi=4))
            if not words_api_token and words_api_enabled:
                words_api_token = input("WordsAPI token: ")
        elif ch == 'q':
            sys.exit(0)

if __name__ == '__main__':
    menu()
