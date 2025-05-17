import pandas as pd

matches = pd.read_csv('matches.csv', index_col=0)

print(matches.shape)