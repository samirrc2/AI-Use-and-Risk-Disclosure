"""Wrapper: the revision analysis lives in capsule/code/src/revision_analyses.py.

Run that file. Do not keep a second copy here. Capsule data already has the derived
tables (doc_lengths.csv, aum_history.csv) that used to require brochure text / the
Form ADV dump.
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "capsule", "code", "src")
os.environ.setdefault("P10_DATA", os.path.join(ROOT, "capsule", "data"))
os.environ.setdefault("P10_OUT_DIR", os.path.join(ROOT, "analysis", "out"))
sys.path.insert(0, SRC)
runpy.run_path(os.path.join(SRC, "revision_analyses.py"), run_name="__main__")
