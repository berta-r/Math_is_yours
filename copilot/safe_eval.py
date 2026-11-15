"""Safe evaluation of ONE Python expression written by the language model.

The model writes a single expression (e.g. ``math.comb(5, 2) * 2``) that
computes the answer to a problem. We never execute arbitrary code:

1. ``ast.parse(expression, mode="eval")``.
2. Walk the AST and reject every node type / name / attribute that is not on
   an explicit whitelist (no lambdas, assignments, imports, dunders, method
   calls, f-strings, starred args...).
3. Rewrite ``**``, ``*`` and ``%`` into calls to guarded helpers so that huge
   powers, huge sequence repetitions and ``"%*d"`` string formatting are
   refused at runtime.
4. ``eval`` the compiled, checked AST with ``{"__builtins__": {}}`` and only
   the whitelisted (and size-capped) functions in the namespace.
5. A ``SIGALRM`` timer stops runaway Python-level loops; the result size is
   checked at the end.

Standard library only (runs on the board).
"""

import ast
import itertools
import math
import signal
import threading
from fractions import Fraction
from types import SimpleNamespace

__all__ = ["SafeEvalError", "safe_eval", "extract_expression"]


class SafeEvalError(Exception):
    """Raised with a short reason when an expression can't be evaluated safely."""


# --------------------------------------------------------------------------- #
# Limits
# --------------------------------------------------------------------------- #
MAX_EXPRESSION_CHARS = 2000
MAX_RANGE = 10 ** 6            # elements per range() call (inclusive)
MAX_POW_EXPONENT = 64          # "always allowed" exponent with |base| <= MAX_POW_BASE
MAX_POW_BASE = 10 ** 9
MAX_RESULT_DIGITS = 10 ** 4    # final int result
MAX_INT_BITS = int(MAX_RESULT_DIGITS * math.log2(10)) + 1   # ~33220 bits
MAX_RESULT_LEN = 10 ** 5       # final list/tuple/set/str result
MAX_SEQ_REPEAT = 10 ** 6       # len(seq * n)
MAX_FACTORIAL = 500
MAX_COMB_N = 10 ** 4
MAX_ITERTOOLS_OUTPUT = 10 ** 6  # total tuples produced by one itertools call
MAX_ITERTOOLS_INPUT = 10 ** 4   # elements in an itertools input iterable
MAX_ITERTOOLS_REPEAT = 10
MAX_ROUND_DIGITS = 100


# --------------------------------------------------------------------------- #
# Guarded helpers
# --------------------------------------------------------------------------- #
def _is_exact(x):
    return isinstance(x, (int, Fraction))  # bool is an int


def _int_bits(x):
    """Bit size of an exact number (numerator/denominator for Fraction)."""
    if isinstance(x, Fraction):
        return max(abs(x.numerator).bit_length(), x.denominator.bit_length())
    return abs(int(x)).bit_length()


def _check_power(base, exp):
    """Refuse exact powers that would produce a huge number.

    Always allowed: |exp| <= 64 and |base| <= 10**9 (the hard rule).
    Also allowed: any exact power whose result fits in ~10**4 digits
    (so ``2**100`` or ``2**2026 % 10`` still work). Float powers are not
    capped: they overflow with OverflowError instead of eating memory.
    """
    if not (_is_exact(base) and _is_exact(exp)):
        return
    if isinstance(exp, Fraction) and exp.denominator != 1:
        return  # fractional exponent -> float result
    e = abs(int(exp))
    if e <= MAX_POW_EXPONENT and abs(base) <= MAX_POW_BASE:
        return
    if abs(base) <= 1:
        return
    if e > MAX_INT_BITS or _int_bits(base) * e > MAX_INT_BITS:
        raise SafeEvalError("result too big: power %s ** %s" % (_short(base), _short(exp)))


def _short(x):
    if isinstance(x, int) and _int_bits(x) > 64:
        return "<%d-bit int>" % _int_bits(x)
    s = repr(x)
    return s if len(s) <= 40 else s[:37] + "..."


def _safe_pow_op(a, b):
    _check_power(a, b)
    return a ** b


def _safe_pow(base, exp, mod=None):
    if mod is None:
        _check_power(base, exp)
        return pow(base, exp)
    return pow(base, exp, mod)


def _seq_len_check(seq, n):
    if isinstance(seq, (str, bytes, list, tuple)) and isinstance(n, int):
        if n > 0 and len(seq) * n > MAX_SEQ_REPEAT:
            raise SafeEvalError("result too big: sequence repetition")


