from __future__ import annotations

import random
from typing import TYPE_CHECKING, TypeAlias

from ..core.generator import Generator, WordFitError, retry
from ..core.word import Direction, Word
from ..utils import in_bounds

if TYPE_CHECKING:  # pragma: no cover
    from ..core import GameType
    from ..core.game import Puzzle


Fit: TypeAlias = tuple[str, list[tuple[int, int]]]
Fits: TypeAlias = list[tuple[str, list[tuple[int, int]]]]


class WordSearchGenerator(Generator):
    """Default generator for standard WordSearch puzzles."""

    def __init__(self, alphabet = [], seed: int = 0) -> None:
      """Initialize Generator."""
      self.alphabet = alphabet
      self.positions = []

    def generate(self, game: GameType) -> Puzzle:
        self.game = game
        self.puzzle = game._build_puzzle(game.size, "")
        self.fill_words()
        if any(word.placed for word in game.words):
            self.fill_blanks()
        return self.puzzle

    def no_duped_words(
        self, puzzle: Puzzle, char: str, position: tuple[int, int], current_word: str | None = None
    ) -> bool:
        """Make sure that adding `char` at `position` will not create a
        duplicate of any word already placed in the puzzle."""
        placed_word_strings = []
        for word_obj in self.game.words:
            if word_obj.placed:
                if current_word and (
                    current_word in word_obj.text or word_obj.text in current_word
                ):
                    continue
                placed_word_strings.append(word_obj.text)
        if not placed_word_strings:
            return True

        # calculate how large of a search radius to check
        radius = len(max(placed_word_strings, key=len)) if placed_word_strings else 0
        # track each directional fragment of characters
        fragments = self.capture_fragments(puzzle, radius, position)
        # check to see if any duped words are now present
        before_ct = after_ct = 0
        for word_text in placed_word_strings:
            for before in fragments:
                # remove the current word
                # after = before.replace(current_word, "")
                after = before.replace("*", char)
                if word_text in before or word_text[::-1] in before:
                    before_ct += 1
                if word_text in after or word_text[::-1] in after:
                    after_ct += 1
        return before_ct == after_ct

    def capture_fragments(self, puzzle: Puzzle, radius: int, position: tuple[int, int]) -> list[str]:
        row, col = position
        fragments = []
        height = width = self.game.size

        # cardinal direction ranges to capture
        ranges = [
            (
                range(row - (radius - 1), row + radius),
                range(col - (radius - 1), col + radius),
            ),  # top-left to bottom-right
            (
                [row] * (radius * 2 - 1),
                range(col - (radius - 1), col + radius),
            ),  # left to right
            (
                range(row - (radius - 1), row + radius),
                [col] * (radius * 2 - 1),
            ),  # top to bottom
            (
                range(row + (radius - 1), row - radius, -1),
                range(col - (radius - 1), col + radius),
            ),  # bottom-left to top-right
        ]

        for row_range, col_range in ranges:
            fragment = ""
            for r, c in zip(row_range, col_range, strict=False):
                if not in_bounds(c, r, width, height):
                    continue
                fragment += "*" if (r, c) == (row, col) else puzzle[r][c]
            fragments.append(fragment)
        return fragments

    def test_a_fit(
        self,
        puzzle: Puzzle,
        word: str,
        position: tuple[int, int],
        direction: Direction,
    ) -> list[tuple[int, int]]:
        """Test if word fits in the puzzle at the specified
        coordinates heading in the specified direction."""
        coordinates = []
        row, col = position
        # iterate over each letter in the word
        for char in word:
            # if coordinates are off of puzzle cancel fit test
            if not in_bounds(col, row, len(puzzle), len(puzzle)):
                return []
            # first check if the spot is inactive on the mask
            if self.game.mask[row][col] == self.game.INACTIVE:
                return []
            # if the current puzzle space is empty or if letters don't match
            if puzzle[row][col] != "" and puzzle[row][col] != char:
                return []
            coordinates.append((row, col))
            # adjust the coordinates for the next character
            row += direction.r_move
            col += direction.c_move
        return coordinates

    def func_test_a_fit(
        self,
        puzzle: Puzzle,
        word: str,
        position: tuple[int, int],
        direction: Direction,
    ) -> list[tuple[int, int]]:
        """Test if word fits in the puzzle at the specified
        coordinates heading in the specified direction."""
        coordinates = []
        row, col = position
        # iterate over each letter in the word
        for char in word:
            # if coordinates are off of puzzle cancel fit test
            if not in_bounds(col, row, len(puzzle), len(puzzle)):
                return []
            # first check if the spot is inactive on the mask
            if self.game.mask[row][col] == self.game.INACTIVE:
                return []
            # if the current puzzle space is empty or if letters don't match
            if puzzle[row][col] != "" and puzzle[row][col] != char:
                return []
            coordinates.append((row, col))
            # adjust the coordinates for the next character
            row += direction.r_move
            col += direction.c_move
        return coordinates

    def find_a_fit(self, word: Word, position: tuple[int, int]) -> Fit:
        """Look for random place in the puzzle where `word` fits."""
        fits: Fits = []
        # check all directions for level
        directions = secret_directions = self.game.directions
        if hasattr(self.game, "secret_directions"):
            secret_directions = self.game.secret_directions
        for d in secret_directions if word.secret else directions:
            coords = self.test_a_fit(word.text, position, d)
            if coords:
                fits.append((Direction(d).name, coords))
        # if the word fits, pick a random fit for placement
        if not fits:
            raise WordFitError
        return random.choice(fits)

    def func_find_a_fit(self, puzzle: Puzzle, word: Word, position: tuple[int, int]) -> Fit:
        """Look for random place in the puzzle where `word` fits."""
        fits: Fits = []
        # check all directions for level
        directions = secret_directions = self.game.directions
        if hasattr(self.game, "secret_directions"):
            secret_directions = self.game.secret_directions
        for d in secret_directions if word.secret else directions:
            coords = self.func_test_a_fit(puzzle, word.text, position, d)
            if coords:
                fits.append((Direction(d).name, coords))
        # if the word fits, pick a random fit for placement
        if not fits:
            raise WordFitError
        return random.choice(fits)

    def fill_words(self) -> None:
        """Fill puzzle with the supplied `words`.
        Some words will be skipped if they don't fit."""
        # try to place each word on the puzzle
        placed_words_texts: list[str] = []
        hidden_words = [word for word in self.game.words if not word.secret]
        secret_words = [word for word in self.game.words if word.secret]

        if not self.positions:
            for i in range(0, len(self.puzzle)):
                for j in range(len(self.puzzle) if self.puzzle else 0):
                    self.positions.append((i, j))

        words_to_place = hidden_words + secret_words
        if not words_to_place:
            if any(words.placed for word in self.game.words):
                self.fill_blanks()
            return

        directions_list = list(self.game.directions)
        initial_puzzle_state = [row[:] for row in self.puzzle]
        stack = [{
            "puzzle": initial_puzzle_state,
            "word_obj": words_to_place.pop(0),
            "positions_to_try": random.sample(self.positions, len(self.positions)),
            "current_pos_directions_to_try": [],
        }]

        solution_found = False
        while stack:
            current_state = stack[-1]

            current_word_obj = current_state["word_obj"]
            current_puzzle_layout = current_state["puzzle"]

            if not current_state["current_pos_directions_to_try"]:
                if not current_state["positions_to_try"]:
                    words_to_place.insert(0, current_word_obj)
                    current_word_obj.start_row = -1
                    current_word_obj.start_column = -1
                    current_word_obj.coordinates = None
                    stack.pop()
                    continue

                current_pos = current_state["positions_to_try"].pop()
                current_state["current_pos_tuple"] = current_pos
                current_state["current_pos_directions_to_try"] = random.sample(directions_list, len(directions_list))

            if not current_state["current_pos_directions_to_try"]:
                stack.pop()
                continue

            direction_to_try = current_state["current_pos_directions_to_try"].pop(0)
            position_to_try = current_state["current_pos_tuple"]

            new_puzzle_state_after_placement = self.func_try_to_fit_word_at(
                current_puzzle_layout,
                current_word_obj,
                position_to_try,
                direction_to_try,
            )

            if new_puzzle_state_after_placement:
                if not words_to_place:
                    self.puzzle = new_puzzle_state_after_placement
                    solution_found = True
                    break
                else:
                    next_word_to_place = words_to_place.pop(0)
                    stack.append({
                        "puzzle": new_puzzle_state_after_placement,
                        "word_obj": next_word_to_place,
                        "positions_to_try": random.sample(self.positions, len(self.positions)),
                        "current_pos_directions_to_try": [],
                    })

        if not solution_found:
            print(f"Warning: Could not place all words. Remaining: {[w.text for w in words_to_place]}")

        if any(word.placed for word in self.game.words) or solution_found:
            self.fill_blanks()


    def add_all_permutations(self, word: Word):
        """Add all permutations of a word with current puzzle state
           to the stack."""
        to_stack = []
        puzzle_state = self.puzzle
        for p in self.positions:
            for d in self.game.directions:
                if self.test_a_fit(word.text, p, d):
                    to_stack.append({
                      "puzzle": puzzle_state,
                      "word": word,
                      "position": p,
                      "direction": d,
                    })
        random.shuffle(to_stack)
        return to_stack

    def try_to_fit_word_at(self, word: Word, pos) -> bool:
        """Try to fit `word` at a given coordinate"""
        # no need to continue if position isn't available
        if self.puzzle[pos[0]][pos[1]] != "" and self.puzzle[pos[0]][pos[1]] != word.text[0]:
            return False
        if self.game.mask[pos[0]][pos[1]] == self.game.INACTIVE:
            return False
        # try and find a directional fit using the starting coordinates if not INACTIVE
        try:
            d, coords = self.find_a_fit(word, (pos[0], pos[1]))
        except:
            return False

        # place word characters at fit coordinates
        previous_chars = []  # track previous to backtrack on WordFitError
        for i, char in enumerate(word.text):
            check_row = coords[i][0]
            check_col = coords[i][1]
            previous_chars.append(self.puzzle[check_row][check_col])

            # no need to check for dupes if characters are the same
            if char == self.puzzle[check_row][check_col]:
                continue
            # make sure placed character doesn't cause a duped word in the puzzle
            if self.no_duped_words(char, (check_row, check_col), word.text):
                self.puzzle[check_row][check_col] = char
            else:
                # if a duped word was created put previous characters back in place
                for n, previous_char in enumerate(previous_chars):
                    self.puzzle[coords[n][0]][coords[n][1]] = previous_char
                # raise WordFitError
                pass # Not important hopefully

        # update word placement info
        word.start_row = pos[0]
        word.start_column = pos[1]
        word.direction = Direction[d]
        word.coordinates = coords

        return word.placed

    def func_try_to_fit_word_at(self, current_puzzle_state: Puzzle, word: Word, pos, direction: Direction) -> Puzzle | None:
        """Try to fit `word` at a given coordinate"""
        coords = self.test_a_fit(current_puzzle_state, word.text, pos, direction)
        if not coords:
            return None

        prospective_puzzle = [row[:] for row in current_puzzle_state]

        for i, char_to_place in enumerate(word.text):
            r, c = coords[i]

            char_before_placement_attempt = prospective_puzzle[r][c]

            if char_before_placement_attempt == char_to_place:
                continue

            if not self.no_duped_words(prospective_puzzle, char_to_place, (r, c), word.text):
                return None

            prospective_puzzle[r][c] = char_to_place

        # update word placement info
        word.start_row = pos[0]
        word.start_column = pos[1]
        word.direction = direction
        word.coordinates = coords

        return prospective_puzzle

    @retry(1000)
    def try_to_fit_word(self, word: Word) -> bool:
        """Try to fit `word` at randomized coordinates.
        @retry wrapper controls the number of attempts"""
        row = random.randint(0, len(self.puzzle) - 1)
        col = random.randint(0, len(self.puzzle) - 1)

        # no need to continue if random coordinate isn't available
        if self.puzzle[row][col] != "" and self.puzzle[row][col] != word.text[0]:
            raise WordFitError
        if self.game.mask[row][col] == self.game.INACTIVE:
            raise WordFitError

        # try and find a directional fit using the starting coordinates if not INACTIVE
        d, coords = self.find_a_fit(word, (row, col))

        # place word characters at fit coordinates
        previous_chars = []  # track previous to backtrack on WordFitError
        for i, char in enumerate(word.text):
            check_row = coords[i][0]
            check_col = coords[i][1]
            previous_chars.append(self.puzzle[check_row][check_col])

            # no need to check for dupes if characters are the same
            if char == self.puzzle[check_row][check_col]:
                continue
            # make sure placed character doesn't cause a duped word in the puzzle
            if self.no_duped_words(char, (check_row, check_col), word.text):
                self.puzzle[check_row][check_col] = char
            else:
                # if a duped word was created put previous characters back in place
                for n, previous_char in enumerate(previous_chars):
                    self.puzzle[coords[n][0]][coords[n][1]] = previous_char
                raise WordFitError

        # update word placement info
        word.start_row = row
        word.start_column = col
        word.direction = Direction[d]
        word.coordinates = coords

        return word.placed

    def fill_blanks(self) -> None:
        """Fill empty puzzle spaces with random characters."""
        # iterate over the entire puzzle

        size = len(self.puzzle)
        for row in range(size):
            for col in range(size):
                # if the current spot is empty fill with random character
                if (
                    self.puzzle[row][col] == ""
                    and self.game.mask[row][col] == self.game.ACTIVE
                ):
                    while True:
                        random_char = random.choice(self.alphabet)
                        if self.no_duped_words(self.puzzle, random_char, (row, col)):
                            self.puzzle[row][col] = random_char
                            break

