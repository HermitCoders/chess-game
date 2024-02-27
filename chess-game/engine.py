import chess
import chess.engine

from game import Game


engine = chess.engine.SimpleEngine.popen_uci('stockfish/stockfish-windows-x86-64-avx2.exe')

if __name__ == "__main__":
    game = Game()
    game.run()

