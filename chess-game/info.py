from PyQt6.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
    QAbstractItemView,
    QTextEdit,
    QTextBrowser,
)
from PyQt6.QtGui import QColor, QPainter, QFont, QTextCursor
from PyQt6.QtCore import Qt, QRect, QObject, QEvent, QTimer, pyqtSignal
import chess
import chess.engine
import re

from utils import sigmoid

import os
import shutil


def find_engine_path() -> str:
    """Resolve the UCI engine executable path.

    Resolution order:
    1. CHESS_ENGINE_PATH environment variable (explicit override).
    2. A "stockfish" binary discoverable on PATH.
    3. Raise a clear, actionable error instead of crashing on import.
    """
    env_path = os.environ.get("CHESS_ENGINE_PATH")
    if env_path:
        if os.path.isfile(env_path):
            return env_path
        raise FileNotFoundError(
            f"CHESS_ENGINE_PATH is set to '{env_path}' but no file exists there."
        )

    found = shutil.which("stockfish")
    if found:
        return found

    raise FileNotFoundError(
        "Could not locate a Stockfish executable. Install Stockfish and make "
        "sure it is on your PATH, or set the CHESS_ENGINE_PATH environment "
        "variable to point at the executable."
    )


class MyQTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() // 120
        # most mice have a baseline scroll speed of 120 units per "notch"
        current_value = self.verticalScrollBar().value()
        self.verticalScrollBar().setValue(current_value - delta)

class MovesBrowser(QTextBrowser):
    pass


class MovesRecord(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.board_frame = parent.board
        self.on_move_clicked = None
        self._targets = {}
        self._lines = []
        self._active_anchor = None

        self.setStyleSheet("background-color: #363636")

        self.text_edit = MovesBrowser()
        self.text_edit.setOpenLinks(False)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFrameStyle(0)
        self.text_edit.setStyleSheet(
            "QTextBrowser {background-color: #363636; color: #f6f6f6; border: 0px;}"
        )
        self.text_edit.setFont(QFont("Menlo", 14))
        self.text_edit.anchorClicked.connect(self._on_anchor_clicked)

        vbox_layout = QVBoxLayout()
        vbox_layout.addWidget(self.text_edit)
        vbox_layout.setSpacing(0)
        vbox_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vbox_layout)

    def render_from_tree(self, move_tree):
        self._targets = {}
        rows = move_tree.get_root().render_table(self._targets)

        self._active_anchor = None
        if move_tree._current_move >= 0:
            for anchor_id, (node, idx) in self._targets.items():
                if node is move_tree and idx == move_tree._current_move:
                    self._active_anchor = anchor_id
                    break

        def style(html):
            if html is None:
                return "&nbsp;"
            return re.sub(
                r'href="(\d+)" style="[^"]*"',
                lambda m: f'href="{m.group(1)}" style="{self._style_for(m.group(1))}"',
                html,
            )

        html_parts = ['<table width="100%" style="border-collapse: collapse;">']
        for row in rows:
            if row["type"] == "row":
                html_parts.append(
                    '<tr>'
                    f'<td width="40" style="color:#8a8a8a; padding: 2px 4px; white-space: nowrap;">{row["move_number"]}.</td>'
                    f'<td width="120" style="padding: 2px 4px;">{style(row["white"])}</td>'
                    f'<td width="120" style="padding: 2px 4px;">{style(row["black"])}</td>'
                    '</tr>'
                )
            else:  # variation
                variation_html = " ".join(style(html) for depth, html in row["lines"])
                html_parts.append(
                    '<tr>'
                    f'<td></td><td colspan="2" style="color:#9a9a9a; padding: 2px 4px 2px 20px;">{variation_html}</td>'
                    '</tr>'
                )
        html_parts.append("</table>")

        self.text_edit.setHtml("".join(html_parts))
        self._scroll_to_active()

    def _scroll_to_active(self):
        if self._active_anchor is None:
            self.text_edit.verticalScrollBar().setValue(0)
            return

        doc = self.text_edit.document()
        block = doc.begin()
        found = False
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                fmt = frag.charFormat()
                if fmt.isAnchor() and self._active_anchor in fmt.anchorNames():
                    found = True
                    cursor = QTextCursor(doc)
                    cursor.setPosition(frag.position())
                    self.text_edit.setTextCursor(cursor)
                    self.text_edit.ensureCursorVisible()
                    return
                it += 1
            block = block.next()
    
    def _style_for(self, anchor_id):
        styles = ["color:#f6f6f6", "text-decoration:none", "padding:1px 3px", "border-radius:3px"]
        if anchor_id == self._active_anchor:
            styles += ["background-color:#0f6e56", "color:#eafff6"]
        return ";".join(styles)

    def _on_anchor_clicked(self, url):
        anchor_id = url.toString()
        target = self._targets.get(anchor_id)
        if target and self.on_move_clicked:
            node, move_index = target
            self.on_move_clicked(node, move_index)

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

    def update_engine_lines(self, evaluation, board):
        self.table_widget.setColumnCount(2)
        self.table_widget.clearContents()
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
                line_str = board.variation_san(line)
                self.add_table_item(
                    line_str,
                    idx,
                    1,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                )
        self.update()


class ChessEngine(QObject):
    evaluation_result = pyqtSignal(object, list)

    def __init__(self, engine_path: str = None):
        super().__init__()
        self.engine = chess.engine.SimpleEngine.popen_uci(
            engine_path or find_engine_path()
        )

    def evaluate(self, board):
        info = self.engine.analyse(
            board, chess.engine.Limit(depth=16), multipv=5
        )
        self.evaluation_result.emit(board, info)
