from . import domain
import datatypes

_rules = [
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.RECEIVED_TRANSFER),
            domain.MatchKeywords(['GIL', 'AEAT', 'DEDUCCION'], domain.AND)
        ],
        actions=[
            domain.setIssuer('Agencia Tributaria', ),
            domain.setComment('Deducció Maternitat Gil')
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.RECEIVED_TRANSFER),
            domain.MatchKeywords(['AEAT', 'IRPF', 'CARLES'], domain.AND)
        ],
        actions=[
            domain.setIssuer('Agencia Tributaria', ),
            domain.setComment('Devolució Declaració Renda Carles')
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.RECEIVED_TRANSFER),
            domain.MatchKeywords(['AEAT', 'IRPF', 'NURIA'], domain.AND)
        ],
        actions=[
            domain.setIssuer('Agencia Tributaria', ),
            domain.setComment('Devolució Declaració Renda Núria')
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.RECEIVED_TRANSFER),
            domain.MatchKeywords(['ESCORIAL'], domain.AND)
        ],
        actions=[
            domain.setIssuer('Fundació Escola Vedruna'),
            domain.setComment('Nòmina Núria')
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['FUNDACIO', 'EDUCACIO', 'ART'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Escola Bressol Vic"),
            domain.setComment('Mensualitat Gil')
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['BBVA', 'SEGUROS'], domain.AND)
        ],
        actions=[
            domain.setRecipient("BBVA Seguros"),
            domain.setComment("Aportació Pla d'estalvi")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['CRUZ', 'ROJA'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Creu roja"),
            domain.setComment("Semestre de soci")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['MUSSAP'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Mussap"),
            domain.setComment("Assegurança cotxe")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['AXA', 'SEGUROS'], domain.AND)
        ],
        actions=[
            domain.setRecipient("AXA/Winterthur"),
            domain.setComment("Mutua Núria")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['TARADELL', 'RECIBO'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Ajuntament de Taradell"),
            domain.setComment("Impost Vehicles: Yaris")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['TARADELL', 'RESIDUS'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Ajuntament de Taradell"),
            domain.setComment("Impost Residus")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['TARADELL', 'IMMOBLES'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Ajuntament de Taradell"),
            domain.setComment("Impost Bens Immobles")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['TARADELL', 'ADEUDO'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Ajuntament de Taradell"),
            domain.setComment("Impost circulació")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['TARADELL', 'VEHICLES'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Ajuntament de Taradell"),
            domain.setComment("Impost Vehicles")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['TARADELL', 'ENTRADA'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Ajuntament de Taradell"),
            domain.setComment("Impost Gual")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchKeywords(['VEDRUNA', 'ESCORIAL', 'RECIBO'], domain.AND)
        ],
        actions=[
            domain.setRecipient("Fundació Escola Vedruna"),
            domain.setComment("Rebut dinars o altres")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.RECEIVED_TRANSFER),
            domain.MatchDetail('sender_account_number', '21000420510200148152')
        ],
        actions=[
            domain.setIssuer("Fundació Escola Vedruna"),
            domain.setComment("Pagament activitats extres: {details[description]}")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.RECEIVED_TRANSFER),
            domain.MatchKeywords(['TGSS', 'NOMINA', 'PENSION'], domain.AND)
        ],
        actions=[
            domain.setIssuer("Tresoreria Seguretat Social"),
            domain.setComment("Nòmina permís maternitat Núria")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchDetail('librado', 'Nuria'),
            domain.MatchKeywords(['SIMYO'], domain.AND)
        ],
        actions=[
            domain.setComment("Mòbil Núria")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.DOMICILED_RECEIPT),
            domain.MatchDetail('librado', 'Carles'),
            domain.MatchKeywords(['SIMYO'], domain.AND)
        ],
        actions=[
            domain.setComment("Mòbil Carles")
        ]
    ),
    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.RECEIVED_TRANSFER),
            domain.MatchKeywords(['NEXIONA'], domain.AND)
        ],
        actions=[
            domain.setIssuer("Nexiona Connectocrats S.L."),
        ]
    ),

    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.PURCHASE),
            domain.MatchField('destination', 'Paypal')
        ],
        actions=[
            domain.setRecipient(r'Paypal\s+\*(.*)', 0),
            domain.setTag('paypal')
        ]
    ),

    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.PURCHASE),
            domain.MatchFieldMulti('destination', ['Amz*', 'Amzn', 'Amazon', ], domain.OR)
        ],
        actions=[
            domain.setRecipient("Amazon"),
        ]
    ),

    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.PURCHASE_RETURN),
            domain.MatchFieldMulti('source', ['Amz*', 'Amzn', 'Amazon', ], domain.OR)
        ],
        actions=[
            domain.setIssuer("Amazon"),
        ]
    ),

    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.PURCHASE),
            domain.MatchFieldMulti('destination', ['Aliexpress'], domain.OR)
        ],
        actions=[
            domain.setRecipient("Aliexpress"),
        ]
    ),

    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.PURCHASE_RETURN),
            domain.MatchFieldMulti('source', ['Aliexpress'], domain.OR)
        ],
        actions=[
            domain.setIssuer("Aliexpress"),
        ]
    ),

    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.ISSUED_TRANSFER),
            domain.MatchKeywords(['PAGO', 'ENTRE', 'AMIGOS'], domain.AND)
        ],
        actions=[
            domain.setTag("Bizum"),
            domain.setComment("{details[concepto]}", regex=r'\/([^\/]+)$', regex_group=0)

        ]
    ),

    # Categorization Rules

    domain.Rule(
        conditions=[
            domain.MatchTransactionType(datatypes.TransactionType.PURCHASE),
            domain.MatchFieldMulti('destination', ['E\.S\.', 'esclatoil'], domain.OR)
        ],
        actions=[
            domain.setCategory("Gasoil")
        ]
    ),
]

