# Lifecycle fixture (synthetic)

`company.json` is an **invented** company, Example Industrial Products, Inc. (EXMP), with six invented peers. Every number is
made up. It exists so the model, book and letter stages of `ticker-to-proxy` can run and be tested with no network:

```
python3 scripts/lifecycle/ticker_to_proxy.py run EXMP /tmp/exmp --advisor "Evercore Group L.L.C." --fixture examples/lifecycle-fixture/company.json
```

It follows the `company/1` schema in `references/lifecycle.md`, as `fetch_company.py` writes it for a real ticker.
