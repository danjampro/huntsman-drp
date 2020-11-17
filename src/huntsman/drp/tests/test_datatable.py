import pytest
import copy
from datetime import timedelta

from huntsman.drp.utils.date import current_date, parse_date
from huntsman.drp.fitsutil import read_fits_header
from huntsman.drp.datatable import RawDataTable

from pymongo.errors import ServerSelectionTimeoutError


def test_mongodb_wrong_host_name(raw_data_table, config):
    """Test if an error is raised if the mongodb hostname is incorrect."""
    modified_config = copy.deepcopy(config)
    modified_config["mongodb"]["hostname"] = "nonExistantHostName"
    with pytest.raises(ServerSelectionTimeoutError):
        RawDataTable(config=modified_config)


def test_datatable_query_by_date(raw_data_table, fits_header_translator):
    """ """
    # Get list of all dates in the database
    dates = sorted(raw_data_table.query()["dateObs"].values)
    date_end = dates[-1]
    n_files = len(dates)
    for date_start in dates[:-1]:
        # Get filenames between dates
        filenames = raw_data_table.query(date_start=date_start,
                                         date_end=date_end)["filename"].values
        assert len(filenames) <= n_files  # This holds because we sorted the dates
        n_files = len(filenames)
        for filename in filenames:
            # Assert date is within expected range
            header = read_fits_header(filename)
            date = parse_date(fits_header_translator.translate_dateObs(header))
            assert date >= parse_date(date_start)
            assert date < parse_date(date_end)


def test_query_latest(raw_data_table, config, tol=1):
    """Test query_latest finds the correct number of DB entries."""
    date_start = config["exposure_sequence"]["start_date"]
    n_days = config["exposure_sequence"]["n_days"]
    date_start = parse_date(date_start)
    date_now = current_date()
    if date_now <= date_start + timedelta(days=n_days):
        pytest.skip(f"Test does not work unless current date is later than all test exposures.")
    timediff = date_now - date_start
    # This should capture all the files
    qresult = raw_data_table.query_latest(days=timediff.days + tol)
    assert len(qresult) == len(raw_data_table.query())
    # This should capture none of the files
    qresult = raw_data_table.query_latest(days=0, hours=0, seconds=0)
    assert len(qresult) == 0


def test_update(raw_data_table):
    """Test that we can update a document specified by a filename."""
    data = raw_data_table.query().iloc[0]
    # Get a filename to use as an identifier
    filename = data["filename"]
    # Get a key to update
    key = [_ for _ in data.keys() if _ not in ["filename", "_id"]][0]
    old_value = data[key]
    new_value = "ThisIsAnewValue"
    assert old_value != new_value  # Let's be sure...
    # Update the key with the new value
    update_dict = {key: new_value}
    data_id = {"filename": filename}
    raw_data_table.update(data_id, update_dict)
    # Check the values match
    data_updated = raw_data_table.query().iloc[0]
    assert data_updated["_id"] == data["_id"]
    assert data_updated[key] == new_value


def test_update_file_data_bad_filename(raw_data_table):
    """Test that we can update a document specified by a filename."""
    # Specify the bad filename
    filenames = raw_data_table.query()["filename"].values
    filename = "ThisIsNotAFilename"
    assert filename not in filenames
    update_dict = {"A Key": "A Value"}
    with pytest.raises(RuntimeError):
        raw_data_table.update_file_data(filename=filename, data=update_dict)


def test_update_no_permission(raw_data_table):
    """ Make sure we can't edit things without permission. """
    raw_data_table.lock()
    with pytest.raises(PermissionError):
        raw_data_table.update({"filename": "notafile"}, {})
    raw_data_table.unlock()