def _safe_mul(a, b):
    _seq_len_check(a, b)
    _seq_len_check(b, a)
    return a * b


def _safe_mod(a, b):
    if isinstance(a, (str, bytes)):
        raise SafeEvalError("forbidden: string formatting with %")
    return a % b


def _safe_range(*args):
    try:
        r = range(*args)
    except TypeError as exc:
        raise SafeEvalError("runtime error: TypeError: %s" % exc)
    if len(r) > MAX_RANGE:
        raise SafeEvalError("range too big: %d elements (max %d)" % (len(r), MAX_RANGE))
    return r


def _safe_round(number, ndigits=None):
    if ndigits is None:
        return round(number)
    if isinstance(ndigits, int) and abs(ndigits) > MAX_ROUND_DIGITS:
        raise SafeEvalError("round: ndigits too large")
    return round(number, ndigits)


def _safe_factorial(n):
    if isinstance(n, (int, float)) and n > MAX_FACTORIAL:
        raise SafeEvalError("factorial argument too big (max %d)" % MAX_FACTORIAL)
    return math.factorial(n)


def _safe_comb(n, k):
    if isinstance(n, int) and n > MAX_COMB_N:
        raise SafeEvalError("comb argument too big (max %d)" % MAX_COMB_N)
    return math.comb(n, k)


def _safe_perm(n, k=None):
    if isinstance(n, int) and n > MAX_COMB_N:
        raise SafeEvalError("perm argument too big (max %d)" % MAX_COMB_N)
    return math.perm(n, k)


def _safe_prod(iterable, start=1):
    """Pure-Python prod: interruptible by the timer and capped in size."""
    result = start
    for x in iterable:
        result = result * x
        if _is_exact(result) and _int_bits(result) > MAX_INT_BITS:
            raise SafeEvalError("result too big: prod")
    return result


def _materialize(iterable):
    """Turn an itertools input into a tuple, refusing huge inputs."""
    items = []
    for x in iterable:
        items.append(x)
        if len(items) > MAX_ITERTOOLS_INPUT:
            raise SafeEvalError("itertools input too big (max %d)" % MAX_ITERTOOLS_INPUT)
    return tuple(items)


def _check_count(count, name):
    if count > MAX_ITERTOOLS_OUTPUT:
        raise SafeEvalError("%s too big: %d tuples (max %d)" % (name, count, MAX_ITERTOOLS_OUTPUT))


def _safe_permutations(iterable, r=None):
    pool = _materialize(iterable)
    n = len(pool)
    rr = n if r is None else r
    if isinstance(rr, int) and 0 <= rr <= n:
        _check_count(math.perm(n, rr), "permutations")
    return itertools.permutations(pool, r)


def _safe_combinations(iterable, r):
    pool = _materialize(iterable)
    n = len(pool)
    if isinstance(r, int) and 0 <= r <= n:
        _check_count(math.comb(n, r), "combinations")
    return itertools.combinations(pool, r)


def _safe_cwr(iterable, r):
    pool = _materialize(iterable)
    n = len(pool)
    if isinstance(r, int) and r >= 0 and n > 0:
        if r > MAX_ITERTOOLS_OUTPUT:
            _check_count(r, "combinations_with_replacement")
        _check_count(math.comb(n + r - 1, r), "combinations_with_replacement")
    return itertools.combinations_with_replacement(pool, r)


def _safe_product(*iterables, repeat=1):
    if not isinstance(repeat, int) or repeat > MAX_ITERTOOLS_REPEAT:
        raise SafeEvalError("product repeat too big (max %d)" % MAX_ITERTOOLS_REPEAT)
    pools = [_materialize(it) for it in iterables]
    count = 1
    for _ in range(max(repeat, 0)):
        for p in pools:
            count *= len(p)
            _check_count(count, "product")
    return itertools.product(*pools, repeat=repeat)


# --------------------------------------------------------------------------- #
# Whitelists
# --------------------------------------------------------------------------- #
_MATH_FUNCS = {
    "gcd": math.gcd,
    "lcm": math.lcm,
    "sqrt": math.sqrt,
    "factorial": _safe_factorial,
    "comb": _safe_comb,
    "perm": _safe_perm,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "prod": _safe_prod,
    "isqrt": math.isqrt,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "hypot": math.hypot,
}
_ITERTOOLS_FUNCS = {
    "permutations": _safe_permutations,
    "combinations": _safe_combinations,
    "product": _safe_product,
    "combinations_with_replacement": _safe_cwr,
}
_FRACTIONS_FUNCS = {"Fraction": Fraction}

