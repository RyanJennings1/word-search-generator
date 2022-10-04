import os
import random
import re
import uuid
from pathlib import Path

import pytest
from PyPDF2 import PdfFileReader

from word_search_generator import WordSearch, config, export, utils

WORDS = "dog, cat, pig, horse, donkey, turtle, goat, sheep"


def test_export_pdf_puzzles(tmp_path):
    """Export a bunch of puzzles as PDF and make sure they are all 1-page."""
    sizes = [s for s in range(config.min_puzzle_size, config.max_puzzle_size)]
    puzzles = []
    pages = set()
    for size in sizes:
        words = utils.get_random_words(
            random.randint(config.min_puzzle_words, config.max_puzzle_words)
        )
        level = random.randint(1, 3)
        puzzle = WordSearch(words, level=level, size=size)
        path = Path.joinpath(tmp_path, f"{uuid.uuid4()}.pdf")
        puzzle.save(path)
        puzzles.append(path)
    for p in puzzles:
        pdf = PdfFileReader(open(p, "rb"))
        pages.add(pdf.getNumPages())
    assert pages == {1}


def test_export_pdf_puzzle_with_solution(tmp_path):
    """Make sure a puzzle exported with the solution is 2 pages."""
    puzzle = WordSearch(WORDS)
    path = Path.joinpath(tmp_path, f"{uuid.uuid4()}.csv")
    puzzle.save(path, solution=True)
    found = False
    with open(path, "r") as fp:
        lines = fp.readlines()
        for row in lines:
            if row.find("SOLUTION") == 0:
                found = True
                break
    assert found


def test_export_csv_puzzle_with_solution(tmp_path):
    """Make sure a puzzle exported with the solution is 2 pages."""
    sizes = [s for s in range(config.min_puzzle_size, config.max_puzzle_size)]
    puzzles = []
    pages = set()
    for size in sizes:
        words = utils.get_random_words(
            random.randint(config.min_puzzle_words, config.max_puzzle_words)
        )
        level = random.randint(1, 3)
        puzzle = WordSearch(words, level=level, size=size)
        path = Path.joinpath(tmp_path, f"{uuid.uuid4()}.pdf")
        puzzle.save(path, solution=True)
        puzzles.append(path)
    for p in puzzles:
        pdf = PdfFileReader(open(p, "rb"))
        pages.add(pdf.getNumPages())
    assert pages == {2}


def test_export_overwrite_file_error(tmp_path):
    """Try to export a puzzle with the name of a file that is already present."""
    path = Path.joinpath(tmp_path, "test.pdf")
    path.touch()
    with pytest.raises(FileExistsError):
        export.validate_path(path)


def test_export_pdf_no_extension_provided(tmp_path):
    """Try to export a puzzle with no extension on the path."""
    puzzle = WordSearch(WORDS)
    path = Path.joinpath(tmp_path, "test")
    puzzle.save(path)
    correct_path = path.with_suffix(".pdf")
    assert correct_path.exists()


@pytest.mark.skipif(os.name == "nt", reason="need to figure out")
def test_export_pdf_os_error():
    """Try to export a puzzle to a place you don't have access to."""
    puzzle = WordSearch(WORDS)
    with pytest.raises(OSError):
        puzzle.save("/test.pdf")


@pytest.mark.skipif(os.name == "nt", reason="need to figure out")
def test_export_csv_os_error():
    """Try to export a puzzle to a place you don't have access to."""
    puzzle = WordSearch(WORDS)
    with pytest.raises(OSError):
        puzzle.save("/test.csv")


def test_csv_export_without_solution(tmp_path):
    puzzle = WordSearch(WORDS)
    path = Path.joinpath(tmp_path, "test.csv")
    puzzle.save(path, solution=False)
    with open(path, "r") as f:
        data = f.read()
    assert not re.findall("\nSOLUTION\n", data)


def test_csv_export_with_solution(tmp_path):
    puzzle = WordSearch(WORDS)
    path = Path.joinpath(tmp_path, "test.csv")
    puzzle.save(path, solution=True)
    with open(path, "r") as f:
        data = f.read()
    assert re.findall("\nSOLUTION\n", data)
