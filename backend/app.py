from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import random
import string

app = Flask(__name__)
CORS(app)

META = {
    ".": (
        "Wildcard — matches any single character except a newline. "
        "For example, 'a.c' would match 'abc', 'a1c', 'a-c', and so on. "
        "Use '\\.' if you want to match a literal dot."
    ),
    "^": (
        "Start anchor — asserts that the match must begin at the very start "
        "of the string. No characters are allowed before this pattern. "
        "Example: '^hello' only matches strings that start with 'hello'."
    ),
    "$": (
        "End anchor — asserts that the match must finish at the very end "
        "of the string. No characters are allowed after this pattern. "
        "Example: 'world$' only matches strings that end with 'world'."
    ),
    "|": (
        "Alternation (OR operator) — evaluates the sub-expression on the left "
        "first; if that fails, it tries the sub-expression on the right. "
        "Acts like a logical OR. Example: 'cat|dog' matches either 'cat' or 'dog'."
    ),
}

ESCAPES = {
    r"\d": (
        "Digit shorthand class — matches any single decimal digit from 0 to 9. "
        "Equivalent to writing the character class [0-9]. "
        "Example: '\\d\\d' matches '42' but not 'ab'."
    ),
    r"\w": (
        "Word-character shorthand class — matches any single letter (a–z, A–Z), "
        "digit (0–9), or underscore (_). "
        "Equivalent to [a-zA-Z0-9_]. "
        "Example: '\\w+' matches 'hello_world' but not 'hi there'."
    ),
    r"\s": (
        "Whitespace shorthand class — matches any single whitespace character: "
        "space ( ), tab (\\t), newline (\\n), carriage return (\\r), or form feed (\\f). "
        "Example: 'hello\\sworld' matches 'hello world' with a space between them."
    ),
    r"\D": (
        "Non-digit shorthand class — matches any single character that is NOT "
        "a decimal digit. Equivalent to [^0-9]. "
        "Example: '\\D+' matches 'abc' but not '123'."
    ),
    r"\W": (
        "Non-word-character shorthand class — matches any character that is NOT "
        "a letter, digit, or underscore. Equivalent to [^a-zA-Z0-9_]. "
        "Example: '\\W' matches '@', '!', or ' '."
    ),
    r"\S": (
        "Non-whitespace shorthand class — matches any single character that is "
        "NOT a whitespace character. "
        "Example: '\\S+' matches any sequence of non-space characters like 'hello'."
    ),
    r"\b": (
        "Word-boundary assertion — matches the invisible boundary between a "
        "word character (\\w) and a non-word character (\\W). "
        "Does not consume any characters itself. "
        "Example: '\\bcat\\b' matches 'cat' in 'the cat sat' but not in 'concatenate'."
    ),
    r"\B": (
        "Non-word-boundary assertion — matches any position that is NOT a "
        "word boundary. Useful when you need a pattern to appear inside a word. "
        "Example: '\\Bcat\\B' matches 'cat' inside 'concatenate' but not as a standalone word."
    ),
    r"\n": "Literal newline character — matches an actual line-break in the input.",
    r"\t": "Literal tab character — matches an actual tab character (\\t) in the input.",
    r"\r": "Literal carriage-return character — matches a carriage-return (\\r) in the input.",
}

QUANTIFIERS = {
    "*": (
        "Greedy zero-or-more quantifier — repeats the preceding element as many "
        "times as possible (greedy), but the match still succeeds even if the "
        "element appears zero times. "
        "Example: 'ab*' matches 'a', 'ab', 'abb', 'abbb', etc."
    ),
    "+": (
        "Greedy one-or-more quantifier — repeats the preceding element as many "
        "times as possible, but requires it to appear at least once. "
        "The match fails if the element does not appear at all. "
        "Example: 'ab+' matches 'ab', 'abb', 'abbb' but NOT 'a' alone."
    ),
    "?": (
        "Optional (zero-or-one) quantifier — makes the preceding element optional. "
        "It matches once if present, or skips it if absent. "
        "When placed after *, +, or ?, it switches those quantifiers to lazy mode. "
        "Example: 'colou?r' matches both 'color' and 'colour'."
    ),
}

