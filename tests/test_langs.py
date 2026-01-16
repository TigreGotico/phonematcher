import unittest
from phonematcher.clustering import PhoneticFuzzySearch, EN_MAPPING, NL_MAPPING, DE_MAPPING, PT_MAPPING, RU_MAPPING



class TestPhoneticFuzzySearch(unittest.TestCase):

    def run_lang_tests(self, mapping, test_cases):
        """Helper to initialize search and run batch assertions."""
        ffs = PhoneticFuzzySearch(mapping)
        for i, (original, typo) in enumerate(test_cases):
            ffs.add_term(original, i)

        for i, (original, typo) in enumerate(test_cases):
            results = ffs.search(typo)
            self.assertTrue(len(results) > 0, f"Failed to find match for query: {typo}")
            self.assertEqual(results[0].term, original, f"Query '{typo}' should have matched '{original}'")

    def test_english_en(self):
        cases = [
            ("the weather is thin", "ze wezer is zin"),
            ("rough cough through", "ruff coff thru"),
            ("knight in shining armor", "nite in shinin armur"),
            ("bright white light", "brite wite lite"),
            ("psychology is hard", "sycology is hard"),
            ("phone the pharmacy", "fone ze farmasy"),
            ("sugar and spice", "shugar and spyce"),
            ("children play in church", "tchildren play in tchurch"),
            ("yellow fellow", "jellow fello"),
            ("queue for the queen", "kewe for ze kween"),
            ("think about things", "sink abowt sings"),
            ("ocean motion", "oshan moshan"),
            ("action station", "akshon stashon"),
            ("character and chaos", "karakter and kaoss"),
            ("weight of the world", "wait of ze werld"),
            ("nature and nurture", "nachur and nerchur"),
            ("bread and butter", "bred and buter"),
            ("moon and noon", "mun and nun"),
            ("bird on the curb", "berd on ze kerb"),
            ("simple sample", "simpel sampel")
        ]
        self.run_lang_tests(EN_MAPPING, cases)

    def test_dutch_nl(self):
        cases = [
            ("de kat op de mat", "de cad ob de mad"),
            ("maan en sterren", "man en steren"),
            ("school is leuk", "skool is luik"),
            ("goedemorgen allemaal", "hudemorhen alemal"),
            ("huis en tuin", "huys en tuyn"),
            ("ijs met slagroom", "eis met slachrom"),
            ("nieuwe boek", "niuwe buk"),
            ("schaap in de wei", "skap in de wy"),
            ("groene boom", "grone bom"),
            ("vis in de vijver", "fis in de fyver"),
            ("koud water", "kowd water"),
            ("zachte kussen", "zakte kusen"),
            ("neus en oren", "nuis en oren"),
            ("fijne dag nog", "feine dach nok"),
            ("blauwe lucht", "blawe lukt"),
            ("fietsen in de stad", "fitsen in de stat"),
            ("konijn in het gras", "konein in het kras"),
            ("herfst is koud", "herfst is kowt"),
            ("liedje zingen", "lidje singen"),
            ("brood met kaas", "brot met kas")
        ]
        self.run_lang_tests(NL_MAPPING, cases)

    def test_german_de(self):
        cases = [
            ("ich mag dich", "ich mak dich"),
            ("acht gute nacht", "akt gute nakt"),
            ("zeit für tee", "tseit fur te"),
            ("schöne mädchen", "shone madchen"),
            ("vater und mutter", "fater unt muter"),
            ("wasser ist kalt", "vasser ist kalt"),
            ("schule ist schön", "shule ist shone"),
            ("spritze und stein", "shpritse und shtein"),
            ("pferd im stall", "ferd im shtall"),
            ("liebe grüße", "libe gruse"),
            ("mein neues haus", "main neues haws"),
            ("brot und butter", "brot unt buter"),
            ("singen und klingen", "singen unt klingen"),
            ("taxi nach hause", "taksi nak hawse"),
            ("bitte sehr", "bite ser"),
            ("ähnliche fälle", "enliche fele"),
            ("junge leute", "yunge loite"),
            ("zwanzig ziegen", "tsvantsik tsigen"),
            ("kaffee und kuchen", "kafe und kuken"),
            ("sonne am himmel", "sone am himel")
        ]
        self.run_lang_tests(DE_MAPPING, cases)

    def test_portuguese_pt(self):
        cases = [
            ("pão com queijo", "pao com keijo"),
            ("o carro vermelho", "o caro vermelo"),
            ("minha casa nova", "minya caza nova"),
            ("chocolate quente", "shocolate kente"),
            ("cachorro corre", "kashoro kore"),
            ("maçã e limão", "masa e limão"),
            ("jogo de futebol", "zhogo de futebol"),
            ("vento no campo", "vento no kampo"),
            ("coração batendo", "corasao batendo"),
            ("galinha e coelho", "galinya e koelo"),
            ("xícara de chá", "shicara de sha"),
            ("passaros voam", "pasaros voam"),
            ("guia de viagem", "gia de viazhem"),
            ("hoje tem festa", "oje tem festa"),
            ("água e fogo", "agua e fogo"),
            ("gente feliz", "zhente felis"),
            ("sol na praia", "sol na praya"),
            ("rádio ligado", "radio ligado"),
            ("manhã de sol", "manya de sol"),
            ("peixe no mar", "peishe no mar")
        ]
        self.run_lang_tests(PT_MAPPING, cases)

    def test_russian_ru(self):
        # Using phonetic approximations for typos
        cases = [
            ("доброе утро", "доброэ утро"),
            ("хорошо живу", "харашо жыву"),
            ("чай и сахар", "тяй и сахар"),
            ("щи да каша", "ши да каша"),
            ("я тебя люблю", "я тибя лублу"),
            ("мама мыла раму", "мама мила раму"),
            ("ёлка в лесу", "елка в лису"),
            ("день и ночь", "ден и ноч"),
            ("хлеб и вода", "клеб и вада"),
            ("солнце светит", "сонце светит"),
            ("машина едет", "машына едет"),
            ("город и замок", "горат и замак"),
            ("русский язык", "руский изык"),
            ("белая птица", "бэлая птица"),
            ("цирк и театр", "сирк и тиатр"),
            ("южный ветер", "ужный ветер"),
            ("школьная доска", "школная даска"),
            ("мой верный друг", "мой верний друк"),
            ("чёрный кофе", "чорний кофе"),
            ("этот человек", "этат чилавек")
        ]
        self.run_lang_tests(RU_MAPPING, cases)


if __name__ == "__main__":
    unittest.main()