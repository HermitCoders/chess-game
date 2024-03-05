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


class PieceItem(QLabel):
    def __init__(self, parent, piece: chess.Piece):
        super().__init__(parent)

        self.board = parent
        self.piece = piece

        self.setMaximumSize(self.board.sq_size, self.board.sq_size)

        # Make label transparent, so square behind piece is visible
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

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
