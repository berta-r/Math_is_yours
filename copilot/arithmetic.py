"""Small, exact arithmetic tutor. No model, network, eval or third-party packages.

``respond`` returns ``None`` for language/concept questions so the caller can use
the SLM. Render only ``message``; ``state`` and ``verification`` are private
server-side data. They can contain an exercise's result and must not be sent to
the browser or used as evidence that the student has solved the whole problem.
"""

import ast
from fractions import Fraction
import re


MAX_LENGTH = 160
MAX_NODES = 40
MAX_DEPTH = 12
MAX_MAGNITUDE = 10 ** 12
_NUMBER = r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
_CHARACTERS = re.compile(r"[0-9.\s()+*/-]+\Z")
_NUMERIC_LITERAL = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z")
_PREFIX = re.compile(
    r"^(?:what\s+is|what's|calculate|compute|evaluate|check|"
    r"how\s+much\s+is|quant\s+[ée]s|quan\s+fa|quant\s+fa|"
    r"calcula|comprova)\s+", re.IGNORECASE)
_CLAIM = re.compile(
    r"^(?:i\s+got|i\s+get|my\s+answer\s+is|he\s+obtingut|"
    r"m'ha\s+donat|em\s+d[oó]na|em\s+surt)\s+(.+?)\s+"
    r"(?:for|per\s+a|a|per)\s+(.+)$", re.IGNORECASE)
_ANSWER = re.compile(
    r"^(?:i\s+got|i\s+get|it\s+is|it's|the\s+answer\s+is|"
    r"he\s+obtingut|m'ha\s+donat|em\s+d[oó]na|em\s+surt|[ée]s)\s+",
    re.IGNORECASE)
_OPERATORS = (
    (r"\b(?:multiplied\s+by|multiplicat\s+per)\b", "*"),
    (r"\b(?:divided\s+by|dividit\s+per)\b", "/"),
    (r"\b(?:plus|més|mes)\b", "+"),
    (r"\b(?:minus|menys)\b", "-"),
    (r"\b(?:times|per)\b", "*"),
)


class ArithmeticError(ValueError):
    """An expression cannot be evaluated by this bounded arithmetic tool."""


def _normalise(text):
    text = text.strip().lower().replace("−", "-").replace("–", "-")
    text = text.replace("×", "*").replace("÷", "/").replace("’", "'")
    for pattern, replacement in _OPERATORS:
        text = re.sub(pattern, replacement, text)
    return text.strip()


def _bounded(value):
    if abs(value.numerator) > MAX_MAGNITUDE or value.denominator > MAX_MAGNITUDE:
        raise ArithmeticError("limit")
    return value


