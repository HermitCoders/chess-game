import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtGui import QPalette, QColor

from game import GameFrame


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.stack = QStackedWidget(self)

        self.game_frame = GameFrame(self)

        self.stack.insertWidget(0, self.game_frame)

        self.stack.setCurrentIndex(0)

        self.setCentralWidget(self.stack)
        self.setWindowTitle("Chess")
        self.setMinimumSize(800, 800)
        self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
