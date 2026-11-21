"""bankname.bank_key groups the ways a proxy writes one advisor."""
import pytest
from bankname import bank_key

@pytest.mark.parametrize("a,b", [("Centerview Partners", "Centerview Partners LLC"), ("Goldman Sachs & Co. LLC", "Goldman Sachs"),
                                 ("J.P. Morgan Securities LLC", "JPMorgan"), ("BofA Securities, Inc.", "Merrill Lynch"),
                                 ("Duff & Phelps", "Kroll, LLC"), ("William Blair & Company L.L.C.", "William Blair")])
def test_aliases_group(a, b):
    assert bank_key(a) == bank_key(b) != "unknown"

def test_known_keys():
    assert bank_key("William Blair & Company L.L.C.") == "williamblair"
    assert bank_key("Morgan Stanley & Co. LLC") == "morganstanley"
    assert bank_key("Citigroup Global Markets Inc.") == "citi"

@pytest.mark.parametrize("v", [None, "", "   ", "123", "&amp;"])
def test_empty_or_unreadable_is_unknown(v):
    assert bank_key(v) == "unknown"

def test_unlisted_bank_keeps_its_first_word():
    assert bank_key("Ducera Partners LLC") == "ducera"
    assert bank_key("ducera") == bank_key("DUCERA PARTNERS")

def test_known_collision_jpmorgan_and_morgan_stanley_stay_apart():
    assert bank_key("J.P. Morgan") != bank_key("Morgan Stanley")
