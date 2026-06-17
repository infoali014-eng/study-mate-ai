import re

try:
    import numpy as np
    import plotly.graph_objects as go
    import sympy as sp
except Exception:
    np = None
    go = None
    sp = None


x = sp.symbols("x") if sp else None
t = sp.symbols("t") if sp else None

VISUAL_INTENT_WORDS = {
    "plot",
    "graph",
    "sketch",
    "visualize",
    "visualise",
    "draw",
    "graphically",
    "curve",
}

SUPPORTED_FUNCTION_HINTS = {
    "sin",
    "cos",
    "tan",
    "exp",
    "ln",
    "log",
    "sqrt",
    "piecewise",
}

SUBSCRIPT_MAP = str.maketrans("₀₁₂₃₄₅₆₇₈₉₋₊", "0123456789-+")
SUPERSCRIPT_MAP = {
    "⁰": "^0",
    "¹": "^1",
    "²": "^2",
    "³": "^3",
    "⁴": "^4",
    "⁵": "^5",
    "⁶": "^6",
    "⁷": "^7",
    "⁸": "^8",
    "⁹": "^9",
    "⁻": "^-",
    "⁺": "^+",
}


def _normalize_math_text(text):
    """Normalize common student math notation into parser-friendly text."""
    normalized = str(text or "")
    normalized = normalized.replace("−", "-").replace("π", "pi").replace("Π", "pi")
    normalized = normalized.replace("∞", "oo").replace("∫", " integral ")
    normalized = normalized.replace("ln", "log")

    for source, target in SUPERSCRIPT_MAP.items():
        normalized = normalized.replace(source, target)
    for source in "₀₁₂₃₄₅₆₇₈₉₋₊":
        normalized = normalized.replace(source, f"_{source.translate(SUBSCRIPT_MAP)}")

    normalized = re.sub(r"([A-Za-z0-9)\]])\s*\^\s*([+-]?\w+)", r"\1**\2", normalized)
    normalized = re.sub(r"(?<=\d)(?=x\b)", "*", normalized)
    normalized = re.sub(r"\be\s*\*\*\s*x\b", "exp(x)", normalized)
    normalized = normalized.replace("^", "**")
    return normalized


def _safe_sympify(expression):
    """Parse a math expression using a restricted SymPy namespace."""
    clean = _normalize_math_text(expression)
    clean = re.sub(r"\by\s*=", "", clean, flags=re.IGNORECASE).strip()
    namespace = {
        "x": x,
        "t": t,
        "pi": sp.pi,
        "oo": sp.oo,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "exp": sp.exp,
        "log": sp.log,
        "ln": sp.log,
        "sqrt": sp.sqrt,
        "abs": sp.Abs,
        "Piecewise": sp.Piecewise,
    }
    return sp.sympify(clean, locals=namespace)


def _extract_expression(text):
    """Extract the most likely single-variable expression from a prompt."""
    normalized = _normalize_math_text(text)
    patterns = [
        r"y\s*=\s*([^,\n;]+)",
        r"f\s*\(\s*x\s*\)\s*=\s*([^,\n;]+)",
        r"function\s+([^,\n;]+)",
        r"derivative\s+of\s+([^,\n;]+)",
        r"differentiate\s+([^,\n;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    after_keywords = re.sub(
        r"\b(plot|graph|sketch|visualize|visualise|draw|explain graphically|this|the|of)\b",
        " ",
        normalized,
        flags=re.IGNORECASE,
    ).strip(" .:?")
    if any(token in after_keywords for token in ["x", "sin", "cos", "tan", "exp", "log"]):
        return after_keywords
    return ""


def _parse_bound(value):
    """Parse a bound such as pi, 2*pi, or 0 into a SymPy value."""
    return _safe_sympify(value)


