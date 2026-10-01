from trading.dhan_lot_size import parse_security_master_lot_sizes


def test_parse_official_dhan_security_and_lot_columns():
    csv_text = (
        "SEM_SMST_SECURITY_ID,SEM_LOT_UNITS,SEM_INSTRUMENT_NAME\n"
        "10001,20,OPTIDX\n"
        "10002,0,OPTIDX\n"
        "bad,25,OPTIDX\n"
        "10003,20.5,OPTIDX\n"
    )

    assert parse_security_master_lot_sizes(csv_text) == {"10001": 20}


def test_parse_alternate_security_master_headers_and_empty_metadata():
    csv_text = "SecurityId,LotSize\n12345,15\n"
    assert parse_security_master_lot_sizes(csv_text) == {"12345": 15}
    assert parse_security_master_lot_sizes("unrecognized,columns\n1,2\n") == {}