from __future__ import annotations
import chess
from typing import Dict, List
from abc import ABC, abstractmethod


class MoveTreeABC(ABC):
    @abstractmethod
    def move_forward(self) -> chess.Move:
        pass

    @abstractmethod
    def move_backward(self) -> chess.Move:
        pass

    @abstractmethod
    def move_up(self) -> MoveTreeABC:
        pass

    @abstractmethod
    def move_down(self) -> MoveTreeABC:
        pass

    @abstractmethod
    def add_main(self, move: chess.Move) -> None:
        pass

    @abstractmethod
    def add_variant(self, move: chess.Move) -> None:
        pass

    @abstractmethod
    def has_variant(self) -> bool:
        pass

    @abstractmethod
    def get_next_move(self) -> chess.Move:
        pass

    @abstractmethod
    def get_previous_move(self) -> chess.Move:
        pass

    @abstractmethod
    def get_current_move(self) -> chess.Move:
        pass

    @abstractmethod
    def get_string_repr(self) -> str:
        pass


class MoveTree(MoveTreeABC):
    def __init__(self, board: chess.Board, parent=None) -> None:
        self._parent: MoveTree = parent
        self._main_line: List[chess.Move] = []  # lewo prawo szczala
        self._alt_line: Dict[int, MoveTree] = {}  # gura dul szczala
        self._current_move: int = -1
        self._board: chess.Board = board.copy()

    def move_forward(self) -> chess.Move:
        move = None
        if self._current_move < len(self._main_line) - 1:
            self._current_move += 1
            move = self._main_line[self._current_move]
        return move

    def move_backward(self) -> chess.Move:
        move = None
        if self._current_move >= 0:
            move = self._main_line[self._current_move]
            self._current_move -= 1
        return move

    def move_down(self) -> MoveTreeABC:
        return self._alt_line.get(self._current_move)

    def move_up(self) -> MoveTreeABC:
        return self._parent

    def add_main(self, move: chess.Move) -> None:
        self._main_line.append(move)
        self._current_move = len(self._main_line) - 1

    def add_variant(self, move: chess.Move, board: chess.Board) -> None:
        variant_board = board.copy()
        if self._alt_line.get(self._current_move) is None:
            self._alt_line[self._current_move] = MoveTree(
                parent=self, board=variant_board
            )
            self._alt_line[self._current_move].add_main(move)

    def has_variant(self) -> bool:
        return self._alt_line.get(self._current_move) is not None

    def get_next_move(self) -> chess.Move:
        move = None
        if self._current_move < len(self._main_line) - 1:
            move = self._main_line[self._current_move + 1]
        return move

    def get_current_move(self) -> chess.Move:
        return self._main_line[self._current_move]

    def get_previous_move(self) -> chess.Move:
        move = None
        if self._current_move >= 0:
            move = self._main_line[self._current_move - 1]
        return move

    def get_string_repr(self) -> str:
        board = self._board.copy(stack=True)
        san = []

        for i, move in enumerate(self._main_line):
            if board.turn == chess.WHITE:
                san.append(f"{board.fullmove_number}. {board.san_and_push(move)}")
            elif not san:
                san.append(f"{board.fullmove_number}...{board.san_and_push(move)}")
            else:
                san.append(board.san_and_push(move))
            varanit = self._alt_line.get(i)
            if varanit:
                san.append(f"({varanit.get_string_repr()})")
        return " ".join(san)