def _extract_integral(text):
    """Extract definite or indefinite integral data from common notation."""
    normalized = _normalize_math_text(text)

    definite_patterns = [
        r"integral\s*_?([+\-]?(?:\d+(?:\.\d+)?|pi|[0-9*./+\- ]*pi))\s*\*\*\s*([+\-]?(?:\d+(?:\.\d+)?|pi|[0-9*./+\- ]*pi))\s*(.+?)\s*d\s*x",
        r"integral\s+from\s+(.+?)\s+to\s+(.+?)\s+(?:of\s+)?(.+?)(?:\s+d\s*x|\s+dx|$)",
        r"integrate\s+(.+?)\s+from\s+(.+?)\s+to\s+(.+?)(?:$|[,.])",
    ]

    for index, pattern in enumerate(definite_patterns):
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        if index == 2:
            expr_text, lower_text, upper_text = match.groups()
        else:
            lower_text, upper_text, expr_text = match.groups()
        return {
            "kind": "definite_integral",
            "expression": _safe_sympify(expr_text),
            "lower": _parse_bound(lower_text),
            "upper": _parse_bound(upper_text),
        }

    indefinite_patterns = [
        r"integral\s+(.+?)\s*d\s*x",
        r"integrate\s+(.+?)(?:\s+with respect to x|$)",
    ]
    for pattern in indefinite_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return {
                "kind": "indefinite_integral",
                "expression": _safe_sympify(match.group(1)),
            }
    return None


def _extract_area_between_curves(text):
    """Extract simple 'area between y=... and y=...' prompts."""
    normalized = _normalize_math_text(text)
    if "area between" not in normalized.lower():
        return None
    matches = re.findall(r"y\s*=\s*([^,\n;]+)", normalized, flags=re.IGNORECASE)
    if len(matches) >= 2:
        return {
            "kind": "area_between_curves",
            "expression": _safe_sympify(matches[0]),
            "expression_2": _safe_sympify(matches[1]),
        }
    match = re.search(r"area between\s+(.+?)\s+and\s+(.+?)(?:$|[,.])", normalized, flags=re.IGNORECASE)
    if match:
        return {
            "kind": "area_between_curves",
            "expression": _safe_sympify(match.group(1)),
            "expression_2": _safe_sympify(match.group(2)),
        }
    return None


def _extract_parametric(text):
    """Extract simple parametric equations x=..., y=... in t."""
    normalized = _normalize_math_text(text)
    if "parametric" not in normalized.lower():
        return None
    x_match = re.search(r"\bx\s*=\s*([^,\n;]+)", normalized, flags=re.IGNORECASE)
    y_match = re.search(r"\by\s*=\s*([^,\n;]+)", normalized, flags=re.IGNORECASE)
    if x_match and y_match:
        return {
            "kind": "parametric",
            "x_expression": _safe_sympify(x_match.group(1)),
            "y_expression": _safe_sympify(y_match.group(1)),
        }
    return None


def _safe_lambdify(expression, symbol=x):
    """Create a NumPy function from a SymPy expression."""
    return sp.lambdify(symbol, expression, modules=["numpy"])


def _domain_for_expression(expression, lower=None, upper=None):
    """Choose a sensible x-domain for plotting."""
    if lower is not None and upper is not None:
        low = float(sp.N(lower))
        high = float(sp.N(upper))
        padding = max((high - low) * 0.25, 1.0)
        return low - padding, high + padding

    if expression.has(sp.log):
        return 0.05, 8.0
    if expression.has(sp.tan):
        return -float(sp.pi), float(sp.pi)
    if expression.has(sp.sin) or expression.has(sp.cos):
        return -2 * float(sp.pi), 2 * float(sp.pi)
    if expression.has(sp.exp):
        return -3.0, 3.0
    return -5.0, 5.0


def _sample_expression(expression, lower=None, upper=None, points=1400):
    """Sample a function while removing undefined, complex, and huge values."""
    x_min, x_max = _domain_for_expression(expression, lower, upper)
    x_values = np.linspace(x_min, x_max, points)
    f = _safe_lambdify(expression)
    with np.errstate(all="ignore"):
        y_values = np.asarray(f(x_values), dtype=np.complex128)
    y_values = np.real_if_close(y_values, tol=1000)
    y_values = np.asarray(y_values, dtype=float)
    y_values[~np.isfinite(y_values)] = np.nan
    y_values[np.abs(y_values) > 1e6] = np.nan
    return x_values, y_values


def _add_axis_layout(fig, title, x_title="x", y_title="y"):
    """Apply educational Plotly layout defaults."""
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=40, r=24, t=70, b=40),
    )
    fig.update_xaxes(showgrid=True, zeroline=True, zerolinewidth=1, zerolinecolor="#334155")
    fig.update_yaxes(showgrid=True, zeroline=True, zerolinewidth=1, zerolinecolor="#334155")
    return fig


def _figure_to_json(fig):
    """Serialize Plotly figure for SQLite chat metadata."""
    return fig.to_json()


