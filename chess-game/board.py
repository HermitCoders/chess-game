from PyQt6.QtWidgets import QFrame, QGridLayout, QWidget
from collections import defaultdict
import chess

from piece import PieceItem


class ChessBoard(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.SQUARE_SIZE = 100
        self.SQUARES_NUMBER = 64
        # self.board = chess.Board("rnbqkbnr/pp1p1ppp/8/2pPp3/8/8/PPP1PPPP/RNBQKBNR w KQkq c6 0 1")
        self.board = chess.Board()
        self.previous_board = None

        self.square_colors = {"light": "#e6e6e6", "dark": "#a6a6a6"}
        self.check_colors = {"light": "#e2514c", "dark": "#d74840"}
        self.highlight_colors = {"light": "#00e6b8", "dark": "#00cca3"}
        self.secondary_colors = {"frame": "#262626"}

        self.highlighted_squares = set()
        self.framed_squares = set()
        self.checked_squares = set()
        self.previous_sq_idx = None
        self.possible_moves = None
        self.possible_promotions = None
        self.move_made = False
        self.pieces_items = {}

        self.setContentsMargins(0, 0, 0, 0)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.draw_board()
        self.draw_pieces()
        self.setLayout(self.layout)

    def draw_board(self):
        for sqr_index in range(self.SQUARES_NUMBER):
            square = QWidget(self)
            square.setFixedSize(self.SQUARE_SIZE, self.SQUARE_SIZE)
            square.setObjectName(chess.SQUARE_NAMES[sqr_index])
            self.set_square_style(sqr_index)
            col, row = self.get_square_coords(sqr_index)
            self.layout.addWidget(square, row, col)

    def draw_pieces(self):
        for sqr_index in range(self.SQUARES_NUMBER):
            col, row = self.get_square_coords(sqr_index)
            piece: PieceItem = self.board.piece_at(sqr_index)
            if piece:
                piece_label = PieceItem(self, piece)
                self.layout.addWidget(piece_label, row, col)
                self.pieces_items[sqr_index] = piece_label

    def update_pieces(self, next_board):
        for sqr_index in range(self.SQUARES_NUMBER):
            if self.previous_board.piece_at(sqr_index) != next_board.piece_at(sqr_index):
                col, row = self.get_square_coords(sqr_index)

                old_piece: PieceItem = self.pieces_items.get(sqr_index)
                if old_piece:
                    self.layout.removeWidget(old_piece)
                    del self.pieces_items[sqr_index]
                    old_piece.deleteLater()
                    old_piece.setParent(None)

                piece: chess.Piece = next_board.piece_at(sqr_index)
                if piece:
                    piece_label = PieceItem(self, piece)
                    self.layout.addWidget(piece_label, row, col)
                    self.pieces_items[sqr_index] = piece_label

    def get_square_coords(self, square_index):
        col = chess.square_file(square_index)
        row = 7 - chess.square_rank(square_index)
        return col, row

    def get_square_color(self, square_index):
        col, row = self.get_square_coords(square_index)
        return "light" if row % 2 == col % 2 else "dark"

    def set_square_style(self, square_index, square_style=None):
        square = self.findChild(QWidget, chess.SQUARE_NAMES[square_index])
        color = self.get_square_color(square_index)
        if square_style == "highlight":
            if square_index not in self.highlighted_squares:
                style = f"background-color: {self.highlight_colors[color]}"
                self.highlighted_squares.add(square_index)
            else:
                style = f"background-color: {self.square_colors[color]}"
                self.highlighted_squares.remove(square_index)
        elif square_style == "frame":
            style = f'background-color: {self.square_colors[color]}; border: 4px solid {self.secondary_colors["frame"]}'
            self.framed_squares.add(square_index)
        elif square_style == "check":
            style = f"background-color: {self.check_colors[color]}"
        else:
            style = f"background-color: {self.square_colors[color]}"
        square.setStyleSheet(style)

    def unhighlight_all(self):
        for sqr_index in self.highlighted_squares.union(self.framed_squares):
            self.set_square_style(sqr_index)
        self.highlighted_squares = set()

    def unframe_all(self):
        for sqr_index in self.framed_squares:
            self.set_square_style(sqr_index)
        self.framed_squares = set()

    def uncheck_all(self):
        for sqr_index in self.checked_squares:
            self.set_square_style(sqr_index)
        self.checked_squares = set()

    def get_possible_moves(self):
        possible_moves = defaultdict(list)
        possible_promotions = defaultdict(list)

        for pos in list(self.board.legal_moves):
            if pos.promotion:
                possible_promotions[pos.from_square].append(pos.to_square)
            possible_moves[pos.from_square].append(pos.to_square)

        self.possible_moves = possible_moves
        self.possible_promotions = possible_promotions

    def mouse_position_to_square_index(self, mouse_position):
        col = int(mouse_position.x() // self.SQUARE_SIZE)
        row = 7 - int(mouse_position.y() // self.SQUARE_SIZE)
        square_index = chess.square(col, row)
        return square_index

    def draw_possible_moves(self, square_index):
        self.get_possible_moves()
        if square_index in self.possible_moves:
            self.set_square_style(square_index, "frame")
            for sq_idx in self.possible_moves[square_index]:
                self.set_square_style(sq_idx, "frame")

    def move_piece(self, square_index):
        if (
            self.previous_sq_idx in self.possible_moves.keys()
            and square_index in self.possible_moves[self.previous_sq_idx]
        ):
            if (
                self.previous_sq_idx in self.possible_promotions.keys()
                and square_index in self.possible_promotions[self.previous_sq_idx]
            ):
                move = chess.Move(self.previous_sq_idx, square_index, promotion=5)
            else:
                move = chess.Move(self.previous_sq_idx, square_index)
            self.previous_board = self.board.copy()
            self.board.push(move)
            self.move_made = True
            self.update_pieces(self.board)
        else:
            self.move_made = False
