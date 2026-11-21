"""Properties of the redline diff: nothing is lost, nothing is invented, identical input shows no change."""
import pytest
from hypothesis import given, strategies as st
import redline as RL

pytestmark = pytest.mark.fuzz
WORDS = st.sampled_from(["the", "Company", "$35.00", "$36.00", "9.0x", "analysis", "William", "Blair", "per", "share", "(1)", "12.5%", "NM", "merger", "a", "b"])
PARA = st.lists(WORDS, min_size=1, max_size=15)
DOC = st.lists(PARA, max_size=10)

def words_of(paras, kinds):
    out = []
    for p in paras:
        if p and p[0][0] == "head": continue
        out += "".join(t for k, t in p if k in kinds).split()
    return out

@given(DOC, DOC, st.floats(0.05, 0.95))
def test_revised_text_is_exactly_reconstructed(O, R, th):
    paras, st_ = RL.diff_aligned(O, R, th)
    assert words_of(paras[:len(R)], ("eq", "mv", "ins")) == [w for p in R for w in p]
    assert st_["aligned"] <= min(len(O), len(R)) and st_["moved"] <= st_["aligned"]

@given(DOC, DOC)
def test_every_original_word_is_kept_or_struck(O, R):
    paras, _ = RL.diff_aligned(O, R)
    assert sorted(words_of(paras, ("eq", "mv", "del"))) == sorted(w for p in O for w in p)

@given(DOC)
def test_identical_is_unchanged(O):
    paras, s = RL.diff_aligned(O, O)
    assert s["moved"] == 0 and all(k == "eq" for p in paras for k, _ in p)

@given(st.lists(st.lists(st.one_of(WORDS, st.just("")), min_size=1, max_size=6), max_size=6), st.lists(st.lists(WORDS, min_size=1, max_size=6), max_size=6))
def test_table_rows_never_crash(a, b):
    O = [{"row": r} for r in a]; R = [{"row": r} for r in b]
    paras, s = RL.diff_aligned(O, R)
    assert len(paras) >= len(R)

@given(st.text(max_size=400), st.sampled_from(["on", "off", "auto"]))
def test_split_paragraphs_total(t, mode):
    paras, m = RL.split_paragraphs(t, mode)
    assert m in ("on", "off")
    for p in paras:
        if isinstance(p, dict): assert any(p["row"])
        else: assert p and all(w for w in p)
