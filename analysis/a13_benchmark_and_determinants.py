"""Wrapper: the benchmark/determinants analysis lives in capsule/code/src/benchmark_determinants.py.

Run that file. Do not keep a second copy here. Capsule data already has
keyword_constructs.csv, which used to be read off brochure text.
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "capsule", "code", "src")
os.environ.setdefault("P10_DATA", os.path.join(ROOT, "capsule", "data"))
os.environ.setdefault("P10_OUT_DIR", os.path.join(ROOT, "analysis", "out"))
sys.path.insert(0, SRC)
runpy.run_path(os.path.join(SRC, "benchmark_determinants.py"), run_name="__main__")
