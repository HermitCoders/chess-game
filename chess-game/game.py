import sys
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
)
from PyQt6.QtGui import QPalette, QColor

from board import ChessBoard


class GameFrame(QFrame):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent

        self.setStyleSheet("background-color: #262626")

        self.board = ChessBoard(self)

        game_widget = QWidget()
        game_layout = QHBoxLayout()
        game_layout.setContentsMargins(0, 0, 0, 0)
        game_layout.setSpacing(30)
        game_layout.addWidget(self.board, 8)
        # self.setLayout(game_layout)
        
        game_widget.setLayout(game_layout)

        vbox_widget = QWidget()
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(game_widget, 16)
        vbox_widget.setLayout(vbox_layout)

        self.setLayout(vbox_layout)
