import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QSizePolicy
from PyQt6.QtGui import QPalette, QColor, QCloseEvent

from game import GameFrame
import chess.engine


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        engine = chess.engine.SimpleEngine.popen_uci(
            "stockfish/stockfish-windows-x86-64-avx2.exe"
        )

        self.stack = QStackedWidget(self)

        self.game_frame = GameFrame(self, engine)

        self.stack.insertWidget(0, self.game_frame)

        self.stack.setCurrentIndex(0)

        self.setCentralWidget(self.stack)
        self.setWindowTitle("Chess")
        self.setMinimumSize(820, 820)
        self.show()

    def closeEvent(self, event: QCloseEvent):
        self.game_frame.engine.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.exec()