def _critical_points(expression):
    """Return real critical points that can be shown on the graph."""
    derivative = sp.diff(expression, x)
    points = []
    try:
        solutions = sp.solve(sp.Eq(derivative, 0), x)
    except Exception:
        solutions = []
    for solution in solutions[:8]:
        if solution.is_real is False:
            continue
        try:
            sx = float(sp.N(solution))
            sy = float(sp.N(expression.subs(x, solution)))
            if np.isfinite(sx) and np.isfinite(sy):
                points.append((sx, sy, sp.sstr(solution)))
        except Exception:
            continue
    return points


def _intersections(expr_a, expr_b):
    """Return real intersections for two functions."""
    points = []
    try:
        solutions = sp.solve(sp.Eq(expr_a, expr_b), x)
    except Exception:
        solutions = []
    for solution in solutions[:10]:
        if solution.is_real is False:
            continue
        try:
            sx = float(sp.N(solution))
            sy = float(sp.N(expr_a.subs(x, solution)))
            if np.isfinite(sx) and np.isfinite(sy):
                points.append((sx, sy, sp.sstr(solution)))
        except Exception:
            continue
    return points


def _plot_function(expression, title=None, extra_traces=None, lower=None, upper=None):
    """Build a base function plot."""
    x_values, y_values = _sample_expression(expression, lower=lower, upper=upper)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines",
            name=f"y = {sp.sstr(expression)}",
            line=dict(color="#2563eb", width=3),
        )
    )

    for px, py, label in _critical_points(expression):
        fig.add_trace(
            go.Scatter(
                x=[px],
                y=[py],
                mode="markers+text",
                text=[f"critical x={label}"],
                textposition="top center",
                name="Critical point",
                marker=dict(size=9, color="#ef4444"),
            )
        )

    for trace in extra_traces or []:
        fig.add_trace(trace)
    return _add_axis_layout(fig, title or f"Graph of y = {sp.sstr(expression)}")


def _visual_sections(summary, exact="", numeric="", visual="", exam_tip="", mistake="", quick=""):
    """Create the educational explanation block below a graph."""
    lines = [
        "## Mathematical Visualization",
        summary,
    ]
    if exact:
        lines.extend(["", "### Exact Result", exact])
    if numeric:
        lines.extend(["", "### Numerical Approximation", numeric])
    lines.extend(
        [
            "",
            "### Visual Interpretation",
            visual or "The graph shows how the function changes across the selected x-values.",
            "",
            "### Mathematical Meaning",
            "The plotted curve connects the symbolic formula to its numerical behavior.",
            "",
            "### Exam Tip",
            exam_tip or "Always label axes, important points, and the interval used for a graph-based answer.",
            "",
            "### Common Mistake",
            mistake or "Do not ignore domain restrictions, asymptotes, or the interval of integration.",
            "",
            "### Quick Summary",
            quick or "Use the graph to understand shape, sign, area, and key points before doing final algebra.",
        ]
    )
    return "\n".join(lines)


