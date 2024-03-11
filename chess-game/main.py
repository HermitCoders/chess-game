import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtGui import QCloseEvent

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
        self.setMinimumSize(820, 820)
        self.show()

    def closeEvent(self, event: QCloseEvent):
        self.game_frame.thread.quit()
        self.game_frame.thread.wait()
        self.game_frame.chess_engine.engine.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    # Start the engine thread when the application starts
    window.game_frame.thread.start()
    app.exec()
