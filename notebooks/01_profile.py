import pandas as pd
import numpy as np
import os

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 160)

DATA = '/home/claude/credresolve/data'
tables = [f.replace('.csv','') for f in os.listdir(DATA) if f.endswith('.csv') and f != 'data_dictionary.csv']

dfs = {}
for t in tables:
    dfs[t] = pd.read_csv(f'{DATA}/{t}.csv')

print("="*100)
print("TABLE SHAPES & EXACT DUPLICATE ROWS")
print("="*100)
for t, df in sorted(dfs.items()):
    dupe_full = df.duplicated().sum()
    print(f"{t:28s} rows={len(df):7d}  cols={len(df.columns):3d}  exact_dupe_rows={dupe_full:6d}")

print()
print("="*100)
print("PRIMARY-KEY-LIKE COLUMN DUPLICATE CHECK (first column of each table)")
print("="*100)
for t, df in sorted(dfs.items()):
    pk = df.columns[0]
    n_total = len(df)
    n_unique = df[pk].nunique()
    print(f"{t:28s} pk={pk:20s} total={n_total:7d}  unique={n_unique:7d}  dupe_pk_rows={n_total-n_unique:6d}")
