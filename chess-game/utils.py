import math


def sigmoid(x):
    return 1 / (1 + math.exp(-0.3 * x))


def sign(x):
    return (x > 0) - (x < 0)
