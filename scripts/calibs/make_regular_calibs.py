"""
Script to create master calibs in regular intervals. In each time interval, produce master calibs
for today's date and send them to the archive. Only the most recent raw calib data will be used.
Existing calibs for today's date will be overwritten.
"""
import time
import argparse
from datetime import timedelta
from multiprocessing import Pool

from huntsman.drp.base import HuntsmanBase
from huntsman.drp.utils.date import current_date
from huntsman.drp.datatable import RawDataTable
from huntsman.drp.screening import RawCalibScreener


# TODO: Move this class
class RegularCalibMaker(HuntsmanBase):

    def __init__(self, sleep_interval=86400, day_range=1000, nproc=1, config=None, logger=None,
                 **kwargs):
        super().__init__(config=config, logger=logger, **kwargs)
        self.sleep_interval = sleep_interval
        self.day_range = day_range
        self.datatable = RawDataTable(config=self.config, logger=self.logger)
        self._calib_screener = RawCalibScreener(config=self.config, logger=self.logger)
        self._nproc = nproc
        self._calib_types = self.config["calib"]["types"]

    def run(self):
        """ Periodically create a new set of master calibs. """
        with Pool(self._nproc) as pool:
            while True:
                pool.apply_async(self._run_next, (current_date(),))

                self.logger.info(f"Sleeping for {self.sleep_interval} seconds.")
                time.sleep(self.sleep_interval)

    def _run_next(self, date_end):
        """ Run the next set of calibs. """
        date_start = date_end - timedelta(days=self.day_range)

        # Get latest files that satisfy screening criteria
        df = self.datatable.query(date_start=date_start, date_end=date_end,
                                  screener=self._calib_screener)

        # Ingest into repo
        filenames = df["filenames"].values
        self.butler_repository.ingest_raw_data(filenames)

        # Make master calibs and archive them
        self.butler_repository.make_master_calibs()
        self.butler_repository.archive_master_calibs()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep_interval", type=int, default=86400)
    parser.add_argument("--day_range", type=int, default=30)
    args = parser.parse_args()

    RegularCalibMaker(sleep_interval=args.sleep_interval, day_range=args.day_range).run()
