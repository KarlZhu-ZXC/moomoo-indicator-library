from __future__ import annotations

import builtins
import math
import runpy
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = [
    ROOT / "indicators" / "smc" / "SMC_STR.py",
    ROOT / "indicators" / "smc" / "SMC_OB.py",
    ROOT / "indicators" / "smc" / "SMC_IMB.py",
    ROOT / "indicators" / "ote" / "OTE_CP.py",
    ROOT / "indicators" / "historical-similarity" / "HIST_SIM.py",
    ROOT / "indicators" / "historical-similarity" / "HIST_SIM_PCT.py",
]
N = 1400
rng = np.random.default_rng(20260828)
returns = rng.normal(0.0002, 0.017, N)
close_arr = 100.0 * np.exp(np.cumsum(returns))
open_arr = np.r_[close_arr[0], close_arr[:-1] * (1.0 + rng.normal(0.0, 0.003, N - 1))]
spread = np.abs(rng.normal(0.008, 0.004, N))
high_arr = np.maximum(open_arr, close_arr) * (1.0 + spread)
low_arr = np.minimum(open_arr, close_arr) * (1.0 - spread)
date_arr = np.busday_offset(np.datetime64("2021-01-01"), np.arange(N), roll="forward")


class Seq:
    __array_priority__ = 1000

    def __init__(self, values):
        self.v = values.v.copy() if isinstance(values, Seq) else np.asarray(values)

    def _coerce(self, other):
        return other.v if isinstance(other, Seq) else other

    def _bin(self, other, fn):
        return Seq(fn(self.v, self._coerce(other)))

    def __add__(self, other): return self._bin(other, np.add)
    def __radd__(self, other): return Seq(np.add(other, self.v))
    def __sub__(self, other): return self._bin(other, np.subtract)
    def __rsub__(self, other): return Seq(np.subtract(other, self.v))
    def __mul__(self, other): return self._bin(other, np.multiply)
    def __rmul__(self, other): return Seq(np.multiply(other, self.v))
    def __truediv__(self, other):
        with np.errstate(divide="ignore", invalid="ignore"):
            return self._bin(other, np.divide)
    def __rtruediv__(self, other):
        with np.errstate(divide="ignore", invalid="ignore"):
            return Seq(np.divide(other, self.v))
    def __mod__(self, other): return self._bin(other, np.mod)
    def __rmod__(self, other): return Seq(np.mod(other, self.v))
    def __neg__(self): return Seq(-self.v)
    def __lt__(self, other): return self._bin(other, np.less)
    def __le__(self, other): return self._bin(other, np.less_equal)
    def __gt__(self, other): return self._bin(other, np.greater)
    def __ge__(self, other): return self._bin(other, np.greater_equal)
    def __eq__(self, other): return self._bin(other, np.equal)
    def __ne__(self, other): return self._bin(other, np.not_equal)
    def __and__(self, other): return self._bin(other, np.logical_and)
    def __rand__(self, other): return Seq(np.logical_and(other, self.v))
    def __or__(self, other): return self._bin(other, np.logical_or)
    def __ror__(self, other): return Seq(np.logical_or(other, self.v))
    def __invert__(self): return Seq(np.logical_not(self.v))
    def __len__(self): return len(self.v)
    def __bool__(self): raise TypeError("Sequence used as scalar boolean")
    def hhv(self, n, min_period=1): return rolling_extreme(self, n, np.nanmax)
    def llv(self, n, min_period=1): return rolling_extreme(self, n, np.nanmin)
    def llv_bars(self, n, min_period=1): return rolling_llv_bars(self, n)
    def smma(self, n=5, m=1): return smma(self, n, m)
    def sum(self, n): return sum_(self, n)


OHLC = {"open": Seq(open_arr), "high": Seq(high_arr), "low": Seq(low_arr), "close": Seq(close_arr)}


class Color:
    white = ("named", "white")
    gray = ("named", "gray")
    blue = ("named", "blue")
    @staticmethod
    def hex(value): return ("hex", value)
    @staticmethod
    def rgb(r, g, b, a=255): return ("rgb", r, g, b, a)


class Line:
    line = "line"
    line_dashed = "line_dashed"
    line_dotted = "line_dotted"


class Shape:
    labeldown = "labeldown"
    labelup = "labelup"
    triangledown = "triangledown"
    triangleup = "triangleup"


def as_seq(x):
    if isinstance(x, Seq): return x
    if isinstance(x, tuple):
        a = np.empty(N, dtype=object); a[:] = [x] * N; return Seq(a)
    return Seq(np.full(N, x))


