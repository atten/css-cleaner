**css_cleaner** is a Python2-tool that removes all unused blocks from CSS file, based on corresponding HTML file.

Usage:
------
    css-cleaner.py [css_path] [html_path]

    ***css_path*** - path to CSS file that should be optimized
    ***html_path*** - path to HTML file, whitch will be used to analyze CSS usage

After analysis, a new optimized CSS file will be generated in the same directory with original CSS file.

You may use diff tools to compare files and check for unwanted changes.


Features:
---------
* Deals with common CSS3 expressions [.#:], selectors [>+~] and @media definion
* Keeps formatting in optimized file as much as possible

Known issues:
-------------
* clears comment strings outside block definions
* does`t proof expressions in square brackets, like [class*="vspace-"], outputs it 'as is'