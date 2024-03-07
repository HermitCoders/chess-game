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
from PyQt6.QtGui import QCloseEvent, QMouseEvent, QPalette, QColor
from PyQt6.QtCore import Qt, QRect

from board import ChessBoard
from info import MovesRecord, EvaluationBar
import chess
import chess.engine


class GameFrame(QFrame):
    def __init__(self, parent, engine):
        super().__init__(parent)

        self.parent = parent
        self.engine = engine

        self.setStyleSheet("background-color: #262626")

        self.evaluation_bar = EvaluationBar(self)
        self.evaluation_bar.setFixedSize(30, 800)

        self.board = ChessBoard(self)
        self.board.setFixedSize(800, 800)

        self.moves_record = MovesRecord(self)
        self.moves_record.setFixedSize(300, 800)

        # Game layout
        game_layout = QHBoxLayout()
        game_layout.setContentsMargins(0, 0, 0, 0)
        game_layout.setSpacing(10)
        game_layout.addWidget(self.evaluation_bar)
        game_layout.addWidget(self.board)
        game_layout.addWidget(self.moves_record)

        game_widget = QWidget()
        game_widget.setLayout(game_layout)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(game_widget)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setLayout(main_layout)

    def mousePressEvent(self, event: QMouseEvent):
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
                self.moves_record.update_moves()
                self.moves_record.display_moves()

            self.board.previous_sq_idx = square_index
        else:
            print("Mouse click is outside the frame's visible area")

        self.evaluation_bar.update_engine_evaluation(self.evaluation())

    # def mouseReleaseEvent(self, event: QMouseEvent):
    #     self.moves_record.update_moves()

    def evaluation(self):
        info = self.engine.analyse(
            self.board.board, chess.engine.Limit(time=0.1), multipv=3
        )
        return info[0]["score"].white()
