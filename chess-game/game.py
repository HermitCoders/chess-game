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
from PyQt6.QtCore import Qt, QRect

from board import ChessBoard
from piece import PieceItem
import chess


class GameFrame(QFrame):
    def __init__(self, parent):
        super().__init__()

        self.parent = parent

        self.setStyleSheet("background-color: #262626")

        self.board = ChessBoard(self)

        game_widget = QWidget()
        game_layout = QHBoxLayout()
        game_layout.setContentsMargins(0, 0, 0, 0)
        game_layout.setSpacing(0)
        game_layout.addWidget(self.board, 1)
        game_widget.setLayout(game_layout)

        vbox_widget = QWidget()
        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(game_widget, 1)
        vbox_widget.setLayout(vbox_layout)

        self.setLayout(vbox_layout)

    def mousePressEvent(self, event):
        global_pos = self.mapToGlobal(event.pos())

        rect = QRect(
            self.board.mapToGlobal(self.board.rect().topLeft()), self.board.size()
        )
        if rect.contains(global_pos):
            # The mouse click is within the frame's visible area
            local_pos = self.board.mapFromGlobal(global_pos)
            square_index = self.board.mouse_position_to_square_index(local_pos)

            if event.buttons() == Qt.MouseButton.RightButton:
                self.board.unframe_all()
                self.board.set_square_style(square_index, "highlight")

            elif event.buttons() == Qt.MouseButton.LeftButton:
                self.board.unhighlight_all()
                self.board.draw_possible_moves(square_index)
                self.board.move_piece(square_index)

            self.board.previous_sq_idx = square_index
        else:
            print("Mouse click is outside the frame's visible area")
