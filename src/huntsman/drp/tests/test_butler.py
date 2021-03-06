import os

from huntsman.drp.utils import current_date


def test_initialise(butler_repos):
    """Make sure the repos are created properly"""
    for butler_repo in butler_repos:
        with butler_repo:
            for dir in [butler_repo.butler_directory, butler_repo.calib_directory]:
                assert os.path.isdir(dir)
                assert "_mapper" in os.listdir(dir)
            assert butler_repo.butler is not None


def test_temp_repo(temp_butler_repo):
    """Test the temp butler repo behaves as expected"""
    attrs = ["butler", "butler_directory", "calib_directory"]
    for a in attrs:
        assert getattr(temp_butler_repo, a) is None
    with temp_butler_repo:
        for a in attrs:
            assert getattr(temp_butler_repo, a) is not None
    # Now check things have been cleaned up properly
    for a in attrs:
        assert getattr(temp_butler_repo, a) is None


def test_ingest(raw_data_table, butler_repos, config):
    """Test ingest for each Butler repository."""
    config = config["testing"]["exposure_sequence"]
    n_filters = len(config["filters"])

    filenames = raw_data_table.query_column("filename")
    for butler_repo in butler_repos:
        with butler_repo as br:

            # Count the number of ingested files
            data_ids = br.butler.queryMetadata('raw', ['visit', 'ccd'])
            assert len(data_ids) == 0
            br.ingest_raw_data(filenames)
            data_ids = br.butler.queryMetadata('raw', ['visit', 'ccd'])
            assert len(data_ids) == len(filenames)

            # Check we have the right number of each datatype
            n_flat = config["n_cameras"] * config["n_days"] * config["n_flat"] * n_filters
            data_ids = br.butler.queryMetadata('raw', ['visit', 'ccd'],
                                               dataId={"dataType": "flat"})
            assert len(data_ids) == n_flat
            n_sci = config["n_cameras"] * config["n_days"] * config["n_science"] * n_filters
            data_ids = br.butler.queryMetadata('raw', ['visit', 'ccd'],
                                               dataId={"dataType": "science"})
            assert len(data_ids) == n_sci
            n_bias = config["n_cameras"] * config["n_days"] * config["n_bias"] * 2  # 2 exp times
            data_ids = br.butler.queryMetadata('raw', ['visit', 'ccd'],
                                               dataId={"dataType": "bias"})
            assert len(data_ids) == n_bias


def test_make_master_calibs(raw_data_table, temp_butler_repo, config):
    """ Make sure the correct number of master bias frames are produced."""
    config = config["testing"]["exposure_sequence"]
    n_filters = len(config["filters"])
    n_bias = config["n_cameras"] * 2  # 2 exp times
    n_flat = config["n_cameras"] * n_filters

    # Use the Butler repo to make the calibs
    filenames = raw_data_table.query_column("filename")
    with temp_butler_repo as br:
        br.ingest_raw_data(filenames)
        # Make the biases
        br.make_master_biases(calib_date=current_date(), rerun="test_rerun", ingest=True)
        metadata_bias = br.query_calib_metadata(table="bias")
        # Make the flats, using make_master_calibs for test completeness
        br.make_master_calibs(calib_date=current_date(), rerun="test_rerun", ingest=True,
                              skip_bias=True)
        metadata_flat = br.query_calib_metadata(table="flat")

    # Check the biases
    assert len(metadata_bias) == n_bias
    exptimes = set()
    ccds = set()
    for md in metadata_bias:
        exptimes.update([md["expTime"]])
        ccds.update([md["ccd"]])
    assert len(exptimes) == 2
    assert len(ccds) == config["n_cameras"]

    # Check the flats
    assert len(metadata_flat) == n_flat
    filters = set()
    ccds = set()
    for md in metadata_flat:
        filters.update([md["filter"]])
        ccds.update([md["ccd"]])
    assert len(filters) == 2
    assert len(ccds) == config["n_cameras"]