def _evaluate(expression):
    """Return (Fraction, AST) after validating every node and intermediate."""
    if not expression or len(expression) > MAX_LENGTH:
        raise ArithmeticError("limit")
    if not _CHARACTERS.fullmatch(expression):
        raise ArithmeticError("unsupported")
    if "**" in expression or "//" in expression:
        raise ArithmeticError("unsupported")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        raise ArithmeticError("syntax") from None
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise ArithmeticError("limit")

    def visit(node, depth=0):
        if depth > MAX_DEPTH:
            raise ArithmeticError("limit")
        if isinstance(node, ast.Expression):
            return visit(node.body, depth + 1)
        if isinstance(node, ast.Constant):
            token = ast.get_source_segment(expression, node)
            if not token or not _NUMERIC_LITERAL.fullmatch(token):
                raise ArithmeticError("unsupported")
            # Parse the original decimal spelling, never the AST's float value.
            try:
                return _bounded(Fraction(token))
            except (ValueError, OverflowError):
                raise ArithmeticError("syntax") from None
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand, depth + 1)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = visit(node.left, depth + 1), visit(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                return _bounded(left + right)
            if isinstance(node.op, ast.Sub):
                return _bounded(left - right)
            if isinstance(node.op, ast.Mult):
                return _bounded(left * right)
            if right == 0:
                raise ArithmeticError("zero")
            return _bounded(left / right)
        raise ArithmeticError("unsupported")

    return visit(tree), tree.body


def _format(value):
    """Prefer finite decimal spelling when it needs at most 12 places."""
    if value.denominator == 1:
        return str(value.numerator)
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    places = max(twos, fives)
    if denominator == 1 and places <= 12:
        scaled = abs(value.numerator) * 2 ** (places - twos) * 5 ** (places - fives)
        digits = str(scaled).zfill(places + 1)
        return ("-" if value < 0 else "") + digits[:-places] + "." + digits[-places:]
    return str(value)


def _display(expression):
    return expression.replace("*", "×").replace("/", "÷").replace("-", "−")


def _parse(text):
    """Recognise an entire arithmetic request; never extract incidental digits."""
    text = text.strip().replace("’", "'").rstrip(" ?.;").strip()
    text = _PREFIX.sub("", text, count=1)
    claimed = _CLAIM.fullmatch(text)
    if claimed:
        return _normalise(claimed.group(2)), _normalise(claimed.group(1))
    if text.count("=") == 1:
        left, right = (_normalise(part) for part in text.split("="))
        # Allow either "18-6=12" or "12=18-6" without changing meaning.
        if re.fullmatch(_NUMBER, left) and not re.fullmatch(_NUMBER, right):
            left, right = right, left
        return left, right
    expression = _normalise(text)
    if _CHARACTERS.fullmatch(expression):
        return expression, None
    # A recognisable numeric expression with an unsupported operator is rejected
    # explicitly. Natural-language questions remain the SLM's responsibility.
    if re.fullmatch(r"[0-9.\s()+*/^%<>=!-]+", expression or ""):
        return expression, None
    return None


def _steps(expression, tree):
    """Build small exact operations in dependency order; no generated math."""
    result, _ = _evaluate(expression)
    if isinstance(tree, ast.BinOp) and isinstance(tree.op, ast.Sub):
        left = ast.get_source_segment(expression, tree.left)
        right = ast.get_source_segment(expression, tree.right)
        a, _ = _evaluate(left)
        b, _ = _evaluate(right)
        if a.denominator == b.denominator == 1 and 10 <= a <= 99 and 0 < b <= a % 10:
            units = a.numerator % 10
            tens = a.numerator - units
            first = f"{units} - {_format(b)}"
            remaining, _ = _evaluate(first)
            second = f"{tens} + {_format(remaining)}"
            verified, _ = _evaluate(second)
            if verified == result:
                return [first, second], (str(a), str(tens), str(units))

    steps = []

    def walk(node):
        if isinstance(node, ast.BinOp):
            a = walk(node.left)
            b = walk(node.right)
            operator = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(node.op)]
            # Parentheses preserve the meaning of negative and fractional parts.
            step = f"({_format(a)}) {operator} ({_format(b)})"
            value, _ = _evaluate(step)
            steps.append(step)
            return value
        if isinstance(node, ast.UnaryOp):
            value = walk(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        value, _ = _evaluate(ast.get_source_segment(expression, node))
        return value

    walked = walk(tree)
    if not steps or _evaluate(steps[-1])[0] != result or walked != result:
        # A unary minus around a compound expression requires a final step.
        steps.append(expression)
    return steps, None


def _response(message, state=None, **verification):
    return {"message": message, "source": "verified_arithmetic", "action": "arithmetic",
            "state": state, "verification": verification}


def _invalid(error, catalan):
    if str(error) == "zero":
        message = ("No podem dividir per zero. Revisa el divisor abans de continuar." if catalan else
                   "We cannot divide by zero. Check the divisor before continuing.")
    elif str(error) == "limit":
        message = ("Aquest càlcul és massa llarg o té nombres massa grans. Escriu un pas més petit." if catalan else
                   "This calculation is too long or its numbers are too large. Enter one smaller step.")
    else:
        message = ("Escriu un càlcul amb nombres, parèntesis i +, −, × o ÷. Encara no puc verificar aquesta expressió." if catalan else
                   "Enter a calculation using numbers, parentheses and +, −, × or ÷. I cannot verify this expression yet.")
    return _response(message, status="invalid")


def _state(expression, step):
    return {"kind": "arithmetic_v1", "expression": expression, "step": step}


def _pending(previous):
    if not isinstance(previous, dict) or previous.get("kind") != "arithmetic_v1":
        return None
    expression, step = previous.get("expression"), previous.get("step")
    if not isinstance(expression, str) or type(step) is not int:
        return None
    try:
        result, tree = _evaluate(expression)
        steps, split = _steps(expression, tree)
    except ArithmeticError:
        return None
    if not 0 <= step < len(steps):
        return None
    return expression, result, steps, step


def _completion(catalan):
    return ("Aquest càlcul és correcte. Ara explica què representa en el problema; encara no hem comprovat tota la solució."
            if catalan else
            "This arithmetic checks out. Now explain what it represents in the problem; we have not checked the whole solution yet.")


def _continue(text, previous, catalan):
    pending = _pending(previous)
    if pending is None:
        return None
    expression, result, steps, step = pending
    answer = _normalise(_ANSWER.sub("", text.strip().rstrip(" ?.;"), count=1))
    # Numeric replies may be fractions. Other calculations start a new request.
    if not re.fullmatch(_NUMBER + r"(?:\s*/\s*" + _NUMBER + r")?", answer):
        parsed = _parse(text)
        if parsed is None or parsed[1] is None:
            return None
        try:
            candidate, _ = _evaluate(parsed[0])
            # An explicit equality for this step (or the full calculation) can
            # complete it, but an unrelated equality must start a new request.
            if ast.dump(ast.parse(parsed[0], mode="eval")) not in (
                    ast.dump(ast.parse(steps[step], mode="eval")),
                    ast.dump(ast.parse(expression, mode="eval"))):
                return None
            claimed, _ = _evaluate(parsed[1])
            if candidate == result and claimed == result and parsed[0] == expression:
                return _response(_completion(catalan), expression=expression, result=_format(result),
                                 claim_correct=True, status="complete")
            answer = parsed[1]
        except ArithmeticError as error:
            return _invalid(error, catalan)
    try:
        value, _ = _evaluate(answer)
        expected, _ = _evaluate(steps[step])
    except ArithmeticError as error:
        return _invalid(error, catalan)
    if value != expected:
        prompt = (f"Revisa aquest pas: quant és {_display(steps[step])}?" if catalan else
                  f"Check this smaller step again: what is {_display(steps[step])}?")
        return _response(prompt, _state(expression, step), expression=expression,
                         result=_format(result), claim_correct=False, status="guided")
    step += 1
    if step == len(steps):
        return _response(_completion(catalan), expression=expression, result=_format(result),
                         claim_correct=True, status="complete")
    prompt = (f"Aquest pas és correcte. Ara calcula {_display(steps[step])}. Què obtens?" if catalan else
              f"That step checks out. Now calculate {_display(steps[step])}. What do you get?")
    return _response(prompt, _state(expression, step), expression=expression,
                     result=_format(result), claim_correct=True, status="guided")


def respond(text, language="eng", guided=False, previous=None):
    """Verify a whole arithmetic input, or return None for the conceptual SLM.

    ``guided`` should be true for every unfinished exercise. ``previous`` is the
    prior returned state, stored privately with the conversation by the caller.
    A wrong proposed result receives a check step even outside an exercise.
    Expressions support exact decimals, fractions, parentheses and + - * /.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    catalan = language in ("cat", "ca", "catalan")
    if len(text) > MAX_LENGTH:
        # The tool's arithmetic limit must not intercept long conceptual chats.
        if _parse(text[:MAX_LENGTH + 1]) is not None:
            return _invalid(ArithmeticError("limit"), catalan)
        return None
    if previous is not None:
        continued = _continue(text, previous, catalan)
        if continued is not None:
            return continued
    parsed = _parse(text)
    if parsed is None:
        return None
    expression, claim = parsed
    # A number by itself is a conversation reply, not a calculation request.
    if claim is None and re.fullmatch(_NUMBER, expression):
        return None
    try:
        result, tree = _evaluate(expression)
        proposed = _evaluate(claim)[0] if claim is not None else None
        steps, split = _steps(expression, tree)
    except ArithmeticError as error:
        return _invalid(error, catalan)
    metadata = {"expression": expression, "result": _format(result),
                "claim_correct": None if proposed is None else proposed == result}
    if proposed == result:
        return _response(_completion(catalan) if guided else (
            "Sí, aquest càlcul és correcte." if catalan else "Yes, that calculation checks out."),
            **metadata, status="complete")
    if guided or proposed is not None:
        prefix = ("El resultat proposat no coincideix amb el càlcul. " if catalan else
                  "The proposed result does not match the calculation. ") if proposed is not None else ""
        if split:
            number, tens, units = split
            prompt = (f"Separa {number} en {tens} + {units}. Primer calcula {_display(steps[0])}. Què obtens?" if catalan else
                      f"Split {number} into {tens} + {units}. First calculate {_display(steps[0])}. What do you get?")
        else:
            prompt = (f"Fem un pas cada vegada. Com calcularies {_display(steps[0])}? Explica el pas o escriu el resultat." if catalan else
                      f"Let's take one step at a time. How would you calculate {_display(steps[0])}? Explain the step or enter its result.")
        return _response(prefix + prompt, _state(expression, 0), **metadata, status="guided")
    equation = f"{_display(expression)} = {_format(result)}. "
    explanation = ("Calcula primer els parèntesis i després les multiplicacions i divisions, abans de sumar o restar."
                   if catalan else
                   "Work inside parentheses first, then multiply and divide before adding or subtracting.")
    if isinstance(tree, ast.BinOp) and isinstance(tree.op, ast.Sub):
        a, _ = _evaluate(ast.get_source_segment(expression, tree.left))
        b, _ = _evaluate(ast.get_source_segment(expression, tree.right))
        explanation = (("Comprovació: " if catalan else "Check by adding back: ") +
                       f"{_format(result)} + ({_format(b)}) = {_format(a)}.")
    return _response(equation + explanation, **metadata, status="complete")
