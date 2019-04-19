from .domain import Rule
from .io import Match, MatchAll, MatchAny
from .io import Set, SetFromCapture, Add
from datatypes import TransactionType

_rules = [
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
            MatchAll('keywords', 'ESCORIAL')
        ],
        actions=[
            Set('source', 'Fundació Escola Vedruna'),
            Set('comment', 'Nòmina Núria')
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
            Set('comment', "Aportació Pla d'estalvi")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            MatchAll('keywords', 'CRUZ', 'ROJA')
        ],
        actions=[
            Set('destination', "Creu roja"),
            Set('comment', "Semestre de soci")
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
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('details.drawee', 'Nuria'),
            MatchAll('keywords', 'SIMYO')
        ],
        actions=[
            Set('comment', "Mòbil Núria")
        ]
    ),
    Rule(
        conditions=[
            Match('type', TransactionType.DOMICILED_RECEIPT),
            Match('details.drawee', 'Carles'),
            MatchAll('keywords', 'SIMYO')
        ],
        actions=[
            Set('comment', "Mòbil Carles")
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
            MatchAny('type', TransactionType.PURCHASE, TransactionType.PURCHASE_RETURN),
            MatchAny('destination', r'Amz\*', r'Amzn', r'Amazon', regex='search')
        ],
        actions=[
            Set('destination', "Amazon"),
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
            Match('type', TransactionType.ISSUED_TRANSFER),
            MatchAll('keywords', 'PAGO', 'ENTRE', 'AMIGOS')
        ],
        actions=[
            Add('tags', "Bizum"),
            SetFromCapture('comment', source='details.concept', regex=r'\/([^\/]+)$')
        ]
    ),

    # Categorization Rules

    Rule(
        conditions=[
            Match('type', TransactionType.PURCHASE),
            MatchAny('destination', r'E\.S\.\s+', r'esclatoil', regex='search')
        ],
        actions=[
            Set('category', 'Gasoil')
        ]
    ),
]
