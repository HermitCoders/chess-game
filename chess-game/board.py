import sys
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QWidget,
    QGraphicsView,
)
from PyQt6.QtGui import QPalette, QColor, QPainter, QBrush, QPen
from PyQt6.QtCore import Qt, QRegularExpression, QRect

import chess
from piece import PieceItem
from collections import defaultdict

sq_size = 100


class ChessBoard(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.sq_size = sq_size
        # self.board = chess.Board("5k2/1P6/8/8/8/8/8/1K6 w - - 0 1")
        self.board = chess.Board()

        self.square_colors = {"light": "#e6e6e6", "dark": "#a6a6a6"}
        # self.highlight_colors = {'light': '#e2514c', 'dark': '#d74840'}
        self.highlight_colors = {"light": "#00e6b8", "dark": "#00cca3"}
        self.secondary_colors = {"frame": "#262626"}

        self.highlighted_squares = set()
        self.framed_squares = set()
        self.previous_sq_idx = None
        self.possible_moves = None
        self.possible_promotions = None
        self.move_made = False
        self.capture = False

        self.pieces_items = {}

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(8 * self.sq_size, 8 * self.sq_size)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.draw_board()
        self.draw_pieces()
        self.setLayout(self.layout)

    def draw_board(self):
        for sqr_index in range(64):
            square = QWidget(self)
            square.setObjectName(chess.SQUARE_NAMES[sqr_index])

            self.set_square_style(sqr_index)

            col, row = self.get_square_coords(sqr_index)
            self.layout.addWidget(square, row, col)

    def draw_pieces(self):
        for sqr_index in range(64):
            col, row = self.get_square_coords(sqr_index)
            piece = self.board.piece_at(sqr_index)
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
        col = int(mouse_position.x() // self.sq_size)
        row = 7 - int(mouse_position.y() // self.sq_size)
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
                self.board.push(
                    chess.Move(self.previous_sq_idx, square_index, promotion=5)
                )
            else:
                self.board.push(chess.Move(self.previous_sq_idx, square_index))
            last_move = self.board.peek()
            self.move_made = True
            self.update_board(last_move)
        else:
            self.move_made = False
            self.capture = False

    def remove_piece_item(self, square_index):
        piece = self.pieces_items[square_index]
        self.layout.removeWidget(piece)
        del self.pieces_items[square_index]
        piece.deleteLater()

    def move_piece_item(self, source_square_index, target_square_index):
        # Take the piece from the source square
        piece = self.pieces_items[source_square_index]
        # Remove it from the source square
        self.layout.removeWidget(piece)
        # Place it on the target square
        col, row = self.get_square_coords(target_square_index)
        self.layout.addWidget(piece, row, col)
        # Reassign the piece to the new key
        del self.pieces_items[source_square_index]
        self.pieces_items[target_square_index] = piece

    def update_board(self, move):
        source_square_index = move.from_square
        target_square_index = move.to_square

        # Capture
        if target_square_index in self.pieces_items.keys():
            self.remove_piece_item(target_square_index)
            self.capture = True

        # Promotion
        if move.promotion:
            self.remove_piece_item(source_square_index)
            piece = PieceItem(self, self.board.piece_at(target_square_index))
            col, row = self.get_square_coords(target_square_index)
            self.layout.addWidget(piece, row, col)
            self.pieces_items[target_square_index] = piece

        # Castle
        elif (
            self.pieces_items[source_square_index].objectName() == "k"
            and chess.square_distance(source_square_index, target_square_index) > 1
        ):
            uci_string = move.uci()
            if uci_string == "e1g1":  # White short
                rook_source_sq_idx = 7
                rook_target_sq_idx = 5

            elif uci_string == "e1c1":  # White long
                rook_source_sq_idx = 0
                rook_target_sq_idx = 3

            elif uci_string == "e8g8":  # Black short
                rook_source_sq_idx = 63
                rook_target_sq_idx = 61

            elif uci_string == "e8c8":  # Black long
                rook_source_sq_idx = 56
                rook_target_sq_idx = 59
            self.move_piece_item(rook_source_sq_idx, rook_target_sq_idx)
        else:
            self.move_piece_item(source_square_index, target_square_index)
