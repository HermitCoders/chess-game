from PyQt6.QtWidgets import (
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
    QAbstractItemView,
    QTextBrowser,
    QGraphicsOpacityEffect,
    QProgressBar,
)
from PyQt6.QtGui import QColor, QPainter, QFont, QTextCursor, QFontMetrics
from PyQt6.QtCore import Qt, QRect, QObject, QEvent, QTimer, pyqtSignal
import chess
import chess.engine
import re

from utils import sigmoid

import os
import shutil
import logging

logger = logging.getLogger(__name__)


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
        self._active_anchor = None

        self.setStyleSheet("background-color: #363636")

        self.text_edit = MovesBrowser()
        self.text_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.text_edit.document().setDocumentMargin(0)
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

        viewport_width = self.text_edit.viewport().width()
        move_number_width = 40
        remaining = max(viewport_width - move_number_width, 100)
        column_width = remaining // 2
        
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

        html_parts = ['<table width="100%" cellpadding="6" cellspacing="0" border="0" style="border-collapse: collapse; margin: 0;">']
        for row in rows:
            if row["type"] == "row":
                html_parts.append(
                    '<tr>'
                    f'<td width="{move_number_width}" style="color:#8a8a8a; white-space: nowrap;">{row["move_number"]}.</td>'
                    f'<td width="{column_width}">{style(row["white"])}</td>'
                    f'<td width="{column_width}">{style(row["black"])}</td>'
                    '</tr>'
                )
            else:  # variation
                variation_lines = []
                for depth, html in row["lines"]:
                    margin_left = depth * 16
                    variation_lines.append(
                        f'<div style="margin-left: {margin_left}px; margin-top: 4px;">{style(html)}</div>'
                    )
                variation_html = "".join(variation_lines)
                html_parts.append(
                    '<tr style="background-color: #2b2b2b;">'
                    f'<td colspan="3" style="color:#9a9a9a;">{variation_html}</td>'
                    '</tr>'
                )
        html_parts.append("</table>")

        scrollbar = self.text_edit.verticalScrollBar()
        previous_scroll = scrollbar.value()

        self.text_edit.setHtml("".join(html_parts))

        scrollbar.setValue(previous_scroll)
        self._scroll_to_active()

    def _scroll_to_active(self):
        if self._active_anchor is None:
            self.text_edit.verticalScrollBar().setValue(0)
            return

        doc = self.text_edit.document()
        block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                fmt = frag.charFormat()
                if fmt.isAnchor() and self._active_anchor in fmt.anchorNames():
                    cursor = QTextCursor(doc)
                    cursor.setPosition(frag.position())
                    rect = self.text_edit.cursorRect(cursor)

                    scrollbar = self.text_edit.verticalScrollBar()
                    visible_top = scrollbar.value()
                    visible_bottom = visible_top + self.text_edit.viewport().height()

                    if rect.top() < visible_top or rect.bottom() > visible_bottom:
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
        self.board_frame = parent.board
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

        if self.board_frame.flipped:
            bar_height = 1 - bar_height

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
        super().__init__(parent)
        self.board_frame = parent.board
        self._last_evaluation = None
        self._last_board = None

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

    def set_thinking(self, is_thinking):
        if is_thinking:
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(0.4)
            self.table_widget.setGraphicsEffect(effect)
        else:
            self.table_widget.setGraphicsEffect(None)

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

    def add_table_item(self, text, row, col, alignment, color=None, bold=False):
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment)
        item.setForeground(QColor(color or "#f6f6f6"))
        font = QFont("Menlo", 12)
        font.setBold(bold)
        item.setFont(font)
        if row % 2 == 1:
            item.setBackground(QColor("#3d3d3d"))
        self.table_widget.setItem(row, col, item)

    def _color_for_score(self, score):
        flipped = self.board_frame.flipped
        mate = score.mate()
        if mate is not None:
            favors_bottom = (mate > 0) != flipped
            return "#5dcaa5" if favors_bottom else "#e2514c"
        centipawns = score.score()
        if centipawns is None:
            return "#f6f6f6"
        magnitude = min(abs(centipawns) / 300, 1.0)
        favors_bottom = (centipawns >= 0) != flipped
        target = "#5dcaa5" if favors_bottom else "#e2514c"
        return self._blend("#f6f6f6", target, magnitude)

    def _blend(self, base_hex, target_hex, t):
        base = QColor(base_hex)
        target = QColor(target_hex)
        r = int(base.red() + (target.red() - base.red()) * t)
        g = int(base.green() + (target.green() - base.green()) * t)
        b = int(base.blue() + (target.blue() - base.blue()) * t)
        return QColor(r, g, b).name()

    def update_engine_lines(self, evaluation, board):
        self._last_evaluation = evaluation
        self._last_board = board
        self.table_widget.setColumnCount(2)
        self.table_widget.clearContents()
        for idx, eval_dict in enumerate(evaluation[:3]):
            score = eval_dict["score"].white()
            score_str = self.get_score_str(score)
            score_color = self._color_for_score(score)
            self.add_table_item(
                score_str,
                idx,
                0,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                color=score_color,
            )

            line = eval_dict.get("pv", "")
            # Consider only lines longer than two moves unless its forced mate
            if len(line) > 2 or score.mate():
                line_str = board.variation_san(line)
                available_width = self.table_widget.columnWidth(1) - 10
                metrics = QFontMetrics(QFont("Menlo", 12))
                elided = metrics.elidedText(
                    line_str, Qt.TextElideMode.ElideRight, available_width
                )
                self.add_table_item(
                    elided,
                    idx,
                    1,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                )
        self.update()

    def refresh_colors(self):
        """Re-render the last known evaluation with the current board
        orientation's color mapping, without re-querying the engine --
        flipping the board doesn't change the position, so there's
        nothing new to evaluate."""
        if self._last_evaluation is not None:
            self.update_engine_lines(self._last_evaluation, self._last_board)

class ChessEngine(QObject):
    evaluation_result = pyqtSignal(object, list)

    def __init__(self, engine_path: str = None):
        super().__init__()
        self.engine = chess.engine.SimpleEngine.popen_uci(
            engine_path or find_engine_path()
        )

    def evaluate(self, board):
        try:
            info = self.engine.analyse(
                board, chess.engine.Limit(depth=16), multipv=3
            )
        except chess.engine.EngineTerminatedError:
            logger.error("Stockfish process terminated unexpectedly during analysis")
            return
        except chess.engine.EngineError as e:
            logger.error("Stockfish engine error during analysis: %s", e)
            return
        self.evaluation_result.emit(board, info)