# The modules are replaced by plain namespaces holding only the whitelisted
# (wrapped) callables, as defence in depth behind the AST attribute check.
_MODULES = {
    "math": _MATH_FUNCS,
    "itertools": _ITERTOOLS_FUNCS,
    "fractions": _FRACTIONS_FUNCS,
}

_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "divmod": divmod,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": _safe_pow,
    "range": _safe_range,
    "reversed": reversed,
    "round": _safe_round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "Fraction": Fraction,
}

# Names the rewritten AST uses for the guarded operators. They are dunder
# names, so the model can never reference them (dunders are rejected).
_POW_HELPER = "__se_pow__"
_MUL_HELPER = "__se_mul__"
_MOD_HELPER = "__se_mod__"


def _make_globals():
    g = {"__builtins__": {}}
    g.update(_BUILTINS)
    for mod_name, funcs in _MODULES.items():
        g[mod_name] = SimpleNamespace(**funcs)
    g[_POW_HELPER] = _safe_pow_op
    g[_MUL_HELPER] = _safe_mul
    g[_MOD_HELPER] = _safe_mod
    return g


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub, ast.Not)
_ALLOWED_CMPOPS = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
                   ast.Is, ast.IsNot, ast.In, ast.NotIn)
_ALLOWED_CONST_TYPES = (int, float, complex, str, bool, type(None))


# --------------------------------------------------------------------------- #
# AST validation
# --------------------------------------------------------------------------- #
class _Validator:
    """Recursive whitelist check. Raises SafeEvalError("forbidden: ...")."""

    def __init__(self):
        self.bound = set()  # comprehension variables seen so far

    def fail(self, what):
        raise SafeEvalError("forbidden: %s" % what)

    def check_name(self, name):
        if name.startswith("__") or "__" in name:
            self.fail("dunder name %r" % name)

    def visit(self, node):
        method = getattr(self, "visit_" + type(node).__name__, None)
        if method is None:
            self.fail(type(node).__name__)
        method(node)

    # -- leaves -------------------------------------------------------------
    def visit_Expression(self, node):
        self.visit(node.body)

    def visit_Constant(self, node):
        if not isinstance(node.value, _ALLOWED_CONST_TYPES):
            self.fail("constant of type %s" % type(node.value).__name__)

    def visit_Name(self, node):
        self.check_name(node.id)
        if not isinstance(node.ctx, ast.Load):
            self.fail("assignment to %r" % node.id)
        if node.id in self.bound or node.id in _BUILTINS or node.id in _MODULES:
            return
        self.fail("name %r" % node.id)

    # -- operators ----------------------------------------------------------
    def visit_BinOp(self, node):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            self.fail("operator %s" % type(node.op).__name__)
        self.visit(node.left)
        self.visit(node.right)

    def visit_UnaryOp(self, node):
        if not isinstance(node.op, _ALLOWED_UNARYOPS):
            self.fail("operator %s" % type(node.op).__name__)
        self.visit(node.operand)

    def visit_BoolOp(self, node):
        for v in node.values:
            self.visit(v)

    def visit_Compare(self, node):
        for op in node.ops:
            if not isinstance(op, _ALLOWED_CMPOPS):
                self.fail("comparison %s" % type(op).__name__)
        self.visit(node.left)
        for c in node.comparators:
            self.visit(c)

    def visit_IfExp(self, node):
        self.visit(node.test)
        self.visit(node.body)
        self.visit(node.orelse)

    # -- containers ---------------------------------------------------------
    def _visit_elts(self, node):
        for e in node.elts:
            if isinstance(e, ast.Starred):
                self.fail("starred expression")
            self.visit(e)
        if not isinstance(getattr(node, "ctx", ast.Load()), ast.Load):
            self.fail("assignment")

    visit_Tuple = _visit_elts
    visit_List = _visit_elts

    def visit_Set(self, node):
        self._visit_elts(node)

    def visit_Subscript(self, node):
        if not isinstance(node.ctx, ast.Load):
            self.fail("assignment")
        self.visit(node.value)
        sl = node.slice
        # Python 3.8 compatibility wrappers.
        if type(sl).__name__ == "Index":
            sl = sl.value  # pragma: no cover
        self.visit(sl)

    def visit_Slice(self, node):
        for part in (node.lower, node.upper, node.step):
            if part is not None:
                self.visit(part)

    # -- comprehensions -----------------------------------------------------
    def _bind_target(self, target):
        if isinstance(target, ast.Name):
            self.check_name(target.id)
            if target.id in _BUILTINS or target.id in _MODULES:
                self.fail("comprehension variable shadows %r" % target.id)
            self.bound.add(target.id)
        elif isinstance(target, ast.Tuple):
            for elt in target.elts:
                self._bind_target(elt)
        else:
            self.fail("comprehension target %s" % type(target).__name__)

    def _visit_comp(self, node):
        for gen in node.generators:
            if getattr(gen, "is_async", 0):
                self.fail("async comprehension")
            self.visit(gen.iter)
            self._bind_target(gen.target)
            for cond in gen.ifs:
                self.visit(cond)
        self.visit(node.elt)

    visit_ListComp = _visit_comp
    visit_SetComp = _visit_comp
    visit_GeneratorExp = _visit_comp

    # -- calls and attributes -----------------------------------------------
    def visit_Attribute(self, node):
        if not isinstance(node.ctx, ast.Load):
            self.fail("assignment")
        value = node.value
        if not (isinstance(value, ast.Name) and value.id in _MODULES
                and value.id not in self.bound):
            self.fail("attribute access .%s" % node.attr)
        if node.attr not in _MODULES[value.id]:
            self.fail("%s.%s" % (value.id, node.attr))

    def visit_Call(self, node):
        func = node.func
        if isinstance(func, ast.Name):
            if func.id not in _BUILTINS or func.id in self.bound:
                self.fail("call to %r" % func.id)
        elif isinstance(func, ast.Attribute):
            self.visit_Attribute(func)
        else:
            self.fail("call to %s" % type(func).__name__)
        for a in node.args:
            if isinstance(a, ast.Starred):
                self.fail("starred argument")
            self.visit(a)
        for kw in node.keywords:
            if kw.arg is None:
                self.fail("**kwargs")
            self.check_name(kw.arg)
            self.visit(kw.value)