def ref_fn(x, n):
    a = as_seq(x).v
    n = int(n)
    if a.dtype.kind == "b":
        out = np.zeros(N, dtype=bool)
    elif a.dtype.kind in "OUS":
        out = np.empty(N, dtype=object); out[:] = None
    else:
        out = np.full(N, np.nan)
    if n == 0: return Seq(a)
    if n > 0: out[n:] = a[:-n]
    else: out[:n] = a[-n:]
    return Seq(out)


def open_(ref=0): return ref_fn(OHLC["open"], ref)
def high_(ref=0): return ref_fn(OHLC["high"], ref)
def low_(ref=0): return ref_fn(OHLC["low"], ref)
def close_(ref=0): return ref_fn(OHLC["close"], ref)


def replace_na(x, value):
    a = as_seq(x).v.copy()
    if a.dtype.kind in "fc": a[np.isnan(a)] = value
    elif a.dtype.kind == "O":
        a = np.asarray([value if z is None or (isinstance(z, float) and math.isnan(z)) else z for z in a])
    return Seq(a)


def fill_na(x, method="forward"):
    a = as_seq(x).v.astype(float, copy=True)
    if method == "forward":
        held = np.nan
        for i, z in enumerate(a):
            if np.isnan(z): a[i] = held
            else: held = z
    elif method == "backward":
        held = np.nan
        for i in range(N - 1, -1, -1):
            if np.isnan(a[i]): a[i] = held
            else: held = a[i]
    else: raise ValueError(method)
    return Seq(a)


def is_na(x):
    a = as_seq(x).v
    if a.dtype.kind in "fc": return Seq(np.isnan(a))
    return Seq(np.asarray([z is None for z in a]))


def bars_last(cond):
    c = as_seq(cond).v.astype(bool); out = np.full(N, np.nan); last = None
    for i, v in enumerate(c):
        if v: last = i
        if last is not None: out[i] = i - last
    return Seq(out)


def bars_next(cond):
    c = as_seq(cond).v.astype(bool); out = np.full(N, np.nan); nxt = None
    for i in range(N - 1, -1, -1):
        if c[i]: nxt = i
        if nxt is not None: out[i] = nxt - i
    return Seq(out)


def bars_count(x): return Seq(np.arange(1, N + 1, dtype=float))
def curr_bars_count(x): return Seq(np.arange(N - 1, -1, -1, dtype=float))


def rolling_extreme(x, n, fn):
    a = as_seq(x).v.astype(float); n = int(n); out = np.full(N, np.nan)
    for i in range(N):
        w = a[max(0, i - n + 1): i + 1]
        if not np.all(np.isnan(w)): out[i] = fn(w)
    return Seq(out)


def rolling_llv_bars(x, n):
    a = as_seq(x).v.astype(float); n = int(n); out = np.full(N, np.nan)
    for i in range(N):
        start = max(0, i - n + 1); w = a[start:i + 1]
        if np.all(np.isnan(w)): continue
        minimum = np.nanmin(w); matches = np.flatnonzero(np.isclose(w, minimum, rtol=0.0, atol=0.0))
        if len(matches): out[i] = len(w) - 1 - matches[-1]
    return Seq(out)


def smma(x, n=5, m=1):
    a = as_seq(x).v.astype(float); out = np.full(N, np.nan); alpha = float(m) / int(n)
    valid = np.flatnonzero(~np.isnan(a))
    if not len(valid): return Seq(out)
    start = int(valid[0]); out[start] = a[start]
    for i in range(start + 1, N): out[i] = out[i - 1] if np.isnan(a[i]) else alpha * a[i] + (1 - alpha) * out[i - 1]
    return Seq(out)


def sum_(x, n):
    a = as_seq(x).v.astype(float); n = int(n)
    if n == 0: return Seq(np.cumsum(np.nan_to_num(a, nan=0.0)))
    out = np.full(N, np.nan)
    for i in range(N): out[i] = np.nansum(a[max(0, i - n + 1): i + 1])
    return Seq(out)


def max_(*args):
    if all(not isinstance(x, Seq) for x in args): return builtins.max(*args)
    arrays = [as_seq(x).v for x in args]; out = arrays[0]
    for a in arrays[1:]: out = np.maximum(out, a)
    return Seq(out)


def min_(*args):
    if all(not isinstance(x, Seq) for x in args): return builtins.min(*args)
    arrays = [as_seq(x).v for x in args]; out = arrays[0]
    for a in arrays[1:]: out = np.minimum(out, a)
    return Seq(out)


def abs_(x): return Seq(np.abs(as_seq(x).v)) if isinstance(x, Seq) else builtins.abs(x)


