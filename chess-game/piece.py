import sys
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QWidget,
    QLabel,
    QGraphicsPixmapItem,
    QGraphicsItem,
)
from PyQt6.QtGui import QPalette, QColor, QPixmap, QCursor
from PyQt6.QtCore import Qt, QRegularExpression

import chess
from collections import defaultdict


class PieceItem(QLabel):
    def __init__(self, parent, piece: chess.Piece):
        super().__init__(parent)

        self.board = parent
        self.piece = piece

        # policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # policy.setHeightForWidth(True)
        # self.setSizePolicy(policy)
        
        self.setMaximumSize(self.board.sqr_size, self.board.sqr_size)

        # Make label transparent, so square behind piece is visible
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.src_pos = None
        self.mouse_pos = None
        self.src_square = None
        self.dst_square = None
        # self.legal_moves = None
        # self.legal_dst_squares = None

        # Store original piece image
        pixmap = QPixmap(
            "./assets/pieces/{}{}.png".format(
                "w" if self.piece.color else "b",
                chess.piece_symbol(self.piece.piece_type),
            )
        )
        self.setObjectName(chess.piece_symbol(self.piece.piece_type))
        self.setPixmap(pixmap)

        # When label is scaled, also scale image inside the label
        self.setScaledContents(True)

        self.setMouseTracking(True)

        self.show()

    def mousePressEvent(self, event):
        mouse_pos = self.board.mapFromGlobal(event.globalPosition())
        # print('Global piece: ', mouse_pos)

        col = int(mouse_pos.x() // self.board.sqr_size)
        row = 7 - int(mouse_pos.y() // self.board.sqr_size)
        sq = chess.square(col, row)
        
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.board.unhightlight_all()
            self.board.mark_square(sq)
            self.draw_possible_moves(sq)
            
        if event.buttons() == Qt.MouseButton.RightButton:
            self.board.highlight_square(sq)


    def draw_possible_moves(self, sq):
        # print(self.board.possible_moves, self.board.possible_promotions)
        moves = self.board.possible_moves[sq]
        
        for move in moves:
            self.board.dot_square(move)

        
