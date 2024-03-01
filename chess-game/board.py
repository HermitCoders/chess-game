import sys
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QWidget,
)
from PyQt6.QtGui import QPalette, QColor


class ChessBoard(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout = QGridLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.draw_squares()
        self.setLayout(self.layout)

    def draw_squares(self):
        for row, rank in enumerate("87654321"):
            for col, file in enumerate("abcdefgh"):
                square = QWidget(self)
                square.setObjectName(file + rank)
                square.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                if row % 2 == col % 2:
                    square.setStyleSheet("background-color: #e6e6e6")
                else:
                    square.setStyleSheet("background-color: #a6a6a6")
                self.layout.addWidget(square, row, col)
