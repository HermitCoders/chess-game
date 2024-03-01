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
    QGraphicsItem
)
from PyQt6.QtGui import QPalette, QColor, QPixmap
from PyQt6.QtCore import Qt

import chess


class PieceItem(QLabel):
    def __init__(self, parent, piece: chess.Piece):
        super().__init__(parent)

        self.board = parent
        self.piece = piece

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMaximumSize(self.board.sqr_size, self.board.sqr_size)
        
        # Make label transparent, so square behind piece is visible
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


        # self.src_pos = None
        # self.mouse_pos = None
        # self.src_square = None
        # self.dst_square = None
        # self.legal_moves = None
        # self.legal_dst_squares = None

        # Store original piece image
        pixmap = QPixmap('./assets/pieces/{}{}.png'.format('w' if self.piece.color else 'b',
                                                           chess.piece_symbol(self.piece.piece_type)))
        self.setPixmap(pixmap)

        # self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        # self.setAcceptHoverEvents(True)

        # When label is scaled, also scale image inside the label
        self.setScaledContents(True)

        self.setMouseTracking(True)

        self.show()
        