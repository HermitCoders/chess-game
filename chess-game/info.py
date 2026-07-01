from PyQt6.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
    QAbstractItemView,
    QTextEdit,
)
from PyQt6.QtGui import QColor, QPainter, QFont
from PyQt6.QtCore import Qt, QRect, QObject, pyqtSignal
import chess
import chess.engine

from utils import sigmoid


class MyQTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() // 120
        # most mice have a baseline scroll speed of 120 units per "notch"
        current_value = self.verticalScrollBar().value()
        self.verticalScrollBar().setValue(current_value - delta)


class MovesRecord(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.board_frame = parent.board

        self.setStyleSheet("background-color: #363636")

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFrameStyle(0)
        self.text_edit.setStyleSheet(
            "QTextEdit {background-color: #363636; color: #f6f6f6; border: 0px;}"
        )
        self.text_edit.setFont(QFont("Menlo", 14))

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.text_edit)
        vbox_layout.setSpacing(0)
        vbox_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vbox_layout)

    def render_from_tree(self, move_tree):
        lines = move_tree.get_root().render_outline()
        html_lines = []
        for depth, text in lines:
            margin = depth * 20
            html_lines.append(
                f'<div style="margin-left: {margin}px;">{text}</div>'
            )
        self.text_edit.setHtml("".join(html_lines))
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )


class EvaluationBar(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.centipawns = 0
        self.mate = None

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

        painter.setFont(QFont("Menlo", 12))

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

        # Main table formatting
        self.table_widget = MyQTableWidget()
        self.table_widget.setFrameStyle(0)
        self.table_widget.setRowCount(3)
        self.table_widget.setColumnCount(2)
        self.table_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Vertical header formatting
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

        # Horizontal header formatting
        self.table_widget.horizontalHeader().setVisible(False)
        self.table_widget.horizontalHeader().setDefaultSectionSize(40)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.table_widget)
        vbox_layout.setSpacing(0)
        vbox_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vbox_layout)

    def get_score_str(self, score):
        if score.score() is not None:
            score_str = str(round(score.score() / 100, 1))
        else:
            score_str = str(score.mate())
            score_str = (
                ("-M" + score_str[1:])
                if score_str.startswith("-")
                else ("M" + score_str)
            )
        return score_str

    def add_table_item(self, text, row, col, alignment):
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment)
        item.setForeground(QColor("#f6f6f6"))
        item.setFont(QFont("Menlo", 12))
        self.table_widget.setItem(row, col, item)

    def update_engine_lines(self, evaluation):
        self.table_widget.setColumnCount(2)
        for idx, eval_dict in enumerate(evaluation[:3]):
            score = eval_dict["score"].white()
            score_str = self.get_score_str(score)
            self.add_table_item(
                score_str,
                idx,
                0,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            )

            line = eval_dict.get("pv", "")
            # Consider only lines longer than two moves unless its forced mate
            if len(line) > 2 or score.mate():
                line_str = self.board_frame.board.variation_san(line)
                self.add_table_item(
                    line_str,
                    idx,
                    1,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                )
        self.update()


class ChessEngine(QObject):
    evaluation_result = pyqtSignal(list)
    
    engine = chess.engine.SimpleEngine.popen_uci(
        "/opt/homebrew/bin/stockfish"
    )

    def evaluate(self, board):
        info = self.engine.analyse(
            board, chess.engine.Limit(depth=16), multipv=5
        )
        self.evaluation_result.emit(info)
