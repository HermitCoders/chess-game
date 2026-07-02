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
    def get_variant(self) -> MoveTreeABC:
        pass


class MoveTree(MoveTreeABC):
    def __init__(self, board: chess.Board, parent=None, id: int = 0) -> None:
        self._parent: MoveTree = parent
        self._main_line: List[chess.Move] = []  # lewo prawo szczala
        self._alt_line: Dict[int, List[MoveTree]] = {}  # move index -> list of sibling variations
        self._selected_variant: Dict[int, int] = {}  # move index -> index into that list, "currently active" sibling
        self._current_move: int = -1
        self._board: chess.Board = board.copy()
        self.id = id

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
        return self.get_variant()

    def move_up(self) -> MoveTreeABC:
        return self._parent

    def add_main(self, move: chess.Move) -> None:
        self._main_line.append(move)
        self._current_move = len(self._main_line) - 1

    def add_variant(self, move: chess.Move, board: chess.Board) -> None:
        siblings = self._alt_line.setdefault(self._current_move, [])

        for i, sibling in enumerate(siblings):
            if sibling.get_current_move() == move:
                # This exact variation already exists -- just select it
                # rather than creating a duplicate.
                self._selected_variant[self._current_move] = i
                return

        variant_board = board.copy()
        mt = MoveTree(parent=self, board=variant_board, id=self.id + 1)
        mt.add_main(move)
        siblings.append(mt)
        self._selected_variant[self._current_move] = len(siblings) - 1

    def get_variants(self) -> List["MoveTree"]:
        return self._alt_line.get(self._current_move, [])

    def has_variant(self) -> bool:
        return bool(self.get_variants())

    def select_variant(self, sibling_index: int) -> None:
        """Mark which sibling variation is 'active' at the current move,
        so keyboard navigation (move_down) follows it."""
        self._selected_variant[self._current_move] = sibling_index
    
    def select_path_to_root(self) -> None:
        """Walk up from this node to the root, marking at each parent
        which child (self, or the ancestor leading to self) is the
        'selected' sibling at that branch point -- so keyboard
        navigation stays consistent with wherever you just jumped to."""
        node = self
        while node._parent is not None:
            parent = node._parent
            for move_index, siblings in parent._alt_line.items():
                if node in siblings:
                    parent._selected_variant[move_index] = siblings.index(node)
                    break
            node = parent

    def get_next_move(self) -> chess.Move:
        print('GET NEXT MOVE CURRENT MOVE', self._current_move)
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
    
    def get_root(self) -> "MoveTree":
        node = self
        while node._parent is not None:
            node = node._parent
        return node

    def get_variant(self) -> MoveTreeABC:
        siblings = self.get_variants()
        if not siblings:
            return None
        idx = min(self._selected_variant.get(self._current_move, 0), len(siblings) - 1)
        return siblings[idx]
    
    def get_board(self) -> chess.Board:
        """Reconstruct the actual board position for this node.

        Starts from this node's stored base position (the board as it was
        when this line/variation began) and replays its own main line up
        to (and including) the current move pointer.
        """
        board = self._board.copy()
        for move in self._main_line[: self._current_move + 1]:
            board.push(move)
        return board

    def render_outline(self, targets: dict, depth: int = 0) -> list:
        """Render this node and its variations as a list of (depth, html)
        lines, in the lichess/chess.com style: variations get their own
        indented line(s), the parent line continues below. Multiple
        sibling variations at the same branch point are rendered one
        after another at the same depth, not nested inside each other.

        `targets` is a dict mutated in place: anchor id (str) -> (node,
        move_index), so the UI layer can map a click back to an exact
        position to jump to.
        """
        lines = []
        board = self._board.copy(stack=True)
        buffer = []

        def flush():
            if buffer:
                lines.append((depth, " ".join(buffer)))
                buffer.clear()

        def make_anchor(node, move_index, san):
            anchor_id = str(len(targets))
            targets[anchor_id] = (node, move_index)
            return f'<a name="{anchor_id}" href="{anchor_id}" style="color:#f6f6f6; text-decoration:none;">{san}</a>'

        for i, move in enumerate(self._main_line):
            turn_is_white = board.turn == chess.WHITE
            fullmove_number = board.fullmove_number
            san = board.san_and_push(move)
            move_html = make_anchor(self, i, san)

            if turn_is_white:
                buffer.append(f"{fullmove_number}. {move_html}")
            elif not buffer:
                buffer.append(f"{fullmove_number}...{move_html}")
            else:
                buffer.append(move_html)

            siblings = self._alt_line.get(i, [])
            if siblings:
                flush()
                for sibling in siblings:
                    lines.extend(sibling.render_outline(targets, depth + 1))

        flush()

        for sibling in self._alt_line.get(-1, []):
            lines.extend(sibling.render_outline(targets, depth + 1))

        return lines
