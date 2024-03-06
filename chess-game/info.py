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
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
    QProgressBar,
)
from PyQt6.QtGui import QPalette, QColor, QPainter, QBrush, QFont
from PyQt6.QtCore import Qt, QRegularExpression, QRect, QCoreApplication
from board import ChessMoves
from utils import sigmoid, sign
import chess
import chess.engine


class MovesRecord(QScrollArea):
    def __init__(self, parent):
        super().__init__()

        self.setWidgetResizable(True)

        self.parent = parent

        self.moves_record = []

        self.setStyleSheet("background-color: #404040")
        # self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(300, 800)

        self.setFrameShape(QFrame.Shape.NoFrame)

        self.vbar = self.verticalScrollBar()
        self.vbar.setValue(self.vbar.maximum())

        self.table_widget = QTableWidget()
        self.table_widget.setFrameStyle(0)
        self.table_widget.setColumnCount(3)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.horizontalHeader().setVisible(False)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.table_widget)

        scroll_widget = QWidget()
        scroll_widget.setLayout(vbox_layout)
        self.setWidget(scroll_widget)

    def update_moves(self):
        if self.parent.board.move_made:
            last_move = self.parent.board.board.peek()
            moved_piece = self.parent.board.pieces_items[last_move.to_square]
            piece_symbol = str.upper(moved_piece.piece.symbol())
            move_type = self.parent.board.move_type

            san_move: str = (
                "" if piece_symbol == "P" or last_move.promotion else piece_symbol
            ) + chess.SQUARE_NAMES[last_move.to_square]

            if move_type == ChessMoves.capture:
                if piece_symbol == "P" or last_move.promotion:
                    san_move = (
                        chess.SQUARE_NAMES[last_move.from_square][:1]
                        + move_type
                        + san_move
                    )
                else:
                    san_move = san_move[:1] + move_type + san_move[1:]
            elif move_type in [ChessMoves.short_castle, ChessMoves.long_castle]:
                san_move = move_type

            if last_move.promotion:
                san_move += "=Q"

            if self.parent.board.board.is_checkmate():
                san_move += "#"
            elif self.parent.board.board.is_check():
                san_move += "+"

            # san_move += f" ({self.parent.evaluation_bar.evaluation})"
            self.moves_record.append(san_move)

    def display_moves(self):
        if not self.moves_record:
            return

        for idx, move in enumerate(self.moves_record):
            move_num = (idx // 2) + 1
            self.table_widget.setRowCount(move_num)

            move_num_item = QTableWidgetItem(str(move_num) + ".")
            move_num_item.setTextAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self.table_widget.setItem(idx // 2, 0, move_num_item)

            move_item = QTableWidgetItem(move)
            move_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table_widget.setItem(idx // 2, 1 if idx % 2 == 0 else 2, move_item)

            move_num_item.setForeground(QColor("#f6f6f6"))
            move_item.setForeground(QColor("#f6f6f6"))
            move_num_item.setFont(QFont("Bahnschrift", 16))
            move_item.setFont(QFont("Bahnschrift", 16))
        # Scroll to the last move
        self.table_widget.scrollToBottom()


class EvaluationBar(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.evaluation = 0
        self.mate = None

    def set_evaluation(self, evaluation):
        self.evaluation = evaluation
        self.update()  # Trigger a repaint
        
    def set_mate(self, mate):
        self.mate = mate
        self.update()  # Trigger a repaint

    def update_engine_evaluation(self, score: chess.engine.Score):
        if score.score() is not None:
            evaluation = score.score() / 100
            self.evaluation = evaluation
            self.mate = None
        elif score.mate() != 0:
            self.evaluation = None
            self.mate = score.mate()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.mate:
            bar_height = int(self.mate > 0)
        else:
            bar_height = sigmoid(self.evaluation)

        rect = self.rect()
        white_height = int(rect.height() * (bar_height))
        black_height = rect.height() - white_height
        black_rect = rect.adjusted(0, 0, 0, -white_height)
        white_rect = rect.adjusted(0, black_height, 0, 0)

        # Draw the black and white sections
        painter.fillRect(white_rect, Qt.GlobalColor.white)
        painter.fillRect(black_rect, Qt.GlobalColor.black)
