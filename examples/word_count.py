# Simple parallel processing example: read a bunch of files and get the word count.
#
# Functionally, this code will open 4 files at a time (in 4 separate
# processes), feeding the lines of text to one WordCounter emitter. The
# WordCounter will count up how many occurrences of each word there are and
# print the result.
#
# Call this script simply by passing filenames on the command line:
#
#   python word_count.py file1.txt file2.txt file3.txt

from sys import argv
from emitter import Emitter, Open, Iter, Print

class WordCounter(Emitter):
    def setup(self):
        self.word_counts = {}
    def do(self, line):
        for word in line.split():
            self.word_counts[word] = self.word_counts.get(word, 0) + 1
    def teardown(self):
        for word, count in self.word_counts.items():
            self.emit((word, count))

if __name__ == "__main__":
    files_in = argv[1:]
    Iter(files_in).into(Open(processes=4)).into(WordCounter()).into(Print()).execute()