def floor_(x): return Seq(np.floor(as_seq(x).v)) if isinstance(x, Seq) else math.floor(x)


def math_log(x, base):
    if isinstance(x, Seq):
        with np.errstate(divide="ignore", invalid="ignore"):
            return Seq(np.log(as_seq(x).v) / math.log(base))
    return math.log(x, base)


def year_(source): return Seq(date_arr.astype("datetime64[Y]").astype(int) + 1970)
def month_(source): return Seq((date_arr.astype("datetime64[M]").astype(int) % 12) + 1)
def day_(source): return Seq((date_arr - date_arr.astype("datetime64[M]")).astype(int) + 1)


def iff(logical, a, b):
    cond = as_seq(logical).v.astype(bool)
    return Seq(np.where(cond, as_seq(a).v, as_seq(b).v))


def value_when(logical, x):
    cond = as_seq(logical).v.astype(bool); a = as_seq(x).v
    dtype = object if a.dtype.kind in "OUS" else float
    out = np.empty(N, dtype=dtype); out[:] = None if dtype is object else np.nan
    held = None if dtype is object else np.nan
    for i in range(N):
        if cond[i]: held = a[i]
        out[i] = held
    return Seq(out)


def filter_(cond, n):
    c = as_seq(cond).v.astype(bool); out = np.zeros(N, dtype=bool); blocked = -1
    for i, v in enumerate(c):
        if i <= blocked: continue
        if v: out[i] = True; blocked = i + int(n)
    return Seq(out)


def backset(cond, n):
    c = as_seq(cond).v.astype(bool); out = np.zeros(N, dtype=bool); n = int(n)
    for i, v in enumerate(c):
        if v: out[max(0, i - n + 1): i + 1] = True
    return Seq(out)


PLOTS = []
OUTPUTS = {}

def indicator(*args, **kwargs): pass
def input_parameter(title, default): return default
def output_parameter(**kwargs): OUTPUTS.update(kwargs)
def plot(*args, **kwargs): PLOTS.append(("plot", args))
def plot_fillcolor(*args, **kwargs): PLOTS.append(("fill", args))
def plot_text(*args, **kwargs): PLOTS.append(("text", args))
def plot_stickline(*args, **kwargs): PLOTS.append(("stick", args))
def plot_icon(*args, **kwargs): PLOTS.append(("icon", args))
def plot_hline(*args, **kwargs): PLOTS.append(("hline", args))
def plot_candlestick(*args, **kwargs): PLOTS.append(("candle", args))


def install_ftool():
    public = {
        "Color": Color, "Line": Line, "Shape": Shape,
        "indicator": indicator, "input_parameter": input_parameter, "output_parameter": output_parameter,
        "open": open_, "high": high_, "low": low_, "close": close_, "ref": ref_fn,
        "replace_na": replace_na, "fill_na": fill_na, "is_na": is_na,
        "bars_last": bars_last, "bars_next": bars_next, "bars_count": bars_count,
        "curr_bars_count": curr_bars_count, "max": max_, "min": min_, "abs": abs_,
        "iff": iff, "value_when": value_when, "filter": filter_, "backset": backset,
        "plot": plot, "plot_fillcolor": plot_fillcolor, "plot_text": plot_text,
        "plot_stickline": plot_stickline, "plot_icon": plot_icon,
        "plot_hline": plot_hline, "plot_candlestick": plot_candlestick,
    }
    module = types.ModuleType("ftool"); module.__dict__.update(public); module.__all__ = list(public)
    sys.modules["ftool"] = module

    fmath_public = {"math_log": math_log, "floor": floor_}
    fmath_module = types.ModuleType("fmath"); fmath_module.__dict__.update(fmath_public); fmath_module.__all__ = list(fmath_public)
    sys.modules["fmath"] = fmath_module

    fdatetime_public = {"year": year_, "month": month_, "day": day_}
    fdatetime_module = types.ModuleType("fdatetime"); fdatetime_module.__dict__.update(fdatetime_public); fdatetime_module.__all__ = list(fdatetime_public)
    sys.modules["fdatetime"] = fdatetime_module


def run(script):
    PLOTS.clear(); OUTPUTS.clear(); install_ftool(); runpy.run_path(str(script), run_name=f"__{script.stem}__")
    for key, value in OUTPUTS.items():
        if not isinstance(value, Seq) or len(value) != N: raise AssertionError(f"{script.name}: invalid output {key}")
    return len(PLOTS), len(OUTPUTS)


if __name__ == "__main__":
    for script in SCRIPTS:
        plots, outputs = run(script)
        print(f"{script.name}: PASS, plots={plots}, outputs={outputs}")
