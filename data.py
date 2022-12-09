from random import randint
import pandas as pd


def get_data(amount=100):
    return pd.DataFrame({'x': range(amount), 'y': [randint(0, 100) for _ in range(amount)]})
