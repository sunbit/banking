from .domain import Rule
from .io import Match, MatchAll, MatchAny, MatchNumeric
from .io import Set, SetFromCapture, Add
from datatypes import TransactionType

from bank import load_categories

categories = load_categories('categories.yaml')


_rules = [

    # ---------------------------------------------------------
    # Rules to fix or improve source or destination description
    # And on some cases, set tags or related comment
    # ---------------------------------------------------------

    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'GIL', 'AEAT', 'DEDUCCION')
        ],
        actions=[
            Set('source', 'Agencia Tributaria'),
            Set('comment', 'Deducció Maternitat Gil')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'GIL', 'AEAT', 'DEDUCCION')
        ],
        actions=[
            Set('source', 'Agencia Tributaria'),
            Set('comment', 'Deducció Maternitat Gil')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'AEAT', 'IRPF', 'CARLES')
        ],
        actions=[
            Set('source', 'Agencia Tributaria'),
            Set('comment', 'Devolució Declaració Renda Carles')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'AEAT', 'IRPF', 'NURIA')
        ],
        actions=[
            Set('source', 'Agencia Tributaria'),
            Set('comment', 'Devolució Declaració Renda Núria')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'ESCORIAL'),
            MatchNumeric('amount', 500, operator='gt')
        ],
        actions=[
            Set('source', 'Fundació Escola Vedruna'),
            Set('comment', 'Nòmina Núria'),
            Add('tags', 'nomina')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'FUNDACIO', 'EDUCACIO', 'ART')
        ],
        actions=[
            Set('destination', "Escola Bressol Vic"),
            Set('comment', 'Mensualitat Gil')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'BBVA', 'SEGUROS')
        ],
        actions=[
            Set('destination', "BBVA Seguros"),
            Set('comment', "Aportació Pla d'estalvi"),
            Set('category', categories['estalvi'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'BBVA', 'SEGUROS')
        ],
        actions=[
            Set('source', "BBVA Seguros"),
            Set('comment', "Retirada diners Pla d'estalvi"),
            Set('category', categories['estalvi'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'CRUZ', 'ROJA')
        ],
        actions=[
            Set('destination', "Creu roja"),
            Set('comment', "Semestre de soci"),
            Set('category', categories['donacions'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'MUSSAP')
        ],
        actions=[
            Set('destination', "Mussap"),
            Set('comment', "Assegurança cotxe")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'AXA', 'SEGUROS')
        ],
        actions=[
            Set('destination', "AXA/Winterthur"),
            Set('comment', "Mutua Núria")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'TARADELL', 'RECIBO')
        ],
        actions=[
            Set('destination', "Ajuntament de Taradell"),
            Set('comment', "Impost Vehicles: Yaris")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'TARADELL', 'RESIDUS')
        ],
        actions=[
            Set('destination', "Ajuntament de Taradell"),
            Set('comment', "Impost Residus")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'TARADELL', 'IMMOBLES')
        ],
        actions=[
            Set('destination', "Ajuntament de Taradell"),
            Set('comment', "Impost Bens Immobles")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'TARADELL', 'ADEUDO')
        ],
        actions=[
            Set('destination', "Ajuntament de Taradell"),
            Set('comment', "Impost circulació")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'TARADELL', 'VEHICLES')
        ],
        actions=[
            Set('destination', "Ajuntament de Taradell"),
            Set('comment', "Impost Vehicles")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'TARADELL', 'ENTRADA')
        ],
        actions=[
            Set('destination', "Ajuntament de Taradell"),
            Set('comment', "Impost Gual")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'VEDRUNA', 'ESCORIAL', 'RECIBO')
        ],
        actions=[
            Set('destination', "Fundació Escola Vedruna"),
            Set('comment', "Rebut dinars o altres")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            Match('details.origin_account_number', '21000420510200148152')
        ],
        actions=[
            Set('source', 'Fundació Escola Vedruna'),
            Set('comment', "Pagament activitats extres: {details[concept]}")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'TGSS', 'NOMINA', 'PENSION')
        ],
        actions=[
            Set('source', 'Tresoreria Seguretat Social'),
            Set('comment', "Nòmina permís maternitat Núria")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            MatchAll('keywords', 'NEXIONA')
        ],
        actions=[
            Set('source', 'Nexiona Connectocrats S.L.'),
        ]
    ),
    Rule(
        conditions=[
            MatchAny('type', TransactionType.PURCHASE),
            MatchAny('destination', r'Amz\*', r'Amzn', r'Amazon', regex='search')
        ],
        actions=[
            Set('destination', "Amazon"),
        ]
    ),
    Rule(
        conditions=[
            MatchAny('type', TransactionType.PURCHASE_RETURN),
            MatchAny('source', r'Amz\*', r'Amzn', r'Amazon', regex='search')
        ],
        actions=[
            Set('source', "Amazon"),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'Aliexpress', regex='search')
        ],
        actions=[
            Set('destination', "Aliexpress"),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE_RETURN),
            Match('source', 'Aliexpress', regex='search')
        ],
        actions=[
            Set('source', 'Aliexpress'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            Match('source', r'A\.E\.A\.T\.', regex='search')
        ],
        actions=[
            Set('source', 'Agencia Tributaria')
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            Match('keywords', r'TGSS')
        ],
        actions=[
            Set('source', 'Institut Nacional Seguretat Social')
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            Match('source', r'paypal', regex='search')
        ],
        actions=[
            Set('source', 'Paypal')
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', 'guissona', 'bon area', regex='search')
        ],
        actions=[
            Set('destination', 'BonÀrea Guissona')
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'BON', 'PREU', 'JIP')
        ],
        actions=[
            Set('destination', 'JIP Moda')
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'fisio\s*corporal', regex='search')
        ],
        actions=[
            Set('destination', 'Fisio Corporal El Pont'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('keywords', 'AKI')
        ],
        actions=[
            Set('destination', 'AKI'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('keywords', 'LEROY', 'MERLIN')
        ],
        actions=[
            Set('destination', 'Leroy Merlin'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('keywords', 'BRICOESTEBA')
        ],
        actions=[
            Set('destination', 'FESMÉS'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('keywords', 'PINTUR')
        ],
        actions=[
            Set('destination', 'Pintur Vic'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'(can|cansal).*?codina', regex='search')
        ],
        actions=[
            Set('destination', 'Can Codina'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'itv', r'revisions.*?vehicles', regex='search')
        ],
        actions=[
            Set('destination', 'Itv'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'BISBAT', 'SEMINARI')
        ],
        actions=[
            Set('destination', 'Parking Seminari'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'privalia', regex='search')
        ],
        actions=[
            Set('destination', 'Privalia'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'RESIDENCIAL', 'VIELLA')
        ],
        actions=[
            Set('destination', 'Cafeteria La Salle'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'Ap. H. Sant Joan De Deu')
        ],
        actions=[
            Set('destination', 'Aparcament Sant Joan de Deu'),
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', 'pkhosvic', 'pk vic online', regex='search'),
        ],
        actions=[
            Set('destination', 'Aparcament Hospital General Vic'),
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('destination', 'MATER', 'VILA'),
        ],
        actions=[
            Set('destination', 'Llibreria Mater'),
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('keywords', 'WALLAPOP'),
        ],
        actions=[
            Set('destination', 'Wallapop'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE_RETURN),
            Match('keywords', 'WALLAPOP'),
        ],
        actions=[
            Set('source', 'Wallapop'),
        ]
    ),

    # ---------------------------------------------------------
    # Rules to set comments to help understand the transaction
    # ---------------------------------------------------------

    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('details.drawee', 'Nuria', regex='search'),
            MatchAll('keywords', 'SIMYO')
        ],
        actions=[
            Set('comment', "Mòbil Núria")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('details.drawee', 'Carles', regex='search'),
            MatchAll('keywords', 'SIMYO')
        ],
        actions=[
            Set('comment', "Mòbil Carles")
        ]
    ),


    # ------------------------------------------------
    #             Rules to set tags
    # ------------------------------------------------

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'Paypal', regex='search')
        ],
        actions=[
            SetFromCapture('destination', source='destination', regex=r'Paypal\s+\*(.*)'),
            Add('tags', 'paypal')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.ISSUED_TRANSFER),
            MatchAll('keywords', 'PAGO', 'ENTRE', 'AMIGOS')
        ],
        actions=[
            Add('tags', "Bizum"),
            SetFromCapture('comment', source='details.concept', regex=r'\/([^\/]+)$')
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'Cafeteria La Salle', regex='match'),
        ],
        actions=[
            Add('tags', 'feina'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.RECEIVED_TRANSFER),
            Match('source', r'nexiona', regex='search'),
            MatchNumeric('amount', 500, operator='gt')
        ],
        actions=[
            Add('tags', 'nomina'),
        ]
    ),

    # ------------------------------------------------
    #             Rules to set categories
    # ------------------------------------------------

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'E\.S\.\s+', r'esclatoil', r'area\s+de\s+serveis\s+taradell', regex='search')
        ],
        actions=[
            Set('category', categories['gasoil'])
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'cabrabo', r'bon\s+preu', r'lidl', r'carrefour', r'esclat\s', r'mercadona', r'aldi', regex='search')
        ],
        actions=[
            Set('category', categories['supermercat'])
        ]
    ),

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'guissona', regex='search')
        ],
        actions=[
            Set('category', categories['carnisseria'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'fisio', regex='search')
        ],
        actions=[
            Set('category', categories['salut'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'Pintur vic', r'^aki$', r'fesmés', r'ferreteria', r'instal tot', r'leroy merlin', regex='search')
        ],
        actions=[
            Set('category', categories['ferreteria'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'TELSTAR', 'ELECTRONICA')
        ],
        actions=[
            Set('category', categories['electronica'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'DROGUERIA', 'JUNYENT')
        ],
        actions=[
            Set('category', categories['jardineria'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('keywords', 'FARMACIA')
        ],
        actions=[
            Set('category', categories['farmacia'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'dosfarma', regex='search')
        ],
        actions=[
            Set('category', categories['farmacia'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'eysa', r'aparcament', r'wesmartpark', r'A\.C\.E\.S\.A', r'tunels\s+vallvi', r'invicat.*?mollet', r'par(k|qu)ing', regex='search')
        ],
        actions=[
            Set('category', categories['parkings_peatges'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'restaurant', r'cafeteria', regex='search')
        ],
        actions=[
            Set('category', categories['restauracio'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'Encarna', regex='search')
        ],
        actions=[
            Set('category', categories['herbolari'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'la redoute', r'esports\s+everest', r'Jip moda', r'privalia', r'h&m', regex='search')
        ],
        actions=[
            Set('category', categories['roba_calcat'])
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'itunes', regex='search'),
            MatchNumeric('amount', 13.99, operator='eq', absolute=True)
        ],
        actions=[
            Set('category', categories['subscripcions']),
            Set('comment', 'Netflix')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'itunes', regex='search'),
            Match('category', None)
        ],
        actions=[
            Set('category', categories['apps']),
            Add('tags', 'appstore'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'GOOGLE', 'PLAY', 'APPS'),
        ],
        actions=[
            Set('category', categories['apps']),
            Add('tags', 'googleplay'),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', 'can codina', 'fussimanya', regex='search'),
        ],
        actions=[
            Set('category', categories['carnisseria']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'itv', regex='match'),
        ],
        actions=[
            Set('category', categories['manteniment_cotxes']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', 'privalia', regex='match'),
        ],
        actions=[
            Set('category', categories['roba_calcat']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'CLINICA', 'DENTAL'),
        ],
        actions=[
            Set('category', categories['salut']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'RACO', 'PANARRA'),
        ],
        actions=[
            Set('category', categories['fleca']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('keywords', 'TORTADES', 'GARDEN'),
        ],
        actions=[
            Set('category', categories['jardineria']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('keywords', 'TELECOMUNICACIONS'),
        ],
        actions=[
            Set('category', categories['internet']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('keywords', 'SIMYO'),
        ],
        actions=[
            Set('category', categories['telefon_mobil']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('keywords', 'ENDESA'),
        ],
        actions=[
            Set('category', categories['electricitat']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAny('destination', r'gas natural', r'naturgy', regex='search'),
        ],
        actions=[
            Set('category', categories['gas']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.MORTAGE_RECEIPT),
        ],
        actions=[
            Set('category', categories['credits_hipoteques']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAny('destination', r'santa lucia', r'mapfre', r'mussap', regex='search'),
        ],
        actions=[
            Set('category', categories['assegurances']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('keywords', 'SOREA'),
        ],
        actions=[
            Set('category', categories['aigua']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.ISSUED_TRANSFER),
            Match('keywords', 'CASACUBERTA', 'AUTOMOBILS'),
        ],
        actions=[
            Set('category', categories['manteniment_cotxes']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'cdmon', regex='search'),
        ],
        actions=[
            Set('category', categories['dominis']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'nespresso', regex='search'),
        ],
        actions=[
            Set('category', categories['alimentacio']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'fruites jimenez', regex='search'),
        ],
        actions=[
            Set('category', categories['fruiteria']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'maxi casa', regex='search'),
        ],
        actions=[
            Set('category', categories['basar']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('destination', r'escola bressol', regex='search'),
        ],
        actions=[
            Set('category', categories['escola']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'redondeo\s+s.lidario', regex='search'),
        ],
        actions=[
            Set('category', categories['donacions']),
            Set('comment', 'Arrodoniment compra Esclat')
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('destination', r'sirena', regex='search'),
        ],
        actions=[
            Set('category', categories['peix_congelats']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'llibreria', 'monpaper', regex='search'),
        ],
        actions=[
            Set('category', categories['llibreria_papereria']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAll('destination', 'geni', 'perruquers', regex='search'),
        ],
        actions=[
            Set('category', categories['perruqueria']),
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            Match('keywords', 'OPTICA'),
        ],
        actions=[
            Set('category', categories['optica']),
        ]
    ),

]
