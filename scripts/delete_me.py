from huntsman.drp.datatable import RawDataTable, MasterCalibTable
from huntsman.drp.butler import ButlerRepository

if __name__ == "__main__":

    rdt = RawDataTable()
    mct = MasterCalibTable()
    br = ButlerRepository("/home/lsst/test-butler-repo")

    fnames_sci = rdt.query({"dataType": "science", "expTime": 60, "ccd": 8})["filename"].values[:1]
    fnames_bias = mct.query({"datasetType": "bias"})["filename"].values
    fnames_flat = mct.query({"datasetType": "flat"})["filename"].values

    br.ingest_raw_data(fnames_sci)
    br.ingest_master_calibs("bias", fnames_bias)
    br.ingest_master_calibs("flat", fnames_flat)

    br.make_reference_catalogue()

    br.make_calexps()