def explain_regex(regex):
    steps = []
    # english_parts holds (phrase, quantifier_hint) tuples 
    english_parts = []
    group_stack   = []
    group_num     = 0
    i = 0

    while i < len(regex):
        c = regex[i]

        # Escape Sequences
        if c == "\\":
            token = regex[i:i+2]
            if token in ESCAPES:
                steps.append(f"{token} → {ESCAPES[token]}")
                english_parts.append(("matches any digit (0–9)" if token == r"\d"
                    else "matches any word character" if token == r"\w"
                    else "matches any whitespace character" if token == r"\s"
                    else "matches any non-digit" if token == r"\D"
                    else "matches any non-word character" if token == r"\W"
                    else "matches any non-whitespace character" if token == r"\S"
                    else "matches a word boundary" if token == r"\b"
                    else "matches a non-word boundary" if token == r"\B"
                    else "matches a newline" if token == r"\n"
                    else "matches a tab" if token == r"\t"
                    else f"matches '{token[1]}'", None))
                i += 2
                continue
            else:
                escaped_char = token[1] if len(token) > 1 else ""
                steps.append(
                    f"{token} → Escaped literal — the backslash removes any special "
                    f"meaning from '{escaped_char}', so this matches the character "
                    f"'{escaped_char}' exactly as written."
                )
                english_parts.append((f"the literal character '{escaped_char}'", None))
                i += 2
                continue

        # Character classes [abc], [a-z], [^abc] 
        if c == "[":
            end = regex.find("]", i)
            if end != -1:
                charclass = regex[i:end+1]
                inner = charclass[1:-1]
                negated = inner.startswith("^")
                clean = inner[1:] if negated else inner

                parts = []
                j = 0
                while j < len(clean):
                    if j + 2 < len(clean) and clean[j + 1] == "-":
                        parts.append(f"'{clean[j]}' through '{clean[j+2]}'")
                        j += 3
                    else:
                        parts.append(f"'{clean[j]}'")
                        j += 1
                part_str = ", ".join(parts) if parts else "(empty)"

                if negated:
                    desc = (
                        f"Negated character class — matches exactly one character "
                        f"that is NOT any of: {part_str}. "
                        f"Every character outside this set is accepted, but only "
                        f"one character is consumed per match."
                    )
                    eng = f"any character except {part_str}"
                else:
                    desc = (
                        f"Character class — matches exactly one character chosen "
                        f"from the set: {part_str}. "
                        f"Only one character is consumed, but any member of the set qualifies."
                    )
                    eng = f"any character from {part_str}"

                steps.append(f"{charclass} → {desc}")
                english_parts.append((eng, None))
                i = end + 1
                continue

        # Standard quantifiers *, +, ? 
        if c in QUANTIFIERS:
            prev_token = steps[-1].split(" → ")[0] if steps else "the preceding element"
            steps.append(
                f"{c} → {QUANTIFIERS[c]} "
                f"(Applies to: {prev_token})"
            )
            
            if english_parts:
                base, _ = english_parts[-1]
                if c == "*":
                    english_parts[-1] = (base, "zero or more times")
                elif c == "+":
                    english_parts[-1] = (base, "one or more times")
                elif c == "?":
                    english_parts[-1] = (base, "optionally")
            i += 1
            continue

        # Range / exact quantifier {m,n}
        if c == "{":
            end = regex.find("}", i)
            if end != -1:
                q = regex[i:end+1]
                inner = q[1:-1]
                prev_token = steps[-1].split(" → ")[0] if steps else "the preceding element"

                if "," in inner:
                    lo, hi = inner.split(",", 1)
                    lo = lo.strip()
                    hi = hi.strip()
                    if hi == "":
                        desc = (
                            f"Range quantifier — requires the preceding element to "
                            f"appear at least {lo} times, with no upper limit (unbounded). "
                            f"(Applies to: {prev_token})"
                        )
                        quant_eng = f"at least {lo} times"
                    else:
                        desc = (
                            f"Range quantifier — the preceding element must appear "
                            f"at least {lo} time(s) and at most {hi} time(s). "
                            f"Matches fail outside this range. "
                            f"(Applies to: {prev_token})"
                        )
                        quant_eng = f"between {lo} and {hi} times"
                else:
                    desc = (
                        f"Exact repetition quantifier — the preceding element must "
                        f"appear exactly {inner} time(s), no more and no less. "
                        f"(Applies to: {prev_token})"
                    )
                    quant_eng = f"exactly {inner} time(s)"

                steps.append(f"{q} → {desc}")
                if english_parts:
                    base, _ = english_parts[-1]
                    english_parts[-1] = (base, quant_eng)
                i = end + 1
                continue

        # Meta characters . ^ $ | 
        if c in META:
            steps.append(f"{c} → {META[c]}")
            if c == "^":
                english_parts.append(("starting at the beginning of the string", None))
            elif c == "$":
                english_parts.append(("ending at the end of the string", None))
            elif c == ".":
                english_parts.append(("any single character", None))
            elif c == "|":
                english_parts.append(("OR", None))
            i += 1
            continue

        # Opening parenthesis / groups 
        if c == "(":
            group_num += 1
            group_stack.append(group_num)
            lookahead = regex[i+1:i+3]

            if lookahead == "?:":
                steps.append(
                    f"(?: → Non-capturing group #{group_num} — groups the enclosed "
                    f"tokens into a single unit so quantifiers and alternation apply "
                    f"to all of them together, but the matched text is NOT stored "
                    f"for back-references or extraction."
                )
                english_parts.append((f"[start of group]", None))
                i += 3

            elif lookahead == "?=":
                steps.append(
                    f"(?= → Positive lookahead #{group_num} — checks that the "
                    f"following pattern exists at this position in the string, but "
                    f"does not move the cursor forward (zero-width assertion). "
                    f"The lookahead must succeed for the overall match to continue."
                )
                english_parts.append(("[lookahead: must be followed by]", None))
                i += 3

            elif lookahead == "?!":
                steps.append(
                    f"(?! → Negative lookahead #{group_num} — asserts that the "
                    f"following pattern does NOT exist at this position. "
                    f"Zero-width; no characters are consumed."
                )
                english_parts.append(("[lookahead: must NOT be followed by]", None))
                i += 3

            elif lookahead == "?<":
                steps.append(
                    f"(?<= or (?<! → Lookbehind assertion #{group_num} — checks "
                    f"the text immediately before the current position. "
                    f"Zero-width; no characters are consumed."
                )
                english_parts.append(("[lookbehind assertion]", None))
                i += 3

            else:
                steps.append(
                    f"( → Opens capturing group #{group_num}. "
                    f"The text matched by everything inside this group is captured "
                    f"and stored. It can be retrieved as group {group_num} after "
                    f"the match, and quantifiers placed after the closing ')' "
                    f"will apply to the entire group as a single unit."
                )
                english_parts.append((f"[start of group {group_num}]", None))
                i += 1
            continue

        # Closing parenthesis
        if c == ")":
            gn = group_stack.pop() if group_stack else "?"
            steps.append(
                f") → Closes group #{gn}. "
                f"Everything between the matching '(' and this ')' is now one unit. "
                f"Any quantifier written immediately after this ')' (such as *, +, ?) "
                f"will repeat the entire group, not just the last character."
            )
            english_parts.append((f"[end of group {gn}]", None))
            i += 1
            continue

        # Literal character 
        steps.append(
            f"'{c}' → Literal character — matches the exact character '{c}' "
            f"at this position in the input. The match is case-sensitive, so "
            f"'{c}' will not match '{c.swapcase()}' unless case-insensitive flags are used."
        )
        english_parts.append((f"the letter '{c}'", None))
        i += 1

    sentence_tokens = []
    group_buffers   = {}   
    active_groups   = []  

    for phrase, quant in english_parts:
        if phrase.startswith("[start of group"):
            try:
                gn = int(phrase.split("group")[1].strip().rstrip("]"))
            except Exception:
                gn = 0
            active_groups.append(gn)
            group_buffers[gn] = []
            continue

        if phrase.startswith("[end of group"):
            if active_groups:
                gn = active_groups.pop()
                buf = group_buffers.pop(gn, [])
                merged = ", ".join(buf) if buf else "..."
                full = f"({merged})"
                if quant:
                    full = f"{full} repeated {quant}"
                if active_groups:
                    group_buffers[active_groups[-1]].append(full)
                else:
                    sentence_tokens.append(full)
            continue

        # Build the phrase with its quantifier
        if quant == "optionally":
            full = f"optionally {phrase}"
        elif quant:
            full = f"{phrase} ({quant})"
        else:
            full = phrase

        if active_groups:
            group_buffers[active_groups[-1]].append(full)
        else:
            sentence_tokens.append(full)

    # Join with commas, swapping " OR " around the | token
    parts_out = []
    for tok in sentence_tokens:
        if tok == "OR":
            # Replace the trailing comma+space before OR
            if parts_out and parts_out[-1].endswith(", "):
                parts_out[-1] = parts_out[-1][:-2]
            parts_out.append(" or ")
        else:
            parts_out.append(tok + ", ")

    # Strip trailing comma and capitalise
    raw = "".join(parts_out).strip().rstrip(",").strip()
    if raw:
        explanation = "This pattern matches: " + raw[0].lower() + raw[1:] + "."
    else:
        explanation = "No explanation could be generated."

    return explanation, steps