def _definite_integral_visual(data):
    """Visualize and solve a definite integral."""
    expression = data["expression"]
    lower = data["lower"]
    upper = data["upper"]
    antiderivative = sp.integrate(expression, x)
    exact_value = sp.integrate(expression, (x, lower, upper))
    numeric_value = float(sp.N(exact_value))
    lower_float = float(sp.N(lower))
    upper_float = float(sp.N(upper))

    shade_x = np.linspace(lower_float, upper_float, 600)
    f = _safe_lambdify(expression)
    with np.errstate(all="ignore"):
        shade_y = np.asarray(f(shade_x), dtype=float)
    shade_y[~np.isfinite(shade_y)] = np.nan

    shade_trace = go.Scatter(
        x=np.concatenate([shade_x, shade_x[::-1]]),
        y=np.concatenate([shade_y, np.zeros_like(shade_y)[::-1]]),
        fill="toself",
        fillcolor="rgba(20, 184, 180, 0.28)",
        line=dict(color="rgba(20, 184, 180, 0.2)"),
        name=f"Area from {sp.sstr(lower)} to {sp.sstr(upper)}",
    )
    bound_traces = [
        go.Scatter(
            x=[lower_float, lower_float],
            y=[0, float(sp.N(expression.subs(x, lower)))],
            mode="lines+text",
            text=[None, f"a={sp.sstr(lower)}"],
            textposition="top center",
            line=dict(color="#f97316", dash="dash"),
            name="Lower bound",
        ),
        go.Scatter(
            x=[upper_float, upper_float],
            y=[0, float(sp.N(expression.subs(x, upper)))],
            mode="lines+text",
            text=[None, f"b={sp.sstr(upper)}"],
            textposition="top center",
            line=dict(color="#ef4444", dash="dash"),
            name="Upper bound",
        ),
    ]
    fig = _plot_function(
        expression,
        title=f"Definite Integral: ∫ from {sp.sstr(lower)} to {sp.sstr(upper)} {sp.sstr(expression)} dx",
        extra_traces=[shade_trace] + bound_traces,
        lower=lower,
        upper=upper,
    )
    explanation = _visual_sections(
        summary=(
            f"Step 1: Plot `y = {sp.sstr(expression)}`.\n\n"
            f"Step 2: Shade the region from `x = {sp.sstr(lower)}` to `x = {sp.sstr(upper)}`.\n\n"
            f"Step 3: Integral notation: `∫_{{{sp.sstr(lower)}}}^{{{sp.sstr(upper)}}} {sp.sstr(expression)} dx`.\n\n"
            f"Step 4: Antiderivative: `{sp.sstr(antiderivative)}`.\n\n"
            f"Step 5: Evaluate `F({sp.sstr(upper)}) - F({sp.sstr(lower)})`."
        ),
        exact=f"`{sp.sstr(exact_value)}`",
        numeric=f"`{numeric_value:.8g}`",
        visual="The shaded region represents the signed area accumulated by the function across the interval.",
        exam_tip="For definite integrals, write the antiderivative first, then substitute upper minus lower.",
        mistake="Do not forget that area below the x-axis counts as negative in a signed definite integral.",
        quick=f"The definite integral equals `{sp.sstr(exact_value)}` ≈ `{numeric_value:.8g}`.",
    )
    return _payload("definite_integral", fig, explanation, expression, exact_value, numeric_value)


def _indefinite_integral_visual(data):
    """Visualize and solve an indefinite integral."""
    expression = data["expression"]
    antiderivative = sp.integrate(expression, x)
    fig = _plot_function(expression, title=f"Function for ∫ {sp.sstr(expression)} dx")
    explanation = _visual_sections(
        summary=(
            f"Step 1: Plot `y = {sp.sstr(expression)}` to understand the function being integrated.\n\n"
            f"Step 2: Find an antiderivative.\n\n"
            f"Step 3: `∫ {sp.sstr(expression)} dx = {sp.sstr(antiderivative)} + C`."
        ),
        exact=f"`{sp.sstr(antiderivative)} + C`",
        visual="The curve shows the rate being accumulated. The antiderivative is the family of functions whose derivative gives this curve.",
        exam_tip="Always add `+ C` for an indefinite integral.",
        mistake="Do not give a single number for an indefinite integral.",
        quick=f"The antiderivative is `{sp.sstr(antiderivative)} + C`.",
    )
    return _payload("indefinite_integral", fig, explanation, expression, antiderivative, None)


def _derivative_visual(expression):
    """Visualize a function and its derivative."""
    derivative = sp.diff(expression, x)
    x_values, y_values = _sample_expression(expression)
    _, dy_values = _sample_expression(derivative)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_values, y=y_values, mode="lines", name=f"f(x) = {sp.sstr(expression)}", line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=x_values, y=dy_values, mode="lines", name=f"f'(x) = {sp.sstr(derivative)}", line=dict(color="#f97316", width=3)))
    for px, py, label in _critical_points(expression):
        fig.add_trace(go.Scatter(x=[px], y=[py], mode="markers+text", text=[f"f'(x)=0 at x={label}"], textposition="top center", name="Critical point", marker=dict(size=9, color="#ef4444")))
    fig = _add_axis_layout(fig, f"Derivative Visualization: f(x) and f'(x)")
    explanation = _visual_sections(
        summary=(
            f"Step 1: Start with `f(x) = {sp.sstr(expression)}`.\n\n"
            f"Step 2: Differentiate term by term.\n\n"
            f"Step 3: `f'(x) = {sp.sstr(derivative)}`.\n\n"
            "Step 4: Compare the original curve with the derivative curve."
        ),
        exact=f"`f'(x) = {sp.sstr(derivative)}`",
        visual="The derivative graph shows slope. Positive derivative means the function is increasing; negative derivative means decreasing.",
        exam_tip="Critical points occur where `f'(x)=0` or where the derivative is undefined.",
        mistake="Do not confuse function height `f(x)` with slope `f'(x)`.",
        quick=f"The derivative is `{sp.sstr(derivative)}`.",
    )
    return _payload("derivative", fig, explanation, expression, derivative, None)


