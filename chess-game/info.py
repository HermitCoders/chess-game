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
    QAbstractItemView,
)
from PyQt6.QtGui import QPalette, QColor, QPainter, QBrush, QFont, QWheelEvent
from PyQt6.QtCore import Qt, QRegularExpression, QRect, QCoreApplication
from board import ChessMoves
from utils import sigmoid
import chess
import chess.engine
from itertools import pairwise


class MyQTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() // 120
        current_value = self.verticalScrollBar().value()
        self.verticalScrollBar().setValue(current_value - delta)


class MovesRecord(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.board_frame = parent.board
        self.moves_record = []

        self.setStyleSheet("background-color: #363636")

        self.table_widget = MyQTableWidget()
        self.table_widget.setFrameStyle(0)
        self.table_widget.setColumnCount(3)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.verticalHeader().setDefaultSectionSize(35)

        self.table_widget.horizontalHeader().setVisible(False)
        self.table_widget.horizontalHeader().setDefaultSectionSize(120)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )
        scroll_bar = self.table_widget.verticalScrollBar()
        scroll_bar.setStyleSheet(
            """QScrollBar:vertical {width: 10px; background: #363636; margin: 0px} 
            QScrollBar::sub-page:vertical {background: #363636;}
            QScrollBar::add-page:vertical {background: #363636;}
            QScrollBar::handle:vertical {background: #565656;}"""
        )
        self.table_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_widget.setStyleSheet(
            "QTableWidget {outline: 0;} QTableWidget::item:selected{background: #565656;}"
        )

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.table_widget)
        vbox_layout.setSpacing(0)
        vbox_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vbox_layout)

    def update_moves_record(self):
        if self.board_frame.move_made:
            last_move = self.board_frame.board.peek()
            moved_piece = self.board_frame.pieces_items[last_move.to_square]
            piece_symbol = str.upper(moved_piece.piece.symbol())
            move_type: ChessMoves = self.board_frame.move_type

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

            if self.board_frame.board.is_checkmate():
                san_move += "#"
                self.board_frame.set_square_style(
                    self.board_frame.board.king(self.board_frame.board.turn), "check"
                )
            elif self.board_frame.board.is_check():
                san_move += "+"
                self.board_frame.set_square_style(
                    self.board_frame.board.king(self.board_frame.board.turn), "check"
                )
            else:
                self.board_frame.set_square_style(
                    self.board_frame.board.king(1 - self.board_frame.board.turn)
                )
            # san_move += f" ({self.parent.evaluation_bar.evaluation})"
            self.moves_record.append(san_move)
            self.update_moves_display(san_move)

    def update_moves_display(self, move):
        idx = self.board_frame.board.ply() - 1

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
        self.centipawns = 0
        self.mate = None

    def set_evaluation(self, evaluation):
        self.centipawns = evaluation
        self.update()  # Trigger a repaint

    def set_mate(self, mate):
        self.mate = mate
        self.update()  # Trigger a repaint

        # {'string': 'NNUE evaluation using nn-b1a57edbea57.nnue', 'depth': 0, 'score': PovScore(Mate(-0), BLACK)}]

    def update_engine_evaluation(self, evaluation):
        score = evaluation[0]["score"].white()
        if score.score() is not None:
            self.centipawns = score.score()
            self.mate = None
        else:
            self.centipawns = None
            self.mate = score
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.centipawns is not None:
            bar_height = sigmoid(self.centipawns / 100)
        else:
            bar_height = 0 if str(self.mate)[1:2] == "-" else 1

        rect = self.rect()
        white_height = int(rect.height() * (bar_height))
        black_height = rect.height() - white_height
        black_rect = rect.adjusted(0, 0, 0, -white_height)
        white_rect = rect.adjusted(0, black_height, 0, 0)

        # Draw the black and white sections
        painter.fillRect(white_rect, Qt.GlobalColor.white)
        painter.fillRect(black_rect, Qt.GlobalColor.black)

        painter.setFont(QFont("Bahnschrift", 12))

        if bar_height >= 0.5:
            painter.setPen(QColor("black"))
            text_pos = (
                0,
                rect.height() - int(1.5 * painter.fontMetrics().height()),
                rect.width(),
                painter.fontMetrics().height(),
            )
        else:
            painter.setPen(QColor("white"))
            text_pos = (
                0,
                int(0.5 * painter.fontMetrics().height()),
                rect.width(),
                painter.fontMetrics().height(),
            )

        # Draw the evaluation text
        if self.centipawns is not None:
            text = f"{abs(self.centipawns / 100):.1f}"
        else:
            text = f"M{str(self.mate)[-1]}"

        text_rect = QRect(*text_pos)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
            text,
        )


class EngineLines(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.board_frame = parent.board

        self.setStyleSheet("background-color: #363636")

        self.table_widget = MyQTableWidget()
        self.table_widget.setFrameStyle(0)
        self.table_widget.setRowCount(3)
        self.table_widget.setColumnCount(2)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.verticalHeader().setDefaultSectionSize(30)
        self.table_widget.verticalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table_widget.verticalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self.table_widget.verticalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Fixed
        )

        self.table_widget.horizontalHeader().setVisible(False)
        # self.table_widget.horizontalHeader().setDefaultSectionSize(250)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        # self.table_widget.setStyleSheet(
        #     "QTableWidget {outline: 0;} QTableWidget::item:selected{background: #565656;}"
        # )

        self.table_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.table_widget)
        vbox_layout.setSpacing(0)
        vbox_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vbox_layout)

    def update_engine_lines(self, evaluation, move_index):
        self.table_widget.setColumnCount(2)
        for idx, eval_dict in enumerate(evaluation[:3]):
            score = eval_dict["score"].white()
            if score.score() is not None:
                score = str(round(score.score() / 100, 1))
            else:
                score = str(score.mate())
                score = ("M" + score) if score[0] != "-" else ("-M" + score[1:])

            score_item = QTableWidgetItem(str(score))
            score_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self.table_widget.setItem(idx, 0, score_item)
            score_item.setForeground(QColor("#f6f6f6"))
            score_item.setFont(QFont("Bahnschrift", 12, QFont.Weight.Bold))

            # print((move_index // 2) + 1)
            line = eval_dict.get("pv", "")
            if move_index % 2:
                line_str = f"{move_index // 2 + 1}... "
            else:
                line_str = f"{move_index // 2 + 1}. "
            line_str += line[0].uci()

            if move_index % 2:
                mapped_line = [
                    f"{m1.uci()} {m2.uci()}" for m1, m2 in pairwise(line[1:6])
                ]
                line_str += "".join(
                    f" {j+1}. {m}"
                    for j, m in enumerate(mapped_line, move_index // 2 + 1)
                )
            else:
                mapped_line = [
                    f"{m1.uci()} {m2.uci()}" for m1, m2 in pairwise(line[2:6])
                ]
                line_str += str(" ") + line[1].uci()
                line_str += "".join(
                    f" {j+1}. {m}"
                    for j, m in enumerate(mapped_line, move_index // 2 + 1)
                )

            line_item = QTableWidgetItem(line_str)
            line_item.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.table_widget.setItem(idx, 1, line_item)
            line_item.setForeground(QColor("#f6f6f6"))
            line_item.setFont(QFont("Bahnschrift Light", 12))
        self.update()

        # Scroll to the last move
        # self.table_widget.scrollToBottom()
