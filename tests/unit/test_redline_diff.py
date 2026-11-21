"""redline.py: paragraph splitting, cell normalization and the aligned word/character diff behind every redline."""
import pytest
import redline as RL

def kinds(runs): return [k for k, _ in runs]
def side(paras, keep):
    """Words of one side reconstructed from diff runs: original = eq/mv/del, revised = eq/mv/ins."""
    return " ".join("".join(t for k, t in p if k in keep) for p in paras if p and p[0][0] != "head").split()

def test_split_off_keeps_lines_and_rows():
    paras, mode = RL.split_paragraphs("First para.\n\nSecond para.\n| Company | 9.0x |\n|---|---|\n", "off")
    assert mode == "off"
    assert paras == [["First", "para."], ["Second", "para."], {"row": ["Company", "9.0x"]}]

def test_split_on_reflows_hard_wraps_and_drops_page_numbers():
    text = "William Blair performed a\ndiscounted cash flow analysis\nof the Company.\n12\nThe next paragraph."
    paras, _ = RL.split_paragraphs(text, "on")
    assert [" ".join(p) for p in paras] == ["William Blair performed a discounted cash flow analysis of the Company.", "The next paragraph."]

def test_auto_detects_hard_wrapping():
    wrapped = "\n".join(["this line is long enough and runs on without stopping"] * 14)
    assert RL.split_paragraphs(wrapped, "auto")[1] == "on"
    assert RL.split_paragraphs("One sentence.\nTwo sentence.\n", "auto")[1] == "off"

def test_normalize_quotes_and_bullets():
    assert RL.normalize("“Merger”  ‘x’ ") == '"Merger" \'x\''
    assert RL.normalize("— item").startswith("• ")

def test_layout_tables_become_prose():
    paras, _ = RL.split_paragraphs("| • | a bullet point |\n| only one cell |\n", "off")
    assert paras == [["•", "a", "bullet", "point"], ["only", "one", "cell"]]

@pytest.mark.parametrize("a,b", [("$1,234", "1234"), ("(1.2)", "-1.2"), ("9.1x (3)", "9.1x"), ("n.m.", "NM"), ("N/A", "n.a."), ("€ 5", "5")])
def test_norm_cell_equivalences(a, b):
    assert RL.norm_cell(a) == RL.norm_cell(b)

def test_row_sim():
    assert RL.row_sim(["Alpha", "9.0x", "8.0x"], ["Alpha", "9.0x", "8.0x"]) == 1.0
    assert RL.row_sim(["Alpha", "9.0x"], ["Zeta", "1.0x"]) < 0.35

def test_identical_documents_have_no_changes():
    O, _ = RL.split_paragraphs("A first paragraph.\nA second one.\n| Alpha | 9.0x |\n", "off")
    paras, st = RL.diff_aligned(O, O)
    assert st == {"original_paragraphs": 3, "revised_paragraphs": 3, "aligned": 3, "moved": 0}
    assert all(k in ("eq", "sep") for p in paras for k, _ in p)

def test_digits_marked_not_the_sentence():
    O = [["paragraphs", "2,", "3", "and", "5"]]; R = [["paragraphs", "3,", "4", "and", "6"]]
    runs = RL.diff_aligned(O, R)[0][0]
    assert ["eq", "paragraphs "] == runs[0]
    deleted = "".join(t for k, t in runs if k == "del"); inserted = "".join(t for k, t in runs if k == "ins")
    assert deleted.replace(" ", "") == "235" and inserted.replace(" ", "") == "346"

def test_moved_paragraph_is_marked_moved():
    a = [["alpha", "beta", "gamma", "delta"], ["one", "two", "three", "four"], ["red", "green", "blue", "cyan"]]
    paras, st = RL.diff_aligned(a, [a[2], a[0], a[1]])
    assert st["moved"] == 1 and kinds(paras[0]) == ["mv"]

def test_dropped_paragraphs_listed_at_the_end():
    O = [["kept", "paragraph", "here"], ["dropped", "entirely", "now"]]; R = [["kept", "paragraph", "here"]]
    paras, st = RL.diff_aligned(O, R)
    assert paras[-2][0][0] == "head" and "(1 of 2)" in paras[-2][0][1]
    assert paras[-1] == [["del", "dropped entirely now "]]

def test_changed_table_cell():
    runs = RL.row_diff(["Alpha", "9.0x", "8.0x"], ["Alpha", "9.5x", "8.0x"])
    assert ["del", "9.0x"] in runs and ["ins", "9.5x"] in runs and ["eq", "8.0x"] in runs

def test_char_diff_whole_word_when_dissimilar():
    assert RL.char_diff("cat", "zebra") == [["del", "cat"], ["ins", "zebra"]]
    assert RL.char_diff("$35.00", "$36.00") == [["eq", "$3"], ["del", "5"], ["ins", "6"], ["eq", ".00"]]

def test_lis_indices():
    assert RL.lis_indices([]) == set()
    assert sorted(RL.lis_indices([0, 1, 2])) == [0, 1, 2]
    assert len(RL.lis_indices([2, 0, 1])) == 2

def test_cut_section_takes_last_start_heading():
    paras = [["Contents"], ["Opinion", "of", "Blair"], ["toc"], ["Opinion", "of", "Blair"], ["body"], ["Next", "Heading"], ["after"]]
    got = RL.cut_section(paras, "Opinion of Blair", "Next Heading", "x")
    assert got == [["Opinion", "of", "Blair"], ["body"]]
