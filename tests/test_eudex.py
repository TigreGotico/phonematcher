from phonematcher.eudex import eudex_hash, Hash, weighted_hamming_distance, similar

def test_eudex_hash_basic():
    # Basic ASCII word
    h = eudex_hash("hello")
    assert isinstance(h, int)
    # Same word yields same hash
    assert eudex_hash("hello") == h
    # Different word produces different hash
    assert eudex_hash("hellou") != h

def test_eudex_hash_empty():
    assert eudex_hash("") == 0
    assert eudex_hash(" ") == 0

def test_weighted_hamming_distance():
    h1 = eudex_hash("hello")
    h2 = eudex_hash("hellou")
    dist = weighted_hamming_distance(h1, h2)
    assert dist >= 0
    assert isinstance(dist, int)

def test_similar_function():
    h1 = eudex_hash("hello")
    h2 = eudex_hash("hello")
    h3 = eudex_hash("hellou")
    assert similar(h1, h2)
    # Possibly different, depending on threshold
    assert isinstance(similar(h1, h3), bool)

def test_hash_class_consistency():
    h1 = Hash("hello")
    h2 = Hash("hello")
    assert int(h1) == int(h2)
    h3 = Hash("hellou")
    assert int(h1) != int(h3)

def test_difference_class_methods():
    h1 = Hash("hello")
    h2 = Hash("hellou")
    diff = h1 - h2
    assert isinstance(diff.dist(), int)
    assert isinstance(diff.hamming(), int)
    assert isinstance(diff.xor_val(), int)
    assert isinstance(diff.similar(), bool)

def test_hash_repr():
    h = Hash("test")
    r = repr(h)
    assert r.startswith("Hash(") and r.endswith(")")

def test_similarity_threshold_edge():
    h1 = Hash("hello")
    h2 = Hash("hellp")
    diff = h1 - h2
    # Should be boolean
    val = diff.similar()
    assert isinstance(val, bool)


# -----------------------------
# Exact match / normalization
# -----------------------------
def test_exact():
    assert Hash("JAva") == Hash("jAva")
    assert Hash("co!mputer") == Hash("computer")
    assert Hash("comp-uter") == Hash("computer")
    assert Hash("comp@u#te?r") == Hash("computer")
    assert Hash("lal") == Hash("lel")
    assert Hash("rindom") == Hash("ryndom")
    assert Hash("riiiindom") == Hash("ryyyyyndom")
    assert Hash("riyiyiiindom") == Hash("ryyyyyndom")
    assert Hash("triggered") == Hash("TRIGGERED")
    assert Hash("repert") == Hash("ropert")

# -----------------------------
# Mismatch check
# -----------------------------
def test_mismatch():
    assert Hash("reddit") != Hash("eddit")
    assert Hash("lol") != Hash("lulz")
    assert Hash("ijava") != Hash("java")
    assert Hash("jiva") != Hash("java")
    assert Hash("jesus") != Hash("iesus")
    assert Hash("aesus") != Hash("iesus")
    assert Hash("iesus") != Hash("yesus")
    assert Hash("rupirt") != Hash("ropert")
    assert Hash("ripert") != Hash("ropyrt")
    assert Hash("rrr") != Hash("rraaaa")
    assert Hash("randomal") != Hash("randomai")

# -----------------------------
# Distance comparisons
# -----------------------------
def test_distance():
    assert (Hash("lizzard") - Hash("wizzard")).dist() > (Hash("rick") - Hash("rolled")).dist()
    assert (Hash("bannana") - Hash("panana")).dist() >= (Hash("apple") - Hash("abple")).dist()
    #assert (Hash("franco") - Hash("sranco")).dist() < (Hash("unicode") - Hash("ASCII")).dist()
    assert (Hash("trump") - Hash("drumpf")).dist() < (Hash("gangam") - Hash("style")).dist()

# -----------------------------
# Reflexivity (commutativity)
# -----------------------------
def test_reflexivity():
    assert (Hash("a") - Hash("b")).dist() == (Hash("b") - Hash("a")).dist()
    assert (Hash("youtube") - Hash("facebook")).dist() == (Hash("facebook") - Hash("youtube")).dist()
    assert (Hash("Rust") - Hash("Go")).dist() == (Hash("Go") - Hash("Rust")).dist()
    assert (Hash("rick") - Hash("rolled")).dist() == (Hash("rolled") - Hash("rick")).dist()

# -----------------------------
# Similarity tests
# -----------------------------
def test_similar():
    # Similar
    assert (Hash("yay") - Hash("yuy")).similar()
    assert (Hash("crack") - Hash("crakk")).hamming() < 10
    assert (Hash("what") - Hash("wat")).similar()
    assert (Hash("jesus") - Hash("jeuses")).similar()
    assert (Hash("") - Hash("")).similar()
    assert (Hash("jumpo") - Hash("jumbo")).similar()
    assert (Hash("lol") - Hash("lulz")).similar()
    assert (Hash("goth") - Hash("god")).similar()
    assert (Hash("maier") - Hash("meyer")).similar()
    assert (Hash("java") - Hash("jiva")).similar()
    assert (Hash("möier") - Hash("meyer")).similar()
    assert (Hash("fümlaut") - Hash("fymlaut")).similar()
    #assert (Hash("ümlaut") - Hash("ymlaut")).similar()
    assert (Hash("schmid") - Hash("schmidt")).hamming() < 14

    # Not similar
    assert not (Hash("youtube") - Hash("reddit")).similar()
    assert not (Hash("yet") - Hash("vet")).similar()
    assert not (Hash("hacker") - Hash("4chan")).similar()
    assert not (Hash("awesome") - Hash("me")).similar()
    assert not (Hash("prisco") - Hash("vkisco")).similar()
    assert not (Hash("no") - Hash("go")).similar()
    assert not (Hash("horse") - Hash("norse")).similar()
    assert not (Hash("nice") - Hash("mice")).similar()

