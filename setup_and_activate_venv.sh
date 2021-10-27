if [[ ! -d .venv ]]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install wheel
    pip install --editable .[test]
else
    source .venv/bin/activate
fi
