import pytest

from huntsman.drp.base import load_config
from huntsman.drp.tests.testdata import FakeExposureSequence
from huntsman.drp.fitsutil import FitsHeaderTranslator
from huntsman.drp.datatable import RawDataTable
from huntsman.drp.refcat import TapReferenceCatalogue
from huntsman.drp.butler import ButlerRepository, TemporaryButlerRepository

# ===========================================================================
# Config


@pytest.fixture(scope="session")
def config():
    return load_config(ignore_local=True)

# ===========================================================================
# Reference catalogue


@pytest.fixture(scope="session")
def reference_catalogue(config):
    return TapReferenceCatalogue(config=config)

# ===========================================================================
# Butler repositories


@pytest.fixture(scope="function")
def temp_butler_repo(config):
    return TemporaryButlerRepository(config=config)


@pytest.fixture(scope="function")
def fixed_butler_repo(config, tmp_path_factory):
    dir = tmp_path_factory.mktemp("fixed_butler_repo")
    return ButlerRepository(directory=str(dir), config=config)


@pytest.fixture(scope="function")
def butler_repos(fixed_butler_repo, temp_butler_repo):
    return fixed_butler_repo, temp_butler_repo


# ===========================================================================
# Testing data


@pytest.fixture(scope="session")
def fits_header_translator(config):
    return FitsHeaderTranslator(config=config)


@pytest.fixture(scope="session")
def raw_data_table(tmp_path_factory, config, fits_header_translator):
    """
    Create a temporary directory populated with fake FITS images, then parse the images into the
    raw data table.
    """
    # Generate the fake data
    tempdir = tmp_path_factory.mktemp("test_exposure_sequence")
    expseq = FakeExposureSequence(config=config)
    expseq.generate_fake_data(directory=tempdir)

    # Populate the database
    raw_data_table = RawDataTable(config=config)
    for filename, header in expseq.header_dict.items():
        # Parse the header
        parsed_header = fits_header_translator.parse_header(header)
        parsed_header["filename"] = filename
        # Insert the parsed header into the DB table
        raw_data_table.insert_one(parsed_header)

    # Make sure table has the correct number of rows
    assert len(raw_data_table.query()) == expseq.file_count
    return raw_data_table
