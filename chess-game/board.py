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
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

import chess
from piece import PieceItem

SQR_SIZE = 100


class ChessBoard(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.sqr_size = SQR_SIZE
        self.board = chess.Board()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMaximumSize(8*self.sqr_size, 8*self.sqr_size)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.draw_board()
        
        self.draw_pieces()
        self.setLayout(self.layout)


    def draw_board(self):
        colors = ['#e6e6e6', '#a6a6a6']
        
        for sqr_index in range(64):
            col = chess.square_file(sqr_index)
            row = 7 - chess.square_rank(sqr_index)
            
            color = colors[(col + row) % 2]
            
            square = QWidget(self)
            square.setStyleSheet(f"background-color: {color}")
            self.layout.addWidget(square, row, col)

    def draw_pieces(self):
        for sqr_index in range(64):
            col = chess.square_file(sqr_index)
            row = 7 - chess.square_rank(sqr_index)
            
            piece = self.board.piece_at(sqr_index)
            if piece:
                piece_label = PieceItem(self, piece)
                self.layout.addWidget(piece_label, row, col)
                