def _area_between_curves_visual(data):
    """Visualize and compute simple area between two curves."""
    expr_a = data["expression"]
    expr_b = data["expression_2"]
    points = _intersections(expr_a, expr_b)
    if len(points) >= 2:
        lower = points[0][0]
        upper = points[-1][0]
    else:
        lower, upper = -2.0, 2.0
    x_values = np.linspace(lower, upper, 800)
    f_a = _safe_lambdify(expr_a)
    f_b = _safe_lambdify(expr_b)
    y_a = np.asarray(f_a(x_values), dtype=float)
    y_b = np.asarray(f_b(x_values), dtype=float)
    exact = sp.integrate(sp.Abs(expr_a - expr_b), (x, lower, upper))
    numeric = float(np.trapz(np.abs(y_a - y_b), x_values))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_values, y=y_a, mode="lines", name=f"y = {sp.sstr(expr_a)}", line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=x_values, y=y_b, mode="lines", name=f"y = {sp.sstr(expr_b)}", line=dict(color="#f97316", width=3)))
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([x_values, x_values[::-1]]),
            y=np.concatenate([y_a, y_b[::-1]]),
            fill="toself",
            fillcolor="rgba(139, 92, 246, 0.22)",
            line=dict(color="rgba(139, 92, 246, 0.1)"),
            name="Area between curves",
        )
    )
    for px, py, label in points:
        fig.add_trace(go.Scatter(x=[px], y=[py], mode="markers+text", text=[f"x={label}"], textposition="top center", name="Intersection", marker=dict(size=9, color="#ef4444")))
    fig = _add_axis_layout(fig, f"Area Between y={sp.sstr(expr_a)} and y={sp.sstr(expr_b)}")
    explanation = _visual_sections(
        summary=(
            f"Step 1: Plot both curves: `y={sp.sstr(expr_a)}` and `y={sp.sstr(expr_b)}`.\n\n"
            "Step 2: Find their intersection points.\n\n"
            "Step 3: Integrate the vertical distance between the upper and lower curve."
        ),
        exact=f"`∫ |({sp.sstr(expr_a)}) - ({sp.sstr(expr_b)})| dx` over the shown interval.",
        numeric=f"`{numeric:.8g}`",
        visual="The shaded band is the area trapped between the two curves.",
        exam_tip="For area between curves, use upper curve minus lower curve on each interval.",
        mistake="Do not integrate without checking which curve is on top.",
        quick=f"Approximate area over the shown interval is `{numeric:.8g}`.",
    )
    return _payload("area_between_curves", fig, explanation, expr_a, exact, numeric)


def _parametric_visual(data):
    """Visualize a parametric curve."""
    expr_x = data["x_expression"]
    expr_y = data["y_expression"]
    t_values = np.linspace(-2 * np.pi, 2 * np.pi, 1200)
    fx = _safe_lambdify(expr_x, symbol=t)
    fy = _safe_lambdify(expr_y, symbol=t)
    px = np.asarray(fx(t_values), dtype=float)
    py = np.asarray(fy(t_values), dtype=float)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=px, y=py, mode="lines", name=f"x={sp.sstr(expr_x)}, y={sp.sstr(expr_y)}", line=dict(color="#2563eb", width=3)))
    fig = _add_axis_layout(fig, "Parametric Curve", "x(t)", "y(t)")
    explanation = _visual_sections(
        summary=f"The graph plots the moving point `(x(t), y(t)) = ({sp.sstr(expr_x)}, {sp.sstr(expr_y)})` as `t` changes.",
        visual="A parametric graph is traced by a moving point instead of a direct y=f(x) rule.",
        exam_tip="For parametric equations, label the parameter interval if the question gives one.",
        mistake="Do not treat `t` as the vertical axis; it is the parameter controlling both x and y.",
        quick="The curve shows the path of the parametric point.",
    )
    return _payload("parametric", fig, explanation, expr_y, None, None)


