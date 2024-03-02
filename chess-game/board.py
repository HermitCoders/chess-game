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
from PyQt6.QtCore import Qt, QRegularExpression

import chess
from piece import PieceItem
from collections import defaultdict

SQR_SIZE = 100


class ChessBoard(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.sqr_size = SQR_SIZE
        self.board = chess.Board()

        self.square_colors = {'light': '#e6e6e6', 'dark': '#a6a6a6'}
        # self.highlight_colors = {'light': '#e2514c', 'dark': '#d74840'}
        self.highlight_colors = {'light': '#00e6b8', 'dark': '#00cca3'}
        self.secondary_colors = {'mark': '#262626'}

        self.possible_moves, self.possible_promotions = self.get_possible_moves()


        # self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setMaximumSize(8 * self.sqr_size, 8 * self.sqr_size)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.draw_board()

        self.draw_pieces()
        self.setLayout(self.layout)

    def draw_board(self):
        for sqr_index in range(64):
            col = chess.square_file(sqr_index)
            row = 7 - chess.square_rank(sqr_index)

            square = QWidget(self)
            square.setObjectName(chess.SQUARE_NAMES[sqr_index])
            if row % 2 == col % 2:
                color = 'light'
            else:
                color = 'dark'
            square.setStyleSheet(f'background-color: {self.square_colors[color]}')
            self.layout.addWidget(square, row, col)

    def draw_pieces(self):
        for sqr_index in range(64):
            col = chess.square_file(sqr_index)
            row = 7 - chess.square_rank(sqr_index)

            piece = self.board.piece_at(sqr_index)
            if piece:
                piece_label = PieceItem(self, piece)
                self.layout.addWidget(piece_label, row, col)

    def highlight_square(self, sq):
        square = self.findChild(QWidget, chess.SQUARE_NAMES[sq])

        col = chess.square_file(sq)
        row = 7 - chess.square_rank(sq)

        if row % 2 == col % 2:
            color = 'light'
        else:
            color = 'dark'
        square.setStyleSheet(f'background-color: {self.highlight_colors[color]}')
        
    def mark_square(self, sq):
        square = self.findChild(QWidget, chess.SQUARE_NAMES[sq])

        col = chess.square_file(sq)
        row = 7 - chess.square_rank(sq)

        if row % 2 == col % 2:
            color = 'light'
        else:
            color = 'dark'
        square.setStyleSheet(f'background-color: {self.square_colors[color]}; border: 4px solid {self.secondary_colors["mark"]}')
        
    def dot_square(self, sq):
        square = self.findChild(QWidget, chess.SQUARE_NAMES[sq])

        col = chess.square_file(sq)
        row = 7 - chess.square_rank(sq)

        if row % 2 == col % 2:
            color = 'light'
        else:
            color = 'dark'
        square.setStyleSheet(f'background-color: {self.square_colors[color]}; border: 2px dashed {self.secondary_colors["mark"]}')

    def reset_square(self, sq):
        square = self.findChild(QWidget, chess.SQUARE_NAMES[sq])

        col = chess.square_file(sq)
        row = 7 - chess.square_rank(sq)

        if row % 2 == col % 2:
            color = 'light'
        else:
            color = 'dark'
        square.setStyleSheet(f'background-color: {self.square_colors[color]}')

    def unhightlight_all(self):
        for sqr_index in range(64):
            self.reset_square(sqr_index)

    def get_possible_moves(self):
        possible_moves = defaultdict(list)
        possible_promotions = defaultdict(list)

        for pos in list(self.board.legal_moves):
            if pos.promotion:
                possible_promotions[pos.from_square].append(pos.to_square)
            possible_moves[pos.from_square].append(pos.to_square)

        return possible_moves, possible_promotions

    def mousePressEvent(self, event):
        # print('Global board: ', self.mapFromGlobal(event.globalPosition()))
        if event.buttons() == Qt.MouseButton.RightButton:
            # Store mouse position and square position, relative to the chessboard
            mouse_pos = self.mapFromGlobal(event.globalPosition())

            col = int(mouse_pos.x() // self.sqr_size)
            row = 7 - int(mouse_pos.y() // self.sqr_size)
            sq = chess.square(col, row)
            

            self.highlight_square(sq)

        if event.buttons() == Qt.MouseButton.LeftButton:
            self.unhightlight_all()