# Structural String Generation

def _get_sre():
    """Return (sre_parse, sre_constants) without deprecation warnings."""
    try:
        import re._parser as sp
        import re._constants as sc
        return sp, sc
    except ImportError:
        import sre_parse as sp
        import sre_constants as sc
        return sp, sc


def test_strings(pattern, n=5):
    sre_parse, sre_constants = _get_sre()

    try:
        parsed = sre_parse.parse(pattern)
    except Exception:
        return [], []

    regex_chars = set(string.ascii_lowercase[:8])

    def collect_chars(seq):
        for op, av in seq:
            if op == sre_constants.LITERAL:
                regex_chars.add(chr(av))
            elif op == sre_constants.IN:
                for iop, iav in av:
                    if iop == sre_constants.LITERAL:
                        regex_chars.add(chr(iav))
                    elif iop == sre_constants.RANGE:
                        for c in range(iav[0], iav[1] + 1):
                            regex_chars.add(chr(c))
            elif op in (sre_constants.MAX_REPEAT, sre_constants.MIN_REPEAT):
                collect_chars(av[2])
            elif op == sre_constants.SUBPATTERN:
                collect_chars(av[3])
            elif op == sre_constants.BRANCH:
                for br in av[1]:
                    collect_chars(br)

    collect_chars(parsed)
    all_chars = list(regex_chars)

    def gen_node(node):
        op, av = node

        if op == sre_constants.LITERAL:
            return chr(av)

        elif op == sre_constants.AT:
            return ""  # ^ or $ anchors - consume nothing

        elif op == sre_constants.ANY:
            return random.choice(string.ascii_lowercase + string.digits)

        elif op == sre_constants.IN:
            chars = []
            negated = False
            for iop, iav in av:
                if iop == sre_constants.NEGATE:
                    negated = True
                elif iop == sre_constants.LITERAL:
                    chars.append(chr(iav))
                elif iop == sre_constants.RANGE:
                    chars.extend(chr(c) for c in range(iav[0], iav[1] + 1))
                elif iop == sre_constants.CATEGORY:
                    if iav == sre_constants.CATEGORY_DIGIT:
                        chars.extend(list(string.digits))
                    elif iav == sre_constants.CATEGORY_WORD:
                        chars.extend(list(string.ascii_letters + string.digits + '_'))
                    elif iav == sre_constants.CATEGORY_SPACE:
                        chars.extend([' ', '\t'])
            if negated:
                excl = set(chars)
                chars = [c for c in string.printable if c not in excl and c != '\n']
            return random.choice(chars) if chars else 'x'

        elif op == sre_constants.BRANCH:
            return gen_sequence(random.choice(av[1]))

        elif op == sre_constants.SUBPATTERN:
            return gen_sequence(av[3])

        elif op in (sre_constants.MAX_REPEAT, sre_constants.MIN_REPEAT):
            lo, hi = av[0], av[1]
            if hi == sre_constants.MAXREPEAT:
                hi = lo + random.randint(1, 6)
            cnt = random.randint(lo, min(hi, lo + 6))
            return ''.join(gen_sequence(av[2]) for _ in range(cnt))

        elif op == sre_constants.NOT_LITERAL:
            chars = [c for c in string.ascii_letters + string.digits if ord(c) != av]
            return random.choice(chars) if chars else 'x'

        elif op == sre_constants.CATEGORY:
            if av == sre_constants.CATEGORY_DIGIT:
                return random.choice(string.digits)
            elif av == sre_constants.CATEGORY_WORD:
                return random.choice(string.ascii_lowercase + string.digits)
            elif av == sre_constants.CATEGORY_SPACE:
                return ' '

        elif op in (sre_constants.ASSERT, sre_constants.ASSERT_NOT):
            return ""  # lookahead/lookbehind — zero-width

        return ''

    def gen_sequence(seq):
        return ''.join(gen_node(node) for node in seq)

    #Generate a rejected string by corrupting a valid one 
    def gen_rejected():
        if random.random() < 0.6:
            try:
                s = gen_sequence(parsed)
                if len(s) > 1:
                    idx = random.randint(0, len(s) - 1)
                    action = random.randint(0, 2)
                    if action == 0:
                        s = s[:idx] + s[idx + 1:]           # delete a character
                    elif action == 1:
                        s = s[:idx] + '!' + s[idx + 1:]     # replace with invalid char
                    else:
                        s = s[:idx] + '!' + s[idx:]         # insert invalid char
                return s
            except Exception:
                pass
        length = random.randint(1, 12)
        return ''.join(random.choice(all_chars) for _ in range(length))

    # Run both generators
    accepted, rejected = [], []

    for _ in range(3000):
        try:
            s = gen_sequence(parsed)
            if re.fullmatch(pattern, s) and s not in accepted:
                accepted.append(s)
        except Exception:
            pass

        try:
            s = gen_rejected()
            if s and not re.fullmatch(pattern, s) and s not in rejected:
                rejected.append(s)
        except Exception:
            pass

        if len(accepted) >= n and len(rejected) >= n:
            break

    return accepted[:n], rejected[:n]

#API

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    regex = data.get("regex", "")

    try:
        explanation, steps = explain_regex(regex)
        accepted, rejected = test_strings(regex)

        return jsonify({
            "regex": regex,
            "english": explanation,
            "steps": steps,
            "accepted": accepted,
            "rejected": rejected,
            "valid": True
        })

    except re.error as e:
        return jsonify({
            "valid": False,
            "error": str(e)
        })

if __name__ == "__main__":
    app.run(debug=True)
