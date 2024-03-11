from PyQt6.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
    QAbstractItemView,
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
        self.moves_record = []

        self.setStyleSheet("background-color: #363636")

        # Main table formatting
        self.table_widget = MyQTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_widget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems
        )
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_widget.setStyleSheet(
            """QTableWidget {border: 0px; gridline-color: #2e2e2e}
            QTableWidget::item {background-color: #363636; color: #f6f6f6;}
            QTableWidget::item:selected {background-color: #565656; color: #f6f6f6;}"""
        )

        # Vertical header formatting
        self.table_widget.verticalHeader().setDefaultSectionSize(35)
        self.table_widget.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self.table_widget.verticalHeader().setFixedWidth(40)
        self.table_widget.verticalHeader().setFont(QFont("Bahnschrift", 14))
        self.table_widget.verticalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        )
        self.table_widget.verticalHeader().setStyleSheet(
            """QHeaderView::section {
                background: #363636; 
                color: #f6f6f6; 
                border-top: 0px;
                border-left: 0px;
                border-right: 1px solid #2e2e2e;
                border-bottom: 1px solid #2e2e2e;}"""
        )
        self.table_widget.verticalHeader().setHighlightSections(False)

        # Horizontal header formatting
        self.table_widget.horizontalHeader().setVisible(False)
        self.table_widget.horizontalHeader().setDefaultSectionSize(120)
        self.table_widget.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table_widget.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )

        # Scroll bar formatting
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

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.table_widget)
        vbox_layout.setSpacing(0)
        vbox_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vbox_layout)

    def update_moves_record(self):
        if self.board_frame.move_made:
            last_move = self.board_frame.board.peek()

            san_move = self.board_frame.previous_board.san(last_move)

            if self.board_frame.board.is_check():
                king_square = self.board_frame.board.king(self.board_frame.board.turn)
                self.board_frame.set_square_style(king_square, "check")
                self.board_frame.checked_squares.add(king_square)
            else:
                self.board_frame.uncheck_all()
            # san_move += f" ({self.parent.evaluation_bar.evaluation})"
            self.moves_record.append(san_move)
            self.update_moves_display(san_move)

    def update_moves_display(self, move):
        idx = self.board_frame.board.ply() - 1

        move_num = (idx // 2) + 1
        self.table_widget.setRowCount(move_num)

        move_item = QTableWidgetItem(move)
        move_item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.table_widget.setItem(idx // 2, 0 if idx % 2 == 0 else 1, move_item)

        move_item.setForeground(QColor("#f6f6f6"))
        move_item.setFont(QFont("Bahnschrift", 14))
        # Scroll to the last move
        self.table_widget.scrollToBottom()


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
        item.setFont(QFont("Bahnschrift", 12))
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
        "stockfish/stockfish-windows-x86-64-avx2.exe"
    )

    def evaluate(self, board):
        info = self.engine.analyse(
            board, chess.engine.Limit(depth=16), multipv=5
        )
        self.evaluation_result.emit(info)