class _GuardOperators(ast.NodeTransformer):
    """Rewrite a ** b, a * b, a % b into calls to the guarded helpers."""

    _HELPERS = {ast.Pow: _POW_HELPER, ast.Mult: _MUL_HELPER, ast.Mod: _MOD_HELPER}

    def visit_BinOp(self, node):
        self.generic_visit(node)
        helper = self._HELPERS.get(type(node.op))
        if helper is None:
            return node
        call = ast.Call(func=ast.Name(id=helper, ctx=ast.Load()),
                        args=[node.left, node.right], keywords=[])
        return ast.copy_location(call, node)


# --------------------------------------------------------------------------- #
# Timeout
# --------------------------------------------------------------------------- #
class _Timeout(BaseException):
    """BaseException so a generic `except Exception` in user-level code can't eat it."""


def _alarm_handler(signum, frame):
    raise _Timeout()


def _can_use_alarm():
    return (hasattr(signal, "setitimer") and hasattr(signal, "SIGALRM")
            and threading.current_thread() is threading.main_thread())


# --------------------------------------------------------------------------- #
# Result checks
# --------------------------------------------------------------------------- #
_RESULT_TYPES = (bool, int, float, complex, Fraction, str, tuple, list, set,
                 frozenset, type(None))


def _check_result(value):
    if isinstance(value, range):
        value = list(value)
    elif not isinstance(value, _RESULT_TYPES) and hasattr(value, "__next__"):
        # A generator / zip / permutations object: materialise it, capped.
        value = list(itertools.islice(value, MAX_RESULT_LEN + 1))
    if not isinstance(value, _RESULT_TYPES):
        raise SafeEvalError("unsupported result type %s" % type(value).__name__)
    if isinstance(value, int) and not isinstance(value, bool):
        if _int_bits(value) > MAX_INT_BITS:
            raise SafeEvalError("result too big: int with more than %d digits" % MAX_RESULT_DIGITS)
    elif isinstance(value, Fraction):
        if _int_bits(value) > MAX_INT_BITS:
            raise SafeEvalError("result too big: Fraction")
    elif isinstance(value, (list, tuple, set, frozenset, str)):
        if len(value) > MAX_RESULT_LEN:
            raise SafeEvalError("result too big: %s of length > %d"
                                % (type(value).__name__, MAX_RESULT_LEN))
    return value


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def safe_eval(expression: str, timeout: float = 2.0):
    """Evaluate one Python expression written by the model. Returns the value
    (int, float, Fraction, bool, str, tuple, list, set) or raises SafeEvalError
    with a short reason (syntax error, forbidden construct, timeout, runtime error,
    result too big)."""
    if not isinstance(expression, str):
        raise SafeEvalError("forbidden: expression is not a string")
    expression = expression.strip()
    if not expression:
        raise SafeEvalError("syntax error: empty expression")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise SafeEvalError("forbidden: expression longer than %d chars" % MAX_EXPRESSION_CHARS)

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise SafeEvalError("syntax error: %s" % (exc.msg or exc))
    except (ValueError, RecursionError, MemoryError) as exc:
        raise SafeEvalError("syntax error: %s" % type(exc).__name__)

    try:
        _Validator().visit(tree)
    except RecursionError:
        raise SafeEvalError("forbidden: expression nested too deeply")

    try:
        tree = ast.fix_missing_locations(_GuardOperators().visit(tree))
        code = compile(tree, "<model-expression>", "eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
        raise SafeEvalError("syntax error: %s" % type(exc).__name__)

    namespace = _make_globals()
    use_alarm = timeout is not None and timeout > 0 and _can_use_alarm()
    old_handler = None
    if use_alarm:
        old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    try:
        if use_alarm:
            signal.setitimer(signal.ITIMER_REAL, timeout)
        value = eval(code, namespace)  # noqa: S307 - AST checked, empty builtins
        value = _check_result(value)
    except _Timeout:
        raise SafeEvalError("timeout")
    except SafeEvalError:
        raise
    except RecursionError:
        raise SafeEvalError("runtime error: RecursionError")
    except MemoryError:
        raise SafeEvalError("result too big: MemoryError")
    except Exception as exc:  # ZeroDivisionError, ValueError, TypeError, ...
        msg = str(exc)
        if len(msg) > 120:
            msg = msg[:117] + "..."
        raise SafeEvalError("runtime error: %s: %s" % (type(exc).__name__, msg))
    finally:
        if use_alarm:
            _disarm(old_handler)
    return value


def _disarm(old_handler):
    """Stop the timer and restore the handler, even if the alarm fires right now."""
    try:
        signal.setitimer(signal.ITIMER_REAL, 0)
    except _Timeout:  # pragma: no cover - fired between finally and setitimer
        signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, old_handler)