def _function_visual(expression):
    """Visualize a single function and key behavior."""
    derivative = sp.diff(expression, x)
    second_derivative = sp.diff(expression, x, 2)
    fig = _plot_function(expression)
    explanation = _visual_sections(
        summary=(
            f"Step 1: Plot `y = {sp.sstr(expression)}`.\n\n"
            f"Step 2: Use the derivative `y' = {sp.sstr(derivative)}` to understand increasing/decreasing behavior.\n\n"
            f"Step 3: Use the second derivative `y'' = {sp.sstr(second_derivative)}` to understand concavity and possible inflection points."
        ),
        exact=f"`y = {sp.sstr(expression)}`",
        visual="The graph shows the function shape, intercept behavior, turning points, and domain restrictions.",
        exam_tip="For a sketch, find intercepts, asymptotes, critical points, and end behavior.",
        mistake="Do not draw through undefined points or vertical asymptotes.",
        quick=f"The plotted function is `{sp.sstr(expression)}`.",
    )
    return _payload("function", fig, explanation, expression, expression, None)


def _payload(kind, fig, explanation, expression, exact_result=None, numeric_result=None):
    """Package a math visualization for chat rendering and persistence."""
    return {
        "kind": kind,
        "expression": sp.sstr(expression) if expression is not None else "",
        "exact_result": sp.sstr(exact_result) if exact_result is not None else "",
        "numeric_result": float(numeric_result) if numeric_result is not None and np.isfinite(numeric_result) else None,
        "figure_json": _figure_to_json(fig),
        "explanation": explanation,
    }


def should_visualize_math(prompt):
    """Detect whether the user is asking for a math graph/visual solution."""
    text = str(prompt or "").lower()
    normalized = _normalize_math_text(text)
    has_intent = any(word in normalized for word in VISUAL_INTENT_WORDS)
    has_calculus = any(word in normalized for word in ["integral", "integrate", "derivative", "differentiate", "area under", "area between", "volume of revolution", "riemann", "tangent"])
    has_function = bool(re.search(r"\by\s*=|f\s*\(\s*x\s*\)\s*=", normalized)) or any(hint in normalized for hint in SUPPORTED_FUNCTION_HINTS)
    return has_intent or has_calculus or has_function


def generate_math_visualization(prompt):
    """Return a math visualization payload for supported graph/calculus prompts."""
    if not should_visualize_math(prompt):
        return None

    if not all([np, go, sp]):
        return {
            "kind": "math_error",
            "expression": "",
            "exact_result": "",
            "numeric_result": None,
            "figure_json": "",
            "explanation": (
                "## Mathematical Visualization\n"
                "The math visualization engine needs Plotly, SymPy, and NumPy installed.\n\n"
                "### How to fix it\n"
                "Run `pip install -r requirements.txt`, then restart Streamlit.\n\n"
                "### Quick Summary\n"
                "The app did not crash, but graph rendering is unavailable until the math packages are installed."
            ),
        }

    try:
        area_data = _extract_area_between_curves(prompt)
        if area_data:
            return _area_between_curves_visual(area_data)

        integral_data = _extract_integral(prompt)
        if integral_data:
            if integral_data["kind"] == "definite_integral":
                return _definite_integral_visual(integral_data)
            return _indefinite_integral_visual(integral_data)

        parametric_data = _extract_parametric(prompt)
        if parametric_data:
            return _parametric_visual(parametric_data)

        expression_text = _extract_expression(prompt)
        if not expression_text:
            return None
        expression = _safe_sympify(expression_text)

        normalized = _normalize_math_text(prompt).lower()
        if "derivative" in normalized or "differentiate" in normalized or "tangent" in normalized:
            return _derivative_visual(expression)

        return _function_visual(expression)
    except Exception as exc:
        return {
            "kind": "math_error",
            "expression": "",
            "exact_result": "",
            "numeric_result": None,
            "figure_json": "",
            "explanation": (
                "## Mathematical Visualization\n"
                "I could not safely parse this function for plotting.\n\n"
                "### How to fix it\n"
                "Write the function in a clear form, for example `y = x^2`, `∫_0^2 x^2 dx`, "
                "or `area between y=x^2 and y=x`.\n\n"
                "### Common Mistake\n"
                "Avoid ambiguous notation or missing bounds when asking for a graph."
            ),
            "error": str(exc)[:160],
        }
