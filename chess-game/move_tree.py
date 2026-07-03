from __future__ import annotations
import chess
from typing import Dict, List
from abc import ABC, abstractmethod


def _connector_span(is_last: bool) -> str:
    """Box-drawing connector for a variation branch: an 'L' shape if
    this is the last sibling at its branch point, a 'T' shape
    otherwise. Wrapped in a fixed-width span so it lines up exactly
    with continuation-line padding regardless of glyph metrics."""
    connector = "\u2514\u2500" if is_last else "\u251c\u2500"
    return f'<span style="display:inline-block; width:28px;">{connector}&nbsp;</span>'

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
    def add_variant(self, move: chess.Move, board: chess.Board) -> None:
        pass

    @abstractmethod
    def get_variants(self) -> List["MoveTree"]:
        pass

    @abstractmethod
    def has_variant(self) -> bool:
        pass

    @abstractmethod
    def select_variant(self, sibling_index: int) -> None:
        pass

    @abstractmethod
    def select_path_to_root(self) -> None:
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
    def get_last_move_played(self) -> chess.Move:
        pass

    @abstractmethod
    def get_variant(self) -> MoveTreeABC:
        pass

    @abstractmethod
    def get_root(self) -> "MoveTree":
        pass

    @abstractmethod
    def get_board(self) -> chess.Board:
        pass

    @abstractmethod
    def render_outline(self, targets: dict, depth: int = 0, prefix: str = "") -> list:
        pass

    @abstractmethod
    def render_table(self, targets: dict) -> list:
        pass


class MoveTree(MoveTreeABC):
    def __init__(self, board: chess.Board, parent=None, id: int = 0) -> None:
        self._parent: MoveTree = parent
        self._main_line: List[chess.Move] = []  # moves along this line (left/right navigation)
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
        move = None
        if self._current_move < len(self._main_line) - 1:
            move = self._main_line[self._current_move + 1]
        return move

    def get_current_move(self) -> chess.Move:
        return self._main_line[self._current_move]
    
    def get_last_move_played(self) -> chess.Move:
        """Like get_current_move(), but returns None instead of
        raising if this node's pointer is at -1 (before any of its
        own moves) -- used for the last-move highlight, which should
        simply show nothing rather than error at the very start of a
        line."""
        if self._current_move < 0:
            return None
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

    def render_outline(self, targets: dict, depth: int = 0, prefix: str = "") -> list:
        """Render this node and its variations as a list of (depth, html)
        lines, in the lichess/chess.com style: variations get their own
        indented line(s), the parent line continues below. Multiple
        sibling variations at the same branch point are rendered one
        after another at the same depth, not nested inside each other.

        `prefix` is the connector-line prefix (box-drawing characters)
        for this node's own first line, carried down from the parent
        so nested variations show a continuation bar ("|  ") before
        their own branch mark.

        `targets` is a dict mutated in place: anchor id (str) -> (node,
        move_index), so the UI layer can map a click back to an exact
        position to jump to.
        """
        lines = []
        board = self._board.copy(stack=True)
        buffer = []
        first_line = True

        def flush():
            nonlocal first_line
            if buffer:
                line_prefix = prefix if first_line else '<span style="display:inline-block; width:28px;"></span>'
                lines.append((depth, line_prefix + " ".join(buffer)))
                buffer.clear()
                first_line = False

        def make_anchor(node, move_index, san):
            anchor_id = str(len(targets))
            targets[anchor_id] = (node, move_index)
            return f'<a name="{anchor_id}" href="{anchor_id}" style="color:#f6f6f6; text-decoration:none;">{san}</a>'

        def child_prefix(is_last):
            return _connector_span(is_last)

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
                for j, sibling in enumerate(siblings):
                    is_last = j == len(siblings) - 1
                    lines.extend(
                        sibling.render_outline(
                            targets, depth + 1, child_prefix(is_last)
                        )
                    )

        flush()

        root_siblings = self._alt_line.get(-1, [])
        for j, sibling in enumerate(root_siblings):
            is_last = j == len(root_siblings) - 1
            lines.extend(
                sibling.render_outline(targets, depth + 1, child_prefix(is_last))
            )

        return lines

    def render_table(self, targets: dict) -> list:
        """Render this node's own main line as chess.com/lichess-style
        rows: (move_number, White cell, Black cell). Variations
        branching off are rendered using the existing render_outline()
        and inserted as a full-width row directly beneath the row they
        branch from, rather than being spliced mid-row.
        """
        rows = []
        board = self._board.copy(stack=True)
        current_row = None

        def make_anchor(move_index, san):
            anchor_id = str(len(targets))
            targets[anchor_id] = (self, move_index)
            return f'<a name="{anchor_id}" href="{anchor_id}" style="color:#f6f6f6; text-decoration:none;">{san}</a>'

        def flush_row():
            nonlocal current_row
            if current_row is not None:
                rows.append(current_row)
                current_row = None

        for i, move in enumerate(self._main_line):
            turn_is_white = board.turn == chess.WHITE
            fullmove_number = board.fullmove_number
            san = board.san_and_push(move)
            move_html = make_anchor(i, san)

            if turn_is_white:
                flush_row()
                current_row = {
                    "type": "row",
                    "move_number": fullmove_number,
                    "white": move_html,
                    "black": None,
                }
            else:
                if current_row is None:
                    current_row = {
                        "type": "row",
                        "move_number": fullmove_number,
                        "white": None,
                        "black": None,
                    }
                current_row["black"] = move_html

            siblings = self._alt_line.get(i, [])
            if siblings:
                flush_row()
                for j, sibling in enumerate(siblings):
                    is_last = j == len(siblings) - 1
                    rows.append(
                        {
                            "type": "variation",
                            "lines": sibling.render_outline(
                                targets, depth=0, prefix=_connector_span(is_last)
                            ),
                        }
                    )

        flush_row()

        root_siblings = self._alt_line.get(-1, [])
        for j, sibling in enumerate(root_siblings):
            is_last = j == len(root_siblings) - 1
            rows.append(
                {
                    "type": "variation",
                    "lines": sibling.render_outline(
                        targets, depth=0, prefix=_connector_span(is_last)
                    ),
                }
            )

        return rows
