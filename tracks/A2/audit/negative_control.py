"""Negative control for check_proofs.py: run it against a call-by-NAME Let (substitute the unevaluated bound term,
no value restriction). PROOFS.md Proof 4 says the size measure then fails; the checker must report counterexamples.
Run: .venv/bin/python tracks/A2/audit/negative_control.py   (exit 0 = the control behaved: counterexamples found)"""
import subprocess, sys, textwrap
code = textwrap.dedent('''
    import runpy, sys
    import dsdk.lang.calc as c
    orig_step = c.step
    def step_cbn(e):
        if isinstance(e, c.Let):
            return c._subst(e.body, e.name, e.bound) if e.name else None
        return orig_step(e)
    c.step = step_cbn
    c.substitute = c.substitute
    sys.argv = ["check_proofs.py", "5"]
    runpy.run_path("tracks/A2/audit/check_proofs.py", run_name="__main__")
''')
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
print(r.stdout[-700:])
sys.exit(0 if r.returncode != 0 and "COUNTEREXAMPLE" in r.stdout else 1)
