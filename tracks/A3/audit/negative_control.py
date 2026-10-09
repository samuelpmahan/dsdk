"""Negative control for check_proofs.py: replace `probability` by a version that answers KNOWN 1 for impossible evidence (the
'vacuous truth' bug Proof 2 warns about) and make `condition` drop zero-weight worlds. The checker must report counterexamples.
Run: .venv/bin/python tracks/A3/audit/negative_control.py   (exit 0 = the control behaved)"""
import subprocess, sys, textwrap
code = textwrap.dedent('''
    import runpy, sys
    from fractions import Fraction
    import dsdk.prob as pr, dsdk.prob.worlds as w
    from dsdk.core import Judgment, Status
    real = w.probability
    def buggy(b, q, given=None):
        j = real(b, q, given)
        return Judgment(Status.KNOWN, Fraction(1), "") if j.status is Status.INVALID else j
    pr.probability = buggy
    real_condition = w.condition
    def dropping(b, e):
        c = real_condition(b, e)
        return w.Belief(c.variables, tuple(x for x in c.worlds if x.weight > 0))
    pr.condition = dropping
    sys.argv = ["check_proofs.py"]
    runpy.run_path("tracks/A3/audit/check_proofs.py", run_name="__main__")
''')
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
tail = r.stdout[-600:]
print(tail)
sys.exit(0 if r.returncode != 0 and "COUNTEREXAMPLE" in r.stdout else 1)