# --------------------------------------------------------------------------- #
# Model-output cleanup
# --------------------------------------------------------------------------- #
_PREFIXES = ("answer:", "expression:", "python:", "result:", "final answer:",
             "answer =", "result =", "expr:", "code:")


def _strip_comment(line):
    """Drop a trailing # comment, ignoring # inside string literals."""
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#":
            return line[:i]
        i += 1
    return line


def extract_expression(text: str) -> str:
    """Return the best candidate expression from raw model output.

    Strips markdown code fences, takes the first non-empty line, removes a
    leading ``>>>`` / ``Answer:`` / ``=`` and a trailing ``#`` comment, ``.``
    or ``;``. Returns "" if nothing is left.
    """
    if not text:
        return ""
    text = str(text).replace("\r\n", "\n")

    # Prefer the content of the first fenced code block, if any.
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            block = parts[1]
            first_nl = block.find("\n")
            if first_nl != -1:
                header = block[:first_nl].strip()
                # ```python / ```py / ``` -> drop the language tag line.
                if header == "" or (header.isalnum() and not header.isdigit()
                                    and header.lower() in ("python", "py", "python3")):
                    block = block[first_nl + 1:]
            text = block
        else:
            text = text.replace("```", "")

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.lower() in ("python", "py", "python3"):
            continue
        # Leading markers, possibly repeated ("Answer: = 2+3").
        changed = True
        while changed:
            changed = False
            if line.startswith(">>>"):
                line, changed = line[3:].strip(), True
            low = line.lower()
            for p in _PREFIXES:
                if low.startswith(p):
                    line, changed = line[len(p):].strip(), True
                    break
            if line.startswith("=") and not line.startswith("=="):
                line, changed = line[1:].strip(), True
        line = _strip_comment(line).strip()
        # Inline code backticks.
        line = line.strip("`").strip()
        # Trailing punctuation.
        while line and line[-1] in ".;":
            line = line[:-1].rstrip()
        if line:
            return line
    return ""
