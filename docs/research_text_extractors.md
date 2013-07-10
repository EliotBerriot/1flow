
# Research text extractors

Test URL:

http://www.vcsphoto.com/blog/2013/05/malibu-engagement-session-jennifer-and-scott.html


## boilerpipy

    pip install -e git+https://github.com/Harshavardhana/boilerpipy.git@master#egg=boilerpipy-dev

Cons:

- old chardet
- old urllib2

Try:
    readability -u http://www.vcsphoto.com/blog/2013/05/malibu-engagement-session-jennifer-and-scott.html
    2013-07-09 14:26:18 error getting summary: global name 'compat_str' is not defined
    Error in printing the extracted html () exceptions must be old-style classes or derived from BaseException, not NoneType


## Buriy's fast readability

    pip install -e git+https://github.com/buriy/python-readability@master#egg=readability-dev

Try:

    python /Users/olive/.virtualenvs/1flow/src/readability/readability/readability.py -u http://www.vcsphoto.com/blog/2013/05/malibu-engagement-session-jennifer-and-scott.html

Cons:

- we get an empty page with only the title, not even the text, nor images links.


## Boilerpot

    pip install -e git+https://github.com/jackdied/boilerpot@master#egg=boilerpot-dev


Cons:

- no test call possible via CLI, we have to do the requests part ourselves
- extracts only TEXT (not HTML)

Run:

    http://127.0.0.1:8888/9cea9375-1097-4ca6-9554-9a7229a13b48


## BoilerPy


    pip install -e git+https://github.com/sammyer/BoilerPy.git@master#egg=boilerpy-dev

Cons:

- returns text only
- instanciate all extractors in the same file even if we don't use them.

Run:
    http://127.0.0.1:8888/7e85df97-490a-4101-9703-a0fb012fa198


## Another readability

    pip install -e git+https://github.com/reorx/readability.git@master#egg=readability-dev

Cons:

- seems to take the full HTML page.


Run:

    http://127.0.0.1:8888/956f4e1b-4d7e-4e91-a460-dc656be879ab


## David Cramer's decruft


    pip install -e git+https://github.com/dcramer/decruft.git@master#egg=decruft-dev

Try:
    python /Users/olive/.virtualenvs/1flow/src/decruft/decruft/decruft.py -u http://www.vcsphoto.com/blog/2013/05/malibu-engagement-session-jennifer-and-scott.html


Cons:

- seems to pull all the page.

## Soup-strainer


pip install -e git+https://github.com/rcarmo/soup-strainer.git@master#egg=soup-strainer-dev
